"""
Window control gesture module for left-hand window management.
Handles minimizing windows with closed fist gesture.
"""
import pyautogui
from typing import List, Tuple
from config import Config, FINGER_DEFS
from utils import is_finger_extended


class WindowControlGesture:
    """Manages left-hand window control gestures."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.left_hand_state = "none"  # "none", "fist"

    def detect_and_handle(
        self,
        states: dict,
        task_switch_active: bool
    ) -> str:
        """
        Detect window control gestures and execute actions.
        
        Gesture: Closed fist (all fingers folded) → Minimize window
        
        Args:
            states: Dictionary of finger states
            task_switch_active: Whether task switching is currently active
            
        Returns:
            Current left-hand state
        """
        # Check if all fingers are folded (closed fist)
        all_fingers_folded = not any(states.get(n, False) for n in FINGER_DEFS)
        
        current_left_state = "fist" if all_fingers_folded else "none"
        
        # Trigger window actions only on state transitions
        # and only when not in task switch mode
        if not task_switch_active and self.left_hand_state != current_left_state:
            if current_left_state == "fist":
                pyautogui.hotkey("win", "down")
                print("LEFT HAND: MINIMIZE WINDOW (fist gesture)")
        
        if not task_switch_active:
            self.left_hand_state = current_left_state

        return current_left_state

    def reset(self):
        """Reset window control gesture state."""
        self.left_hand_state = "none"
