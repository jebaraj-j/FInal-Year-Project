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
import re


# Map trigger phrases → process name to kill
CLOSE_COMMANDS = {
    # VS Code (4)


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

# Compact keyword patterns so recognition is less phrase-sensitive.
# This accepts variations like:
# - "close chrome"
# - "chrome close now"
# - "please close file explorer"
PROCESS_KEYWORD_RULES = {
    "chrome.exe": [
        {"open chrome", "close chorme"},
        
    ],
    "notepad.exe": [
        {"open notepad", "close notepad"},
       
    ],
    "SystemSettings.exe": [
        {"open settings", "close setting"},
        
    ],
    "explorer.exe": [
        {" open file explorer", "close file explorer"},
        
        
    ],
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


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

    # 1) Keep exact phrase support for backward compatibility.
    for phrase, process in CLOSE_COMMANDS.items():
        if phrase in text:
            return _kill_process(process)

    # 2) Less phrase-sensitive fallback using keyword rules.
    tokens = _tokenize(text)
    for process, keyword_sets in PROCESS_KEYWORD_RULES.items():
        for keywords in keyword_sets:
            if keywords.issubset(tokens):
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
