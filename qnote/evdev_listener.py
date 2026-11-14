"""
Linux Kernel evdev Physical Double-Alt Listener for Qnote
Directly monitors /dev/input/event* devices.
Bypasses Wayland/X11 compositor boundaries with zero latency and 100% reliability.
Requires user to have read access to /dev/input (e.g. member of 'input' group).
"""
import time
import threading
import glob
from typing import Callable, List

# Linux input-event codes
EV_KEY = 1
KEY_LEFTALT = 56
KEY_RIGHTALT = 100

class EvdevAltListener:
    def __init__(self, callback: Callable[[], None]):
        self.callback = callback
        self._running = False
        self._threads: List[threading.Thread] = []
        self._last_tap_time = 0.0
        self._press_time = 0.0
        self._other_key = False

    def is_available(self) -> bool:
        """Checks if at least one keyboard input device can be read."""
        try:
            import evdev
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            for dev in devices:
                caps = dev.capabilities()
                if EV_KEY in caps:
                    keys = caps[EV_KEY]
                    if KEY_LEFTALT in keys or KEY_RIGHTALT in keys:
                        return True
        except Exception:
            pass
        return False

    def start(self) -> bool:
        """Starts monitoring all readable keyboard devices."""
        try:
            import evdev
        except ImportError:
            return False

        device_paths = evdev.list_devices()
        keyboard_devs = []

        for path in device_paths:
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()
                if EV_KEY in caps:
                    keys = caps[EV_KEY]
                    if KEY_LEFTALT in keys or KEY_RIGHTALT in keys:
                        keyboard_devs.append(dev)
            except (PermissionError, OSError):
                continue

        if not keyboard_devs:
            return False

        self._running = True
        for dev in keyboard_devs:
            t = threading.Thread(target=self._monitor_device, args=(dev,), daemon=True)
            self._threads.append(t)
            t.start()

        return True

    def stop(self):
        self._running = False

    def _monitor_device(self, dev):
        try:
            for event in dev.read_loop():
                if not self._running:
                    break

                if event.type == EV_KEY:
                    now = time.time()
                    code = event.code
                    val = event.value  # 1: press, 0: release, 2: repeat

                    if code in (KEY_LEFTALT, KEY_RIGHTALT):
                        if val == 1:
                            # Press Alt
                            self._press_time = now
                            self._other_key = False
                            
                            # Check if this press immediately completes a double-tap!
                            interval = (now - self._last_tap_time) * 1000.0
                            if 70.0 <= interval <= 500.0:
                                self._last_tap_time = 0.0
                                self.callback()
                        elif val == 0:
                            # Release Alt
                            duration = (now - self._press_time) * 1000.0
                            if duration < 350.0 and not self._other_key:
                                self._last_tap_time = now
                    else:
                        # Another key was pressed, cancel double tap
                        if val == 1:
                            self._other_key = True
                            self._last_tap_time = 0.0
        except Exception:
            pass
