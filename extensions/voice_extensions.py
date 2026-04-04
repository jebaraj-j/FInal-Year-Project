"""
extensions/voice_extensions.py
================================
NEW voice close commands added externally.
Original voice_assistant/main.py is NOT modified.

New commands:
  - "vscode closing"         → close Visual Studio Code
  - "chrome closing"         → close Google Chrome
  - "file explorer closing"  → close File Explorer
"""

import subprocess
import sys


# Map trigger phrases → process name to kill
CLOSE_COMMANDS = {
    # VS Code (4)
    "vscode closing":           "Code.exe",
    "vs code closing":          "Code.exe",
    "visual studio closing":    "Code.exe",
    "close vscode":             "Code.exe",

    # Chrome (4)
    "chrome closing":           "chrome.exe",
    "google chrome closing":    "chrome.exe",
    "browser closing":          "chrome.exe",
    "close chrome":             "chrome.exe",

    # Notepad (4)
    "notepad closing":          "notepad.exe",
    "close notepad":            "notepad.exe",
    "note pad closing":         "notepad.exe",
    "close note pad":           "notepad.exe",

    # Settings (4)
    "settings closing":         "SystemSettings.exe",
    "close settings":           "SystemSettings.exe",
    "windows settings closing": "SystemSettings.exe",
    "close windows settings":   "SystemSettings.exe",

    # File Explorer (4)
    "file explorer closing":    "explorer.exe",
    "explorer closing":         "explorer.exe",
    "files closing":            "explorer.exe",
    "close file explorer":      "explorer.exe",
}


def check_and_execute(text: str) -> tuple[bool, str]:
    """
    Check if a voice command matches a close command.

    Args:
        text: Recognised speech text (lowercase).

    Returns:
        (handled: bool, message: str)
        handled = True means the command was consumed here.
    """
    text = text.lower().strip()
    for phrase, process in CLOSE_COMMANDS.items():
        if phrase in text:
            return _kill_process(process)
    return False, ""


def _kill_process(process_name: str) -> tuple[bool, str]:
    """Kill a Windows process by name using taskkill."""
    try:
        result = subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            name = process_name.replace(".exe", "")
            return True, f"Closed {name}"
        else:
            return True, f"Process {process_name} not running"
    except Exception as e:
        return True, f"Close failed: {e}"
