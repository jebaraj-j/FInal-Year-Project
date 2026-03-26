#!/usr/bin/env python3
"""
Test voice listener with bypassed silence detection.
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from speech.voice_listener import VoiceListener
from utils.logger import get_logger

def test_voice_bypass():
    """Test voice listener with bypassed silence detection."""
    print("=== Voice Bypass Test ===")
    print("Testing voice listener with disabled silence detection...")
    print("Say something when prompted (10 seconds timeout)")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Load configuration
        with open('config/voice_settings.json', 'r') as f:
            config = json.load(f)
        
        # Disable silence detection by setting very low threshold
        config["audio"]["silence_threshold"] = 0.0001
        
        # Initialize voice listener
        listener = VoiceListener(config)
        
        # Start listening
        if not listener.start_listening():
            print("❌ Failed to start voice listener")
            return False
        
        print("✅ Voice listener started successfully")
        print("🎤 Listening... Say something now!")
        
        # Test listening
        result = listener.listen(timeout=10.0)
        
        if result["status"] == "success":
            text = result.get("text", "")
            confidence = result.get("confidence", 0.0)
            print(f"✅ Speech recognized: '{text}' (confidence: {confidence:.2f})")
            return True
        elif result["status"] == "timeout":
            print("⏰ Timeout: No speech detected")
            return False
        elif result["status"] == "error":
            error = result.get("text", "Unknown error")
            print(f"❌ Recognition error: {error}")
            return False
        
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            listener.cleanup()
            print("🧹 Cleanup completed")
        except:
            pass

def main():
    """Run voice bypass test."""
    print("Voice Assistant - Bypass Silence Detection Test")
    print("=" * 50)
    
    # Test with bypassed silence detection
    bypass_test = test_voice_bypass()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Voice Bypass Test: {'✅ Passed' if bypass_test else '❌ Failed'}")
    
    if bypass_test:
        print("\n🎉 Voice recognition works with bypassed silence detection!")
        print("The issue is definitely in the silence detection logic.")
        print("Recommendation: Adjust silence_threshold in voice_settings.json")
    else:
        print("\n❌ Even bypassed silence detection failed")
        print("There might be a deeper issue with the voice listener")

if __name__ == "__main__":
    main()
