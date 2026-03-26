"""
Cursor gesture module for right-hand cursor control and pinch detection.
Handles cursor movement and pinch-based click actions.
"""
import numpy as np
import pyautogui
import time
from typing import List, Tuple, Optional
from config import Config, Palette


class CursorGesture:
    """Manages right-hand cursor control and pinch detection."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.is_cursor_mode = False
        self.prev_index_norm: Optional[np.ndarray] = None
        self.pinch_state = "open"  # open, mild, tight
        self.line_color = Palette.LINE_OPEN
        self.last_single_time = 0.0
        self.last_double_time = 0.0
        
        # Disable PyAutoGUI fail-safe for smooth relative control
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.01

    def process(
        self,
        states: dict,
        pts: List[Tuple[float, float, float]],
        current_pinch_state: str = "open"
    ) -> Tuple[bool, str, Tuple[int, int, int], Optional[np.ndarray]]:
        """
        Process right-hand gestures for cursor control and clicking.
        
        Returns:
            Tuple of (cursor_hand, pinch_state, line_color, prev_index_norm)
        """
        # Determine cursor mode: ONLY index finger extended (not middle finger)
        cursor_hand = (
            states.get("Index", False) and
            not states.get("Middle", False)
        )
        
        # Get thumb and index positions
        thumb_tip = np.array(pts[4][:2])
        index_tip = np.array(pts[8][:2])
        dist = np.linalg.norm(thumb_tip - index_tip)

        # Determine pinch state based on distance
        if dist <= self.cfg.tight_pinch_max:
            self.pinch_state = "tight"
            self.line_color = Palette.LINE_TIGHT
            self._handle_tight_pinch()
        elif dist <= self.cfg.mild_pinch_max:
            self.pinch_state = "mild"
            self.line_color = Palette.LINE_MILD
            self._handle_mild_pinch()
        else:
            self.pinch_state = "open"
            self.line_color = Palette.LINE_OPEN
            if cursor_hand:  # Only move cursor if in cursor mode
                self._handle_open_hand(pts)

        return cursor_hand, self.pinch_state, self.line_color, self.prev_index_norm

    def _handle_open_hand(self, pts: List[Tuple[float, float, float]]):
        """Handle cursor movement when hand is open."""
        index_norm = np.array(pts[8][:2])
        
        if self.prev_index_norm is not None:
            dx = index_norm[0] - self.prev_index_norm[0]
            dy = index_norm[1] - self.prev_index_norm[1]
            movement = np.linalg.norm([dx, dy])
            
            if movement > self.cfg.deadzone:
                move_x = int(dx * self.cfg.sensitivity * self.cfg.camera_width)
                move_y = int(dy * self.cfg.sensitivity * self.cfg.camera_height)
                pyautogui.moveRel(move_x, move_y)
        
        self.prev_index_norm = index_norm.copy()

    def _handle_mild_pinch(self):
        """Handle single clicks during mild pinch."""
        current_time = time.time()
        if current_time - self.last_single_time >= self.cfg.single_repeat_sec:
            pyautogui.click()
            self.last_single_time = current_time
            print("RIGHT HAND: SINGLE CLICK (mild pinch)")

    def _handle_tight_pinch(self):
        """Handle double clicks during tight pinch."""
        current_time = time.time()
        if current_time - self.last_double_time >= self.cfg.double_repeat_sec:
            pyautogui.click(clicks=2)
            self.last_double_time = current_time
            print("RIGHT HAND: DOUBLE CLICK (tight pinch)")

    def reset(self):
        """Reset cursor gesture state."""
        self.is_cursor_mode = False
        self.prev_index_norm = None
        self.pinch_state = "open"
        self.line_color = Palette.LINE_OPEN
