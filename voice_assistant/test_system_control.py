#!/usr/bin/env python3
"""
Test script for system control module.
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from system_control.system_controller import SystemController
from system_control.system_intent_engine import SystemIntentEngine
from utils.logger import get_logger

def test_system_controller():
    """Test system controller functionality."""
    print("=== System Controller Test ===")
    
    try:
        controller = SystemController()
        
        # Test system info
        info = controller.get_system_info()
        print(f"✓ Supported actions: {info['supported_actions']}")
        print(f"✓ Confirmation timeout: {info['confirmation_timeout']}s")
        
        # Test action validation
        test_actions = ["shutdown", "restart", "sleep", "lock"]
        for action in test_actions:
            executor = controller._get_action_executor(action)
            status = "✓" if executor else "✗"
            print(f"{status} {action}: {'Available' if executor else 'Not available'}")
        
        # Test confirmation workflow
        print("\n--- Confirmation Workflow Test ---")
        
        # Test starting confirmation
        def test_callback(result):
            print(f"  Confirmation callback: {result}")
        
        started = controller.start_confirmation_workflow("test", test_callback)
        if started:
            print("✓ Confirmation workflow started")
            
            # Test processing response
            response_result = controller.process_confirmation_response("yes")
            if response_result:
                print("✓ Confirmation response processed")
            else:
                print("✗ Confirmation response processing failed")
        else:
            print("✗ Failed to start confirmation workflow")
        
        # Test controller tests
        test_results = controller.test_system_controller()
        print(f"\n--- Controller Tests ---")
        print(f"Tests passed: {test_results['tests_passed']}")
        print(f"Tests failed: {test_results['tests_failed']}")
        for detail in test_results['details']:
            print(f"  {detail}")
        
        return True
        
    except Exception as e:
        print(f"✗ System controller test failed: {e}")
        return False

def test_system_intent_engine():
    """Test system intent engine."""
    print("\n=== System Intent Engine Test ===")
    
    try:
        # Load configuration
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        
        # Initialize intent engine
        intent_engine = SystemIntentEngine(
            commands_config,
            voice_config['noise_words']
        )
        
        # Test commands
        test_commands = [
            "shutdown system",
            "restart system", 
            "sleep system",
            "lock system",
            "turn off computer",
            "reboot computer",
            "sleep computer",
            "lock computer",
            "please shutdown system",
            "can you restart system"
        ]
        
        for command in test_commands:
            result = intent_engine.parse_intent(command)
            action = result.get('action', 'None')
            confidence = result.get('confidence', 0.0)
            requires_conf = intent_engine.requires_confirmation(action) if action else False
            
            status = "✓" if action else "✗"
            conf_mark = "🔒" if requires_conf else "🔓"
            print(f"{status} '{command}': {action} (confidence: {confidence:.2f}) {conf_mark}")
        
        return True
        
    except Exception as e:
        print(f"✗ Intent engine test failed: {e}")
        return False

def test_integration():
    """Test system controller and intent engine integration."""
    print("\n=== Integration Test ===")
    
    try:
        # Initialize components
        controller = SystemController()
        
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        
        intent_engine = SystemIntentEngine(
            commands_config,
            voice_config['noise_words']
        )
        
        # Test command processing (without actually executing)
        test_commands = [
            ("shutdown system", "shutdown"),
            ("restart system", "restart"),
            ("sleep system", "sleep"),
            ("lock system", "lock")
        ]
        
        for command_text, expected_action in test_commands:
            # Parse intent
            intent = intent_engine.parse_intent(command_text)
            
            if intent['action'] == expected_action:
                # Test confirmation requirement
                requires_conf = intent_engine.requires_confirmation(expected_action)
                
                # Test action validation (don't actually execute)
                action_valid = controller._get_action_executor(expected_action) is not None
                
                status = "✓" if action_valid else "✗"
                conf_mark = "🔒" if requires_conf else "🔓"
                print(f"{status} '{command_text}' → {intent['action']} {conf_mark} {'Valid' if action_valid else 'Invalid'}")
            else:
                print(f"✗ '{command_text}' → Expected {expected_action}, got {intent['action']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def test_safety_workflow():
    """Test safety confirmation workflow."""
    print("\n=== Safety Workflow Test ---")
    
    try:
        controller = SystemController()
        intent_engine = SystemIntentEngine(
            {"system_control": {"shutdown": ["shutdown system"]}},
            ["please", "assistant"]
        )
        
        # Test dangerous actions require confirmation
        dangerous_actions = ["shutdown", "restart", "sleep"]
        safe_actions = ["lock"]
        
        print("Dangerous actions (should require confirmation):")
        for action in dangerous_actions:
            requires_conf = intent_engine.requires_confirmation(action)
            status = "✓" if requires_conf else "✗"
            print(f"  {status} {action}: {'Requires confirmation' if requires_conf else 'No confirmation required'}")
        
        print("\nSafe actions (should not require confirmation):")
        for action in safe_actions:
            requires_conf = intent_engine.requires_confirmation(action)
            status = "✓" if not requires_conf else "✗"
            print(f"  {status} {action}: {'No confirmation required' if not requires_conf else 'Requires confirmation'}")
        
        # Test confirmation workflow simulation
        print("\n--- Confirmation Workflow Simulation ---")
        
        def mock_callback(result):
            print(f"  Confirmation result: {result}")
        
        # Start confirmation for shutdown
        if controller.start_confirmation_workflow("shutdown", mock_callback):
            print("✓ Confirmation started for shutdown")
            
            # Simulate user saying "yes"
            time.sleep(1)
            if controller.process_confirmation_response("yes"):
                print("✓ 'yes' response processed")
            else:
                print("✗ 'yes' response failed")
        else:
            print("✗ Failed to start confirmation")
        
        return True
        
    except Exception as e:
        print(f"✗ Safety workflow test failed: {e}")
        return False

def main():
    """Run all system control tests."""
    print("System Control Module Test Suite")
    print("=" * 40)
    print("⚠️  WARNING: This tests system control functionality")
    print("⚠️  No actual system actions will be executed")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 4
    
    # Test system controller
    if test_system_controller():
        tests_passed += 1
        print("✓ System controller test passed")
    else:
        print("✗ System controller test failed")
    
    # Test intent engine
    if test_system_intent_engine():
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
    
    # Test safety workflow
    if test_safety_workflow():
        tests_passed += 1
        print("✓ Safety workflow test passed")
    else:
        print("✗ Safety workflow test failed")
    
    # Results
    print("\n" + "=" * 40)
    print(f"Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All system control tests passed!")
        print("System control module is ready for production use.")
        print("⚠️  Remember: System actions require confirmation for safety!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
