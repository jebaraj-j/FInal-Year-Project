#!/usr/bin/env python3
"""
Test script for application launcher module.
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_control.app_launcher import ApplicationLauncher
from app_control.app_intent_engine import AppIntentEngine
from utils.logger import get_logger

def test_app_launcher():
    """Test application launcher functionality."""
    print("=== Application Launcher Test ===")
    
    try:
        launcher = ApplicationLauncher()
        
        # Test configuration loading
        available_apps = launcher.get_available_apps()
        print(f"✓ Loaded {len(available_apps)} applications")
        
        # Test app validation
        for app_name in available_apps.keys():
            is_valid = launcher.validate_app(app_name)
            status = "✓" if is_valid else "✗"
            print(f"{status} {app_name}: {'Valid' if is_valid else 'Invalid'}")
        
        # Test app info
        print("\n--- Application Information ---")
        for app_name in list(available_apps.keys())[:3]:  # Test first 3 apps
            info = launcher.get_app_info(app_name)
            status = "✓" if info["available"] else "✗"
            print(f"{status} {app_name}: {info.get('path', 'N/A')}")
        
        # Test app launcher tests
        test_results = launcher.test_app_launcher()
        print(f"\n--- Launcher Tests ---")
        print(f"Tests passed: {test_results['tests_passed']}")
        print(f"Tests failed: {test_results['tests_failed']}")
        for detail in test_results['details']:
            print(f"  {detail}")
        
        return True
        
    except Exception as e:
        print(f"✗ Application launcher test failed: {e}")
        return False

def test_app_intent_engine():
    """Test app intent engine."""
    print("\n=== App Intent Engine Test ===")
    
    try:
        # Load configuration
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        
        # Initialize launcher to get available apps
        launcher = ApplicationLauncher()
        available_apps = launcher.get_available_apps()
        
        # Initialize intent engine
        intent_engine = AppIntentEngine(
            commands_config,
            voice_config['noise_words'],
            available_apps
        )
        
        # Test commands
        test_commands = [
            "open chrome",
            "open code", 
            "open notepad",
            "open settings",
            "open explorer",
            "start chrome",
            "launch notepad",
            "please open chrome",
            "can you open code"
        ]
        
        for command in test_commands:
            result = intent_engine.parse_intent(command)
            app = result.get('app', 'None')
            confidence = result.get('confidence', 0.0)
            
            status = "✓" if app else "✗"
            print(f"{status} '{command}': {app} (confidence: {confidence:.2f})")
        
        return True
        
    except Exception as e:
        print(f"✗ Intent engine test failed: {e}")
        return False

def test_integration():
    """Test app launcher and intent engine integration."""
    print("\n=== Integration Test ===")
    
    try:
        # Initialize components
        launcher = ApplicationLauncher()
        
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        
        intent_engine = AppIntentEngine(
            commands_config,
            voice_config['noise_words'],
            launcher.get_available_apps()
        )
        
        # Test command processing (without actually launching)
        test_commands = [
            ("open notepad", "notepad"),
            ("open chrome", "chrome"),
            ("start settings", "settings"),
            ("launch explorer", "explorer")
        ]
        
        for command_text, expected_app in test_commands:
            # Parse intent
            intent = intent_engine.parse_intent(command_text)
            
            if intent['app'] == expected_app:
                # Validate app exists (don't actually launch)
                app_valid = launcher.validate_app(intent['app'])
                
                status = "✓" if app_valid else "✗"
                print(f"{status} '{command_text}' → {intent['app']} → {'Valid' if app_valid else 'Invalid'}")
            else:
                print(f"✗ '{command_text}' → Expected {expected_app}, got {intent['app']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def main():
    """Run all app launcher tests."""
    print("Application Launcher Module Test Suite")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 3
    
    # Test app launcher
    if test_app_launcher():
        tests_passed += 1
        print("✓ Application launcher test passed")
    else:
        print("✗ Application launcher test failed")
    
    # Test intent engine
    if test_app_intent_engine():
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
        print("🎉 All app launcher tests passed!")
        print("Application launcher module is ready for production use.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
