#!/usr/bin/env python3
"""
Quick startup test to verify all components can initialize.
"""

import sys
import json
from pathlib import Path

def test_config():
    """Test configuration loading."""
    print("Testing configuration...")
    
    try:
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        print("✓ Voice settings loaded")
        
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        print("✓ Commands config loaded")
        
        return voice_config, commands_config
    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        return None, None

def test_imports():
    """Test all module imports."""
    print("\nTesting imports...")
    
    try:
        from utils.logger import get_logger
        print("✓ Logger imported")
        
        from speech.audio_stream_manager import AudioStreamManager
        print("✓ AudioStreamManager imported")
        
        from speech.wake_word_detector import WakeWordDetector
        print("✓ WakeWordDetector imported")
        
        from speech.voice_listener import VoiceListener
        print("✓ VoiceListener imported")
        
        from brightness_control.brightness_intent_engine import BrightnessIntentEngine
        print("✓ BrightnessIntentEngine imported")
        
        from brightness_control.brightness_controller import BrightnessController
        print("✓ BrightnessController imported")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_components():
    """Test component initialization."""
    print("\nTesting component initialization...")
    
    try:
        voice_config, commands_config = test_config()
        if not voice_config or not commands_config:
            return False
        
        # Test logger
        from utils.logger import get_logger
        logger = get_logger()
        print("✓ Logger initialized")
        
        # Test wake word detector
        from speech.wake_word_detector import WakeWordDetector
        wake_detector = WakeWordDetector(
            voice_config["wake_words"],
            voice_config["recognition"]["wake_word_threshold"]
        )
        print("✓ WakeWordDetector initialized")
        
        # Test intent engine
        from brightness_control.brightness_intent_engine import BrightnessIntentEngine
        intent_engine = BrightnessIntentEngine(
            commands_config,
            voice_config["noise_words"]
        )
        print("✓ BrightnessIntentEngine initialized")
        
        # Test brightness controller
        from brightness_control.brightness_controller import BrightnessController
        brightness_controller = BrightnessController()
        print("✓ BrightnessController initialized")
        
        # Test wake word detection
        detected, wake_word, confidence = wake_detector.detect_wake_word("hey assistant")
        if detected:
            print("✓ Wake word detection working")
        else:
            print("✗ Wake word detection failed")
        
        # Test intent parsing
        intent = intent_engine.parse_intent("increase brightness")
        if intent["action"] == "absolute_increase":
            print("✓ Intent parsing working")
        else:
            print("✗ Intent parsing failed")
        
        # Test brightness info
        brightness_info = brightness_controller.get_brightness_info()
        if brightness_info.get("supported", False):
            print("✓ Brightness control supported")
        else:
            print("⚠ Brightness control not supported (may be normal)")
        
        return True
        
    except Exception as e:
        print(f"✗ Component initialization failed: {e}")
        return False

def main():
    """Run all startup tests."""
    print("=== Voice Assistant Startup Test ===\n")
    
    success = True
    
    # Test imports first
    if not test_imports():
        success = False
    
    # Test components
    if not test_components():
        success = False
    
    print(f"\n=== Test Result ===")
    if success:
        print("✓ All tests passed! System is ready to use.")
        print("\nTo start the voice assistant:")
        print("  python main.py")
        print("\nTo run in test mode:")
        print("  python main.py --test")
    else:
        print("✗ Some tests failed. Please check the issues above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
