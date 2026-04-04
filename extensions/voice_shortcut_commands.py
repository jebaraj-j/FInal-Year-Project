"""
extensions/voice_shortcut_commands.py
=====================================
Additional voice shortcut command layer.

This module is intentionally separate from the core voice assistant logic.
It handles shortcut-like commands with strict matching to avoid conflicts.
"""

from typing import Callable, Tuple

import pyautogui


NOISE_WORDS = {
    "assistant",
    "system",
    "please",
    "now",
    "quickly",
}


def _normalize(text: str) -> str:
    normalized = " ".join((text or "").lower().split())
    if not normalized:
        return ""

    tokens = [t for t in normalized.split() if t not in NOISE_WORDS]
    return " ".join(tokens).strip()


def _press(key: str) -> None:
    pyautogui.press(key)


def _hotkey(*keys: str) -> None:
    pyautogui.hotkey(*keys)


def _screenshot() -> None:
    # Windows snip overlay
    _hotkey("win", "shift", "s")


def _open_file() -> None:
    _hotkey("ctrl", "o")


def _close_file() -> None:
    _hotkey("ctrl", "w")


def _close_window() -> None:
    _hotkey("alt", "f4")


def _minimize_window() -> None:
    _hotkey("win", "down")


def _maximize_window() -> None:
    _hotkey("win", "up")


def _zoom_in() -> None:
    _hotkey("ctrl", "+")


def _zoom_out() -> None:
    _hotkey("ctrl", "-")


def _scroll_up() -> None:
    pyautogui.scroll(600)


def _scroll_down() -> None:
    pyautogui.scroll(-600)


def _next_page() -> None:
    _press("pagedown")


def _previous_page() -> None:
    _press("pageup")


def _left() -> None:
    _press("left")


def _right() -> None:
    _press("right")


def _up() -> None:
    _press("up")


def _down() -> None:
    _press("down")


# Priority order matters:
# Specific phrases must be checked before generic words like "next"/"previous".
_PRIORITY_COMMANDS: list[tuple[str, Callable[[], None], str]] = [
    ("next image", _right, "Next image"),
    ("previous image", _left, "Previous image"),
    ("next page", _next_page, "Next page"),
    ("previous page", _previous_page, "Previous page"),
]

_EXACT_COMMANDS: dict[str, tuple[Callable[[], None], str]] = {
    "screenshot": (_screenshot, "Screenshot"),
    "open file": (_open_file, "Open file"),
    "close file": (_close_file, "Close file"),
    "close": (_close_window, "Close window"),
    "minimize": (_minimize_window, "Minimize window"),
    "maximize": (_maximize_window, "Maximize window"),
    "zoom in": (_zoom_in, "Zoom in"),
    "zoom out": (_zoom_out, "Zoom out"),
    "scroll up": (_scroll_up, "Scroll up"),
    "scroll down": (_scroll_down, "Scroll down"),
    "up": (_up, "Arrow up"),
    "down": (_down, "Arrow down"),
    "left": (_left, "Arrow left"),
    "right": (_right, "Arrow right"),
    "next": (_right, "Arrow right"),
    "previous": (_left, "Arrow left"),
}

ADDITIONAL_PHRASES = [item[0] for item in _PRIORITY_COMMANDS] + list(_EXACT_COMMANDS.keys())


def check_and_execute(command_text: str) -> Tuple[bool, str]:
    """
    Execute additional shortcut commands.

    Returns:
        (handled, message)
    """
    text = _normalize(command_text)
    if not text:
        return False, ""

    try:
        for phrase, action, label in _PRIORITY_COMMANDS:
            if text == phrase:
                action()
                return True, label

        item = _EXACT_COMMANDS.get(text)
        if item:
            action, label = item
            action()
            return True, label

        return False, ""
    except Exception as exc:
        return True, f"Shortcut command failed: {exc}"
