"""
Scroll gesture module for vertical scrolling.
Detects index and middle finger extended with other fingers folded.
"""
import pyautogui
from typing import List, Tuple, Optional
from config import Config


class ScrollGesture:
    """Manages scroll gesture detection and handling."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.is_scroll_mode = False
        self.prev_scroll_norm: Optional[float] = None

    def detect_and_handle(
        self,
        states: dict,
        pts: List[Tuple[float, float, float]]
    ) -> Tuple[bool, Optional[float]]:
        """
        Detect scroll gesture and handle scrolling.
        
        Gesture: Index and middle fingers extended, thumb, ring, and pinky folded.
        
        Returns:
            Tuple of (is_scroll_mode, prev_scroll_norm)
        """
        scroll_gesture = (
            states.get("Index", False) and
            states.get("Middle", False) and
            not states.get("Thumb", True) and
            not states.get("Ring", True) and
            not states.get("Pinky", True)
        )

        if scroll_gesture:
            self.is_scroll_mode = True
            if self.prev_scroll_norm is None:
                self.prev_scroll_norm = pts[8][1]  # Index finger Y-coordinate
            else:
                # Calculate scroll amount based on finger movement
                dy = pts[8][1] - self.prev_scroll_norm
                if abs(dy) > self.cfg.scroll_deadzone:
                    scroll_amount = int(-dy * self.cfg.scroll_sensitivity)
                    pyautogui.scroll(scroll_amount)
                    print(f"SCROLL: {scroll_amount}")
                self.prev_scroll_norm = pts[8][1]
        else:
            self.is_scroll_mode = False
            self.prev_scroll_norm = None

        return self.is_scroll_mode, self.prev_scroll_norm

    def reset(self):
        """Reset scroll gesture state."""
        self.is_scroll_mode = False
        self.prev_scroll_norm = None
