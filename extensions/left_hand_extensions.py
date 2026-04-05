"""
Hold-based left-hand gesture extensions used by GestureWorker.

Gestures:
- Copy: pinky only (hold 1s) -> Ctrl+C
- Paste: ring + pinky (hold 1s) -> Ctrl+V
- Minimize: thumb only (hold 1s) -> Win+Down
- Maximize: open palm (hold 1s) -> Win+Up
"""

import time

import pyautogui

from extensions.hold_detector import HoldDetector


class LeftHandExtensions:
    """Manages left-hand hold gestures with cooldown and jitter tolerance."""

    HOLD_TIME = 1.0
    COOLDOWN_TIME = 2.5
    HOLD_GRACE_SEC = 0.20

    def __init__(self):
        self._copy_hold = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)
        self._paste_hold = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)
        self._minimize_hold = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)
        self._maximize_hold = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)
        self._last_active_gesture = None
        self._last_active_time = 0.0

    def process(self, states: dict, is_left_pinch: bool) -> dict:
        """
        Evaluate one frame of left-hand states.

        Args:
            states: dict keys -> Thumb, Index, Middle, Ring, Pinky
            is_left_pinch: kept for API compatibility with caller
        """
        _ = is_left_pinch  # reserved for future tuning, keep stable signature
        result = {"action": None, "progress": 0.0, "gesture": "", "subtitle": ""}

        thumb_e = states["Thumb"]
        index_e = states["Index"]
        middle_e = states["Middle"]
        ring_e = states["Ring"]
        pinky_e = states["Pinky"]

        is_copy = pinky_e and (not ring_e) and (not middle_e) and (not index_e)
        is_paste = ring_e and pinky_e and (not middle_e) and (not index_e)
        is_minimize = thumb_e and (not index_e) and (not middle_e) and (not ring_e) and (not pinky_e)
        is_maximize = thumb_e and index_e and middle_e and ring_e and pinky_e

        active_gesture = None
        if is_copy:
            active_gesture = "copy"
        elif is_paste:
            active_gesture = "paste"
        elif is_minimize:
            active_gesture = "minimize"
        elif is_maximize:
            active_gesture = "maximize"

        now = time.time()
        if active_gesture:
            self._last_active_gesture = active_gesture
            self._last_active_time = now
        elif self._last_active_gesture and (now - self._last_active_time) <= self.HOLD_GRACE_SEC:
            active_gesture = self._last_active_gesture
        else:
            self._last_active_gesture = None

        if active_gesture != "copy":
            self._copy_hold.reset()
        if active_gesture != "paste":
            self._paste_hold.reset()
        if active_gesture != "minimize":
            self._minimize_hold.reset()
        if active_gesture != "maximize":
            self._maximize_hold.reset()

        if active_gesture == "copy":
            fired = self._copy_hold.update(True)
            prog = self._copy_hold.progress()
            if fired:
                pyautogui.hotkey("ctrl", "c")
                result["action"] = "copy"
            result["gesture"] = "Copy (hold 1s)"
            result["subtitle"] = f"Pinky only - {prog*100:.0f}% - Ctrl+C"
            result["progress"] = prog

        elif active_gesture == "paste":
            fired = self._paste_hold.update(True)
            prog = self._paste_hold.progress()
            if fired:
                pyautogui.hotkey("ctrl", "v")
                result["action"] = "paste"
            result["gesture"] = "Paste (hold 1s)"
            result["subtitle"] = f"Ring+Pinky - {prog*100:.0f}% - Ctrl+V"
            result["progress"] = prog

        elif active_gesture == "minimize":
            fired = self._minimize_hold.update(True)
            prog = self._minimize_hold.progress()
            if fired:
                # Two-step minimize handles maximized windows more reliably.
                pyautogui.hotkey("win", "down")
                time.sleep(0.05)
                pyautogui.hotkey("win", "down")
                result["action"] = "minimize"
            result["gesture"] = "Minimize (hold 1s)"
            result["subtitle"] = f"Thumb only - {prog*100:.0f}% - Win+Down"
            result["progress"] = prog

        elif active_gesture == "maximize":
            fired = self._maximize_hold.update(True)
            prog = self._maximize_hold.progress()
            if fired:
                pyautogui.hotkey("win", "up")
                result["action"] = "maximize"
            result["gesture"] = "Maximize (hold 1s)"
            result["subtitle"] = f"Open palm - {prog*100:.0f}% - Win+Up"
            result["progress"] = prog

        return result

    def reset_all(self):
        self._copy_hold.reset()
        self._paste_hold.reset()
        self._minimize_hold.reset()
        self._maximize_hold.reset()
        self._last_active_gesture = None
        self._last_active_time = 0.0
