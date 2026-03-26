"""
Brightness controller using screen_brightness_control (native WMI/DDC).
Tested and confirmed working on this system.
"""

import screen_brightness_control as sbc
from typing import Optional, Dict, Any

try:
    from ..utils.logger import get_logger
except ImportError:
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger


class BrightnessController:
    """
    Controls screen brightness using screen_brightness_control (native WMI/DDC).
    Confirmed working on this system.
    """

    STEP = 10   # % change for relative up/down commands

    def __init__(self):
        self.logger = get_logger()
        self.is_supported = True
        try:
            sbc.get_brightness(display=0)
            self.logger.info("BrightnessController initialized (screen_brightness_control)")
        except Exception as e:
            self.is_supported = False
            self.logger.log_error("BrightnessInitError", str(e))

    def get_current(self) -> int:
        try:
            val = sbc.get_brightness(display=0)
            return val[0] if isinstance(val, list) else int(val)
        except Exception:
            return 0

    def set(self, value: int) -> bool:
        try:
            clamped = max(0, min(100, value))
            sbc.set_brightness(clamped, display=0)
            current = self.get_current()
            self.logger.log_brightness_change(0, current, "set")
            print(f"🔆 Brightness → {current}%")
            return True
        except Exception as e:
            self.logger.log_error("BrightnessSetError", str(e))
            return False

    def increase(self, step: int = STEP) -> bool:
        current = self.get_current()
        return self.set(current + step)

    def decrease(self, step: int = STEP) -> bool:
        current = self.get_current()
        return self.set(current - step)

    def execute_action(self, action: str, value: Optional[int] = None) -> bool:
        """
        Execute brightness action.
        
        Commands:
           "increase brightness" → absolute_increase → 100%
           "brightness up"       → relative_increase  → +10%
           "decrease brightness" → absolute_decrease → 0%
           "brightness down"     → relative_decrease  → -10%
           "set brightness 70"   → set_value → 70%
        """
        if not self.is_supported:
            print("❌ Brightness control not supported on this system")
            return False

        if action == "absolute_increase":
            print("🔆 Brightness → 100% (MAX)")
            return self.set(100)

        elif action == "absolute_decrease":
            print("🔅 Brightness → 0% (MIN)")
            return self.set(0)

        elif action == "relative_increase":
            current = self.get_current()
            new = min(100, current + self.STEP)
            print(f"🔆 Brightness UP: {current}% → {new}%")
            return self.set(new)

        elif action == "relative_decrease":
            current = self.get_current()
            new = max(0, current - self.STEP)
            print(f"🔅 Brightness DOWN: {current}% → {new}%")
            return self.set(new)

        elif action == "set_value":
            if value is not None:
                print(f"🔆 Brightness → {value}%")
                return self.set(value)
            else:
                self.logger.log_error("BrightnessExecuteError", "set_value requires a value")
                return False

        else:
            self.logger.log_error("BrightnessExecuteError", f"Unknown action: {action}")
            return False

    def get_brightness_info(self) -> Dict[str, Any]:
        return {
            "supported": self.is_supported,
            "current_brightness": self.get_current(),
            "min_brightness": 0,
            "max_brightness": 100,
            "monitor_count": 1
        }

    def cleanup(self):
        pass


if __name__ == "__main__":
    bc = BrightnessController()
    print(f"Current brightness: {bc.get_current()}%")
    bc.execute_action("relative_increase")
