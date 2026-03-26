"""
System control module for Windows desktop automation.
Controls system operations (shutdown, restart, sleep, lock) with safety confirmation.
"""

from .system_controller import SystemController
from .system_intent_engine import SystemIntentEngine

__all__ = ['SystemController', 'SystemIntentEngine']
