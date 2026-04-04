"""
extensions/hold_detector.py
===========================
Time-based hold detection layer.
Does NOT modify any original gesture logic.
Simply confirms a gesture is sustained for a required duration before firing.
"""

import time


class HoldDetector:
    """
    Detects whether a gesture is held continuously for a required duration.

    Usage:
        detector = HoldDetector(hold_seconds=1.0)
        # Inside your loop:
        if detector.update(is_gesture_active):
            # Gesture confirmed — fire the action once
    """

    def __init__(self, hold_seconds: float = 1.0, cooldown_seconds: float = 2.0):
        """
        Args:
            hold_seconds:    Time the gesture must be held before confirming.
            cooldown_seconds: Time before the same gesture can fire again.
        """
        self.hold_seconds    = hold_seconds
        self.cooldown_seconds = cooldown_seconds
        self._start_time     = 0.0
        self._last_fired     = 0.0
        self._active         = False

    def update(self, is_active: bool) -> bool:
        """
        Call every frame with whether the target gesture is currently detected.

        Returns:
            True exactly once when the gesture has been held long enough
            AND the cooldown period has passed.
        """
        now = time.time()

        if is_active:
            if not self._active:
                # Rising edge — start timing
                self._start_time = now
                self._active = True

            elapsed = now - self._start_time
            on_cooldown = (now - self._last_fired) < self.cooldown_seconds

            if elapsed >= self.hold_seconds and not on_cooldown:
                self._last_fired = now
                return True  # ← Fire the action

        else:
            # Gesture released — reset
            self._active     = False
            self._start_time = 0.0

        return False

    def progress(self) -> float:
        """
        Returns hold progress as 0.0–1.0 (useful for UI feedback).
        """
        if not self._active or self._start_time == 0.0:
            return 0.0
        return min(1.0, (time.time() - self._start_time) / self.hold_seconds)

    def reset(self):
        """Manually reset state (e.g. when no hands detected)."""
        self._active     = False
        self._start_time = 0.0
