#!/usr/bin/env python3
"""
Debug wake word detection to understand why commands aren't working.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from speech.wake_word_detector import WakeWordDetector

def test_wake_word_detection():
    """Test wake word detection with various phrases."""
    print("=== Wake Word Detection Test ===")
    
    detector = WakeWordDetector(['hey assistant', 'ok assistant', 'hello system'], 0.75)
    
    test_phrases = [
        'hey assistant',
        'ok assistant', 
        'hello system',
        'hey computer',
        'hello there',
        'ok system',
        'hey',
        'assistant',
        'hello',
        'system'
    ]
    
    print("Testing wake word detection:")
    for phrase in test_phrases:
        detected, wake_word, confidence = detector.detect_wake_word(phrase)
        status = "DETECTED" if detected else "NOT DETECTED"
        print(f"  '{phrase}': {status} (confidence: {confidence:.2f})")
        if detected:
            print(f"    -> Matched: '{wake_word}'")

def test_intent_parsing():
    """Test intent parsing with various commands."""
    print("\n=== Intent Parsing Test ===")
    
    from brightness_control.brightness_intent_engine import BrightnessIntentEngine
    import json
    
    with open('config/commands.json', 'r') as f:
        commands_config = json.load(f)
    
    with open('config/voice_settings.json', 'r') as f:
        voice_config = json.load(f)
    
    intent_engine = BrightnessIntentEngine(commands_config, voice_config['noise_words'])
    
    test_commands = [
        'increase brightness',
        'brightness up',
        'decrease brightness',
        'brightness down',
        'set brightness 70',
        'brightness 50',
        'please increase brightness',
        'can you brightness up'
    ]
    
    print("Testing intent parsing:")
    for command in test_commands:
        result = intent_engine.parse_intent(command)
        print(f"  '{command}':")
        print(f"    Action: {result['action']}")
        print(f"    Value: {result['value']}")
        print(f"    Confidence: {result['confidence']:.2f}")

if __name__ == "__main__":
    test_wake_word_detection()
    test_intent_parsing()
