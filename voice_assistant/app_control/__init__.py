"""
Application launcher module for Windows desktop automation.
Launches applications using subprocess with path validation and error handling.
"""

from .app_launcher import ApplicationLauncher
from .app_intent_engine import AppIntentEngine

__all__ = ['ApplicationLauncher', 'AppIntentEngine']
