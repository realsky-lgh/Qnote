"""
Cross-Platform Global Hotkey Listener for Qnote
Detects double-pressing the Alt key (within 80ms ~ 450ms) to toggle the scratchpad.
Works on Windows and Linux (X11 / Wayland fallback via IPC).
"""
import time
import sys
from PyQt6.QtCore import QObject, pyqtSignal
from .config import DOUBLE_PRESS_INTERVAL_MS, MIN_PRESS_INTERVAL_MS

class GlobalHotkeyManager(QObject):
    toggle_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_alt_time = 0.0
        self._listener = None
        self._running = False

    def start(self):
        try:
            from pynput import keyboard
            
            def is_alt_key(key):
                if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                    return True
                # Sometimes on Linux/Win it comes as KeyCode
                name = getattr(key, 'name', None)
                if name and 'alt' in name.lower():
                    return True
                return False

            def on_press(key):
                if is_alt_key(key):
                    now = time.time()
                    dt_ms = (now - self._last_alt_time) * 1000.0
                    if MIN_PRESS_INTERVAL_MS <= dt_ms <= DOUBLE_PRESS_INTERVAL_MS:
                        # Double alt triggered!
                        self._last_alt_time = 0.0
                        self.toggle_requested.emit()
                    else:
                        self._last_alt_time = now
                else:
                    # Pressed other key, reset timer
                    self._last_alt_time = 0.0

            self._listener = keyboard.Listener(on_press=on_press)
            self._listener.daemon = True
            self._listener.start()
            self._running = True
        except Exception as e:
            # Fallback message for Wayland or restricted environments
            print(f"[Qnote Hotkey] Global listener warning: {e}")
            print("[Qnote Hotkey] You can always use system tray, 'qnote --toggle', or inside-window shortcuts.")

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._running = False
