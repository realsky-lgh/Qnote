"""
Ultra-Robust Cross-Platform Global Hotkey & Double-Alt Listener for Qnote
Supports:
1. Linux Native evdev: Kernel-level physical double-Alt detection (bypasses Wayland/X11 boundaries)
2. Windows Native: Win32 GetAsyncKeyState background poller (100% reliable)
3. Linux X11 fallback: Tap-based Double-Alt via pynput
4. Linux GNOME Wayland fallback: Native system shortcut (<Alt>grave / Alt + ~)
"""
import time
import sys
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from .config import DOUBLE_PRESS_INTERVAL_MS, MIN_PRESS_INTERVAL_MS
from .evdev_listener import EvdevAltListener

class GlobalHotkeyManager(QObject):
    toggle_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._listener = None
        self._win32_thread = None
        self._evdev_listener = None
        
        # State machine for Tap-based Double Alt
        self._alt_pressed = False
        self._alt_press_start_time = 0.0
        self._last_tap_time = 0.0
        self._other_key_pressed = False

    def start(self):
        self._running = True

        # 1. Windows: Native Win32 GetAsyncKeyState poller (most responsive and unblockable on Windows)
        if sys.platform == "win32":
            self._start_win32_poller()
            return

        # 2. Linux: Try kernel-level evdev physical listener first
        self._evdev_listener = EvdevAltListener(callback=self._on_evdev_double_alt)
        evdev_started = self._evdev_listener.start()
        
        if evdev_started:
            print("[Qnote Hotkey] Native Linux kernel evdev listener ACTIVE: Double-Alt physical detection enabled.")
        else:
            print("[Qnote Hotkey] Notice: Running under Wayland without direct /dev/input permissions.")
            print("[Qnote Hotkey] 💡 To unlock global Double-Alt in Wayland, run once: sudo usermod -aG input $USER")
            print("[Qnote Hotkey] Fallback shortcuts enabled: Alt + ~ (GNOME native shortcut) or system tray icon.")

        # 3. Universal pynput listener (works in X11 / Xwayland windowed mode)
        self._start_pynput_listener()

        # 4. Linux GNOME: Ensure xwayland grabs and register native system shortcut
        self._setup_linux_gnome_shortcuts()

    def _on_evdev_double_alt(self):
        self.toggle_requested.emit()

    def stop(self):
        self._running = False
        if self._evdev_listener:
            self._evdev_listener.stop()
            self._evdev_listener = None
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    # --- Windows Native Poller ---
    def _start_win32_poller(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            VK_MENU = 0x12  # Alt key

            def win32_loop():
                was_down = False
                press_time = 0.0
                last_tap = 0.0

                while self._running:
                    # High bit set means key is down
                    is_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                    now = time.time()

                    if is_down and not was_down:
                        # Alt key pressed
                        press_time = now
                        was_down = True
                        # Trigger directly on 2nd press if in tap window
                        interval = (now - last_tap) * 1000.0
                        if 60.0 <= interval <= 550.0:
                            last_tap = 0.0
                            self.toggle_requested.emit()
                    elif not is_down and was_down:
                        # Alt key released
                        was_down = False
                        press_duration = (now - press_time) * 1000.0
                        if press_duration < 350.0:
                            last_tap = now

                    time.sleep(0.015)  # 15ms resolution, virtually 0% CPU

            self._win32_thread = threading.Thread(target=win32_loop, daemon=True)
            self._win32_thread.start()
        except Exception as e:
            print(f"[Qnote Hotkey] Windows native poller error: {e}")

    # --- Tap-based Pynput Listener ---
    def _start_pynput_listener(self):
        try:
            from pynput import keyboard

            def is_alt(key):
                if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                    return True
                vk = getattr(key, 'vk', None)
                if vk in (18, 164, 165, 64, 108, 65513, 65514):
                    return True
                name = getattr(key, 'name', '')
                if name and 'alt' in str(name).lower():
                    return True
                key_str = str(key)
                if 'alt' in key_str.lower():
                    return True
                return False

            def on_press(key):
                now = time.time()
                if is_alt(key):
                    if not self._alt_pressed:
                        self._alt_pressed = True
                        self._alt_press_start_time = now
                        self._other_key_pressed = False
                        
                        # Trigger directly on 2nd press
                        interval = (now - self._last_tap_time) * 1000.0
                        if 60.0 <= interval <= 550.0:
                            self._last_tap_time = 0.0
                            self.toggle_requested.emit()
                else:
                    self._other_key_pressed = True
                    self._last_tap_time = 0.0

            def on_release(key):
                now = time.time()
                if is_alt(key):
                    self._alt_pressed = False
                    press_duration = (now - self._alt_press_start_time) * 1000.0
                    if press_duration < 350.0 and not self._other_key_pressed:
                        self._last_tap_time = now

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            print(f"[Qnote Hotkey] Pynput listener warning: {e}")

    # --- Linux GNOME System Shortcuts Setup ---
    def _setup_linux_gnome_shortcuts(self):
        """Auto-configure GNOME settings for Xwayland grabs and fallback shortcut."""
        import subprocess
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.mutter.wayland", "xwayland-allow-grabs", "true"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        try:
            get_cmd = ["gsettings", "get", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings"]
            res = subprocess.run(get_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                raw = res.stdout.strip()
                bindings = eval(raw) if raw.startswith('[') else []
                
                target_path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/qnote/"
                if target_path not in bindings:
                    bindings.append(target_path)
                    val_str = str(bindings).replace("'", '"')
                    subprocess.run(
                        ["gsettings", "set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", val_str],
                        check=True
                    )
                    prefix = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{target_path}"
                    subprocess.run(["gsettings", "set", prefix, "name", "Qnote 速记纸呼出"], check=True)
                    subprocess.run(["gsettings", "set", prefix, "command", "qnote --toggle"], check=True)
                    subprocess.run(["gsettings", "set", prefix, "binding", "<Alt>grave"], check=True)
        except Exception:
            pass
