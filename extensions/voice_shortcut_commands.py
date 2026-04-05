"""
extensions/voice_shortcut_commands.py
=====================================
Additional voice shortcut command layer.

This module is intentionally separate from the core voice assistant logic.
It handles shortcut-like commands with strict matching to avoid conflicts.
"""

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

import ctypes
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


PAGE_JUMP_STEPS = 2


def _press(key: str) -> None:
    pyautogui.press(key)


def _hotkey(*keys: str) -> None:
    pyautogui.hotkey(*keys)


def _screenshot() -> str:
    """
    Capture full-display screenshot and save to project /screenshots folder.
    """
    out_dir = Path(__file__).resolve().parent.parent / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"screenshot_{ts}.png"
    image = pyautogui.screenshot()
    image.save(out_path)
    return f"Screenshot saved: {out_path}"


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
    # Try common zoom-in combos across apps/keyboards.
    try:
        _hotkey("ctrl", "add")  # numpad +
    except Exception:
        pass
    try:
        _hotkey("ctrl", "=")    # main keyboard +
    except Exception:
        pass
    try:
        _hotkey("ctrl", "+")
    except Exception:
        pass
    # Fallback: Ctrl + scroll up
    pyautogui.keyDown("ctrl")
    pyautogui.scroll(500)
    pyautogui.keyUp("ctrl")


def _zoom_out() -> None:
    # Try common zoom-out combos across apps/keyboards.
    try:
        _hotkey("ctrl", "subtract")  # numpad -
    except Exception:
        pass
    try:
        _hotkey("ctrl", "-")
    except Exception:
        pass
    # Fallback: Ctrl + scroll down
    pyautogui.keyDown("ctrl")
    pyautogui.scroll(-500)
    pyautogui.keyUp("ctrl")


def _scroll_up() -> None:
    pyautogui.scroll(600)


def _scroll_down() -> None:
    pyautogui.scroll(-600)


def _next_page() -> None:
    for _ in range(PAGE_JUMP_STEPS):
        _press("pagedown")


def _previous_page() -> None:
    for _ in range(PAGE_JUMP_STEPS):
        _press("pageup")


def _left() -> None:
    _press("left")


def _right() -> None:
    _press("right")


def _up() -> None:
    _press("up")


def _down() -> None:
    _press("down")


def _enter() -> None:
    _press("enter")


def _send_media_key(vk_code: int) -> bool:
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, 0x0002, 0)
        return True
    except Exception:
        return False


def _play_pause() -> None:
    if not _send_media_key(0xB3):
        try:
            _press("playpause")
        except Exception:
            pass


def _next_track() -> None:
    if not _send_media_key(0xB0):
        try:
            _press("nexttrack")
        except Exception:
            pass


def _previous_track() -> None:
    if not _send_media_key(0xB1):
        try:
            _press("prevtrack")
        except Exception:
            pass


# Priority order matters:
# Specific phrases must be checked before generic words like "next"/"previous".
_PRIORITY_COMMANDS: list[tuple[str, Callable[[], Optional[str]], str]] = [
    ("next track", _next_track, "Next track"),
    ("previous track", _previous_track, "Previous track"),
    ("next image", _right, "Next image"),
    ("previous image", _left, "Previous image"),
    ("next page", _next_page, "Next page"),
    ("previous page", _previous_page, "Previous page"),
]

_EXACT_COMMANDS: dict[str, tuple[Callable[[], Optional[str]], str]] = {
    "screenshot": (_screenshot, "Screenshot"),
    "open": (_enter, "Enter"),
    "enter": (_enter, "Enter"),
    "open selected": (_enter, "Enter"),
    "open selected item": (_enter, "Enter"),
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
    "play": (_play_pause, "Play/Pause"),
    "pause": (_play_pause, "Play/Pause"),
    "play video": (_play_pause, "Play/Pause"),
    "pause video": (_play_pause, "Play/Pause"),
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
                maybe_msg = action()
                return True, maybe_msg or label

        item = _EXACT_COMMANDS.get(text)
        if item:
            action, label = item
            maybe_msg = action()
            return True, maybe_msg or label

        return False, ""
    except Exception as exc:
        return True, f"Shortcut command failed: {exc}"
