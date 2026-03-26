"""
Task switch gesture module for left-hand Alt+Tab window switching.
Handles rapid tab cycling with repeated pinch gestures.
"""
import pyautogui
import time
import numpy as np
from typing import List, Tuple
from config import Config


class TaskSwitchGesture:
    """Manages left-hand task switching gestures."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.task_switch_active = False
        self.last_tab_time = 0.0

    def detect_and_handle(
        self,
        pts: List[Tuple[float, float, float]]
    ) -> bool:
        """
        Detect task switch gesture and handle Alt+Tab.
        
        Gesture: Thumb-index pinch (close proximity)
        
        Returns:
            Whether task switching is currently active
        """
        # Calculate thumb-index distance
        thumb_tip = np.array(pts[4][:2])
        index_tip = np.array(pts[8][:2])
        pinch_dist = np.linalg.norm(thumb_tip - index_tip)
        is_pinch = pinch_dist <= self.cfg.left_pinch_threshold
        
        current_time = time.time()
        
        if is_pinch:
            if not self.task_switch_active:
                # Pinch START - begin Alt+Tab
                pyautogui.keyDown("alt")
                pyautogui.press("tab")
                self.task_switch_active = True
                self.last_tab_time = current_time
                print("LEFT HAND: TASK SWITCH START (pinch gesture)")
            elif current_time - self.last_tab_time >= self.cfg.tab_repeat_sec:
                # Pinch HOLD - continue cycling through windows
                pyautogui.press("tab")
                self.last_tab_time = current_time
                print("LEFT HAND: TASK SWITCH CYCLE")
        else:
            if self.task_switch_active:
                # Pinch RELEASE - end Alt+Tab
                pyautogui.keyUp("alt")
                self.task_switch_active = False
                print("LEFT HAND: TASK SWITCH END (pinch released)")

        return self.task_switch_active

    def force_release(self):
        """Force release Alt key if task switching is active."""
        if self.task_switch_active:
            pyautogui.keyUp("alt")
            self.task_switch_active = False
            print("LEFT HAND: TASK SWITCH FORCE END (no hands)")

    def reset(self):
        """Reset task switch gesture state."""
        self.task_switch_active = False
        self.last_tab_time = 0.0
