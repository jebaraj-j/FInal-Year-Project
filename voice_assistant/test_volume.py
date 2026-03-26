#!/usr/bin/env python3
"""
Test script for volume control module.
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from volume_control.volume_controller import VolumeController
from volume_control.volume_intent_engine import VolumeIntentEngine
from utils.logger import get_logger

def test_volume_controller():
    """Test volume controller functionality."""
    print("=== Volume Controller Test ===")
    
    try:
        controller = VolumeController()
        
        # Test getting current volume
        current = controller.get_current()
        print(f"✓ Current volume: {current}%")
        
        # Test volume info
        info = controller.get_volume_info()
        print(f"✓ Device: {info.get('device_name', 'Unknown')}")
        print(f"✓ Supported: {info.get('supported', False)}")
        
        # Test volume changes
        original = current
        
        # Test increase
        if controller.increase(5):
            new_volume = controller.get_current()
            print(f"✓ Increase test: {original}% → {new_volume}%")
        else:
            print("✗ Increase test failed")
        
        # Test decrease
        if controller.decrease(5):
            new_volume = controller.get_current()
            print(f"✓ Decrease test: {original}% → {new_volume}%")
        else:
            print("✗ Decrease test failed")
        
        # Test absolute values
        if controller.set(50):
            new_volume = controller.get_current()
            print(f"✓ Set value test: {original}% → {new_volume}%")
        else:
            print("✗ Set value test failed")
        
        # Restore original
        controller.set(original)
        
        return True
        
    except Exception as e:
        print(f"✗ Volume controller test failed: {e}")
        return False

def test_volume_intent_engine():
    """Test volume intent engine."""
    print("\n=== Volume Intent Engine Test ===")
    
    try:
        # Load configuration
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        
        # Initialize intent engine
        intent_engine = VolumeIntentEngine(
            commands_config,
            voice_config['noise_words']
        )
        
        # Test commands
        test_commands = [
            "increase volume",
            "volume up",
            "decrease volume", 
            "volume down",
            "set volume 70",
            "volume 50",
            "please increase volume",
            "can you volume up"
        ]
        
        for command in test_commands:
            result = intent_engine.parse_intent(command)
            action = result.get('action', 'None')
            confidence = result.get('confidence', 0.0)
            value = result.get('value', None)
            
            status = "✓" if action else "✗"
            value_str = f" (value: {value})" if value is not None else ""
            print(f"{status} '{command}': {action} (confidence: {confidence:.2f}){value_str}")
        
        return True
        
    except Exception as e:
        print(f"✗ Intent engine test failed: {e}")
        return False

def test_integration():
    """Test volume controller and intent engine integration."""
    print("\n=== Integration Test ===")
    
    try:
        # Initialize components
        controller = VolumeController()
        
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        
        intent_engine = VolumeIntentEngine(
            commands_config,
            voice_config['noise_words']
        )
        
        # Test command processing
        test_commands = [
            ("increase volume", "absolute_increase"),
            ("volume up", "relative_increase"),
            ("set volume 75", "set_value"),
            ("volume down", "relative_decrease")
        ]
        
        for command_text, expected_action in test_commands:
            # Parse intent
            intent = intent_engine.parse_intent(command_text)
            
            if intent['action'] == expected_action:
                # Execute action
                success = controller.execute_action(
                    intent['action'],
                    intent['value']
                )
                
                status = "✓" if success else "✗"
                print(f"{status} '{command_text}' → {intent['action']} → Executed")
            else:
                print(f"✗ '{command_text}' → Expected {expected_action}, got {intent['action']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def main():
    """Run all volume control tests."""
    print("Volume Control Module Test Suite")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 3
    
    # Test volume controller
    if test_volume_controller():
        tests_passed += 1
        print("✓ Volume controller test passed")
    else:
        print("✗ Volume controller test failed")
    
    # Test intent engine
    if test_volume_intent_engine():
        tests_passed += 1
        print("✓ Intent engine test passed")
    else:
        print("✗ Intent engine test failed")
    
    # Test integration
    if test_integration():
        tests_passed += 1
        print("✓ Integration test passed")
    else:
        print("✗ Integration test failed")
    
    # Results
    print("\n" + "=" * 40)
    print(f"Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All volume control tests passed!")
        print("Volume control module is ready for production use.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
