"""
Volume control module for Windows desktop automation.
Controls system audio volume using pycaw library with Windows Core Audio API.
"""

from .volume_controller import VolumeController
from .volume_intent_engine import VolumeIntentEngine

__all__ = ['VolumeController', 'VolumeIntentEngine']
