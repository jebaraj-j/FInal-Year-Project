"""
Volume controller using pycaw (Windows Core Audio API).
Reads current volume precisely and adjusts by exact percentage.
"""

import time
from typing import Optional, Dict, Any

try:
    from pycaw.pycaw import AudioUtilities
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

import ctypes
VK_VOLUME_UP   = 0xAF
VK_VOLUME_DOWN = 0xAE
KEYEVENTF_KEYUP = 0x0002

try:
    from ..utils.logger import get_logger
except ImportError:
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger


class VolumeController:
    """
    Controls system audio volume using pycaw for read+set with exact percentages.
    Falls back to VK_VOLUME keys if pycaw is unavailable.
    """

    STEP = 10   # % for relative up/down

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self.logger = get_logger()
        self._ev = None
        self._initialized = True

        if PYCAW_AVAILABLE:
            try:
                device = AudioUtilities.GetSpeakers()
                self._ev = device.EndpointVolume
                # Quick test
                _ = self._ev.GetMasterVolumeLevelScalar()
                self.is_supported = True
                self.logger.info("VolumeController initialized (pycaw)")
            except Exception as e:
                self.logger.log_error("VolumeInitError", str(e))
                self._ev = None
                self.is_supported = True  # Will use VK fallback
                self.logger.info("VolumeController initialized (VK fallback)")
        else:
            self.is_supported = True
            self.logger.info("VolumeController initialized (VK fallback)")

    def get_current(self) -> int:
        """Get current volume as 0-100 integer."""
        if self._ev:
            try:
                return int(self._ev.GetMasterVolumeLevelScalar() * 100)
            except Exception:
                pass
        return -1

    def _set_by_scalar(self, scalar: float) -> bool:
        """Set volume by scalar 0.0-1.0 using pycaw."""
        if self._ev:
            try:
                clamped = max(0.0, min(1.0, scalar))
                self._ev.SetMasterVolumeLevelScalar(clamped, None)
                return True
            except Exception as e:
                self.logger.log_error("VolumeSetError", str(e))
        return False

    def _vk_press(self, vk_code: int, count: int) -> bool:
        """Fallback: press Windows media key N times."""
        try:
            for _ in range(count):
                ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
                time.sleep(0.03)
            return True
        except Exception as e:
            self.logger.log_error("VKPressError", str(e))
            return False

    def set(self, value: int) -> bool:
        """Set volume to exact percentage."""
        clamped = max(0, min(100, value))
        if self._ev:
            return self._set_by_scalar(clamped / 100.0)
        # VK fallback: go to 0 then up
        self._vk_press(VK_VOLUME_DOWN, 50)
        time.sleep(0.1)
        return self._vk_press(VK_VOLUME_UP, clamped // 2)

    def execute_action(self, action: str, value: Optional[int] = None) -> bool:
        """
        Execute volume action.

        "increase volume" → absolute_increase → 100%
        "volume up"       → relative_increase  → current + 10%
        "decrease volume" → absolute_decrease  → 0%
        "volume down"     → relative_decrease  → current - 10%
        "set volume 70"   → set_value → 70%
        """
        if action == "absolute_increase":
            ok = self._set_by_scalar(1.0) if self._ev else self._vk_press(VK_VOLUME_UP, 50)
            print("🔊 Volume → 100%")
            return ok

        elif action == "absolute_decrease":
            ok = self._set_by_scalar(0.0) if self._ev else self._vk_press(VK_VOLUME_DOWN, 50)
            print("🔇 Volume → 0%")
            return ok

        elif action == "relative_increase":
            if self._ev:
                current = self.get_current()
                new = min(100, current + self.STEP)
                print(f"🔊 Volume UP: {current}% → {new}%")
                return self._set_by_scalar(new / 100.0)
            else:
                self._vk_press(VK_VOLUME_UP, 5)
                print("🔊 Volume UP")
                return True

        elif action == "relative_decrease":
            if self._ev:
                current = self.get_current()
                new = max(0, current - self.STEP)
                print(f"🔉 Volume DOWN: {current}% → {new}%")
                return self._set_by_scalar(new / 100.0)
            else:
                self._vk_press(VK_VOLUME_DOWN, 5)
                print("🔉 Volume DOWN")
                return True

        elif action == "set_value":
            if value is not None:
                current = self.get_current()
                print(f"🔊 Volume: {current}% → {value}%")
                return self.set(value)
            else:
                self.logger.log_error("VolumeExecuteError", "set_value requires a value")
                return False

        else:
            self.logger.log_error("VolumeExecuteError", f"Unknown action: {action}")
            return False

    def get_volume_info(self) -> Dict[str, Any]:
        return {
            "supported": self.is_supported,
            "current_volume": self.get_current(),
            "min_volume": 0,
            "max_volume": 100
        }

    def cleanup(self) -> None:
        self.logger.info("VolumeController cleanup completed")


if __name__ == "__main__":
    v = VolumeController()
    print(f"Current volume: {v.get_current()}%")
    print("Testing volume up (+10%)...")
    v.execute_action("relative_increase")
    time.sleep(0.5)
    print(f"After: {v.get_current()}%")
