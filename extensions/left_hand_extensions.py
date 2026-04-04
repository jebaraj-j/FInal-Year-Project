"""
extensions/left_hand_extensions.py
====================================
NEW left-hand gestures added externally.
Original vision_working.py is NOT modified.

Gestures handled here:
  - COPY     : Left index only,          held 1 s  → Ctrl+C
  - PASTE    : Left index + middle,      held 1 s  → Ctrl+V
  - MINIMIZE : Left closed fist,         held 1 s  → Win+Down
  - MAXIMIZE : Left open palm,           held 1 s  → Win+Up
"""

import pyautogui
from extensions.hold_detector import HoldDetector


class LeftHandExtensions:
    """
    Manages all NEW left-hand gestures using hold detection.
    Integrate by calling process() once per frame with current finger states.
    """

    HOLD_TIME     = 1.0   # seconds gesture must be held
    COOLDOWN_TIME = 2.5   # seconds before same action can fire again

    def __init__(self):
        self._copy_hold     = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)
        self._paste_hold    = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)
        self._minimize_hold = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)
        self._maximize_hold = HoldDetector(self.HOLD_TIME, self.COOLDOWN_TIME)

    # ------------------------------------------------------------------
    def process(self, states: dict, is_left_pinch: bool) -> dict:
        """
        Call every frame with left-hand finger states.

        Args:
            states        : dict[str, bool] — finger extended states
                            keys: Thumb, Index, Middle, Ring, Pinky
            is_left_pinch : bool — True when thumb+index distance <= threshold
                            (used to block copy/paste when pinching for Alt+Tab)

        Returns:
            dict with keys:
                'action'    : str  — 'copy' | 'paste' | 'minimize' | 'maximize' | None
                'progress'  : float 0–1 — hold progress of the active gesture
                'gesture'   : str  — human-readable gesture name
                'subtitle'  : str  — UI subtitle
        """
        result = {'action': None, 'progress': 0.0, 'gesture': '', 'subtitle': ''}

        # Don't run copy/paste while pinching for Alt+Tab
        no_pinch = not is_left_pinch

        # ── Detect gesture shapes ───────────────────────────────────
        all_folded   = not any(states[n] for n in ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'])
        all_extended = all(states[n] for n in ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'])

        index_only   = (
            states['Index']
            and not states['Middle']
            and not states['Ring']
            and not states['Pinky']
            and no_pinch
        )
        index_middle = (
            states['Index']
            and states['Middle']
            and not states['Ring']
            and not states['Pinky']
            and no_pinch
        )

        # ── Reset detectors for mutually exclusive gestures ─────────
        # Only one gesture can be held at a time
        active_gesture = None
        if all_folded:    active_gesture = 'minimize'
        elif all_extended: active_gesture = 'maximize'
        elif index_middle: active_gesture = 'paste'     # check before index_only
        elif index_only:   active_gesture = 'copy'

        if active_gesture != 'minimize':  self._minimize_hold.reset()
        if active_gesture != 'maximize':  self._maximize_hold.reset()
        if active_gesture != 'copy':      self._copy_hold.reset()
        if active_gesture != 'paste':     self._paste_hold.reset()

        # ── MINIMIZE (Fist, hold 1 s) ────────────────────────────────
        if active_gesture == 'minimize':
            fired = self._minimize_hold.update(True)
            prog  = self._minimize_hold.progress()
            if fired:
                pyautogui.hotkey('win', 'down')
                result['action'] = 'minimize'
            result['gesture']  = 'Minimize (hold 1s)'
            result['subtitle'] = f'Fist — {prog*100:.0f}% — Win+Down'
            result['progress'] = prog

        # ── MAXIMIZE (Open Palm, hold 1 s) ───────────────────────────
        elif active_gesture == 'maximize':
            fired = self._maximize_hold.update(True)
            prog  = self._maximize_hold.progress()
            if fired:
                pyautogui.hotkey('win', 'up')
                result['action'] = 'maximize'
            result['gesture']  = 'Maximize (hold 1s)'
            result['subtitle'] = f'Open Palm — {prog*100:.0f}% — Win+Up'
            result['progress'] = prog

        # ── PASTE (Index + Middle, hold 1 s) ─────────────────────────
        elif active_gesture == 'paste':
            fired = self._paste_hold.update(True)
            prog  = self._paste_hold.progress()
            if fired:
                pyautogui.hotkey('ctrl', 'v')
                result['action'] = 'paste'
            result['gesture']  = 'Paste (hold 1s)'
            result['subtitle'] = f'Index+Middle — {prog*100:.0f}% — Ctrl+V'
            result['progress'] = prog

        # ── COPY (Index Only, hold 1 s) ──────────────────────────────
        elif active_gesture == 'copy':
            fired = self._copy_hold.update(True)
            prog  = self._copy_hold.progress()
            if fired:
                pyautogui.hotkey('ctrl', 'c')
                result['action'] = 'copy'
            result['gesture']  = 'Copy (hold 1s)'
            result['subtitle'] = f'Index Only — {prog*100:.0f}% — Ctrl+C'
            result['progress'] = prog

        return result

    def reset_all(self):
        """Call when no hands are detected."""
        self._copy_hold.reset()
        self._paste_hold.reset()
        self._minimize_hold.reset()
        self._maximize_hold.reset()
