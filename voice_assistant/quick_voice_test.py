#!/usr/bin/env python3
"""
Quick voice test to verify microphone and voice recognition are working.
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from speech.voice_listener import VoiceListener
from utils.logger import get_logger

def test_voice_listener():
    """Test voice listener functionality."""
    print("=== Quick Voice Test ===")
    print("Testing microphone and voice recognition...")
    print("Say something when prompted (10 seconds timeout)")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Load configuration
        import json
        with open('config/voice_settings.json', 'r') as f:
            config = json.load(f)
        
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

def test_microphone_info():
    """Test microphone information."""
    print("\n=== Microphone Information ===")
    
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        
        print("Available audio devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                device_type = "🎤 INPUT" if info['maxInputChannels'] > 0 else ""
                print(f"  {device_type} Device {i}: {info['name']}")
        
        p.terminate()
        return True
        
    except Exception as e:
        print(f"❌ Failed to get microphone info: {e}")
        return False

def main():
    """Run quick voice tests."""
    print("Voice Assistant - Quick Voice Test")
    print("=" * 40)
    
    # Test microphone info
    mic_test = test_microphone_info()
    
    # Test voice recognition
    voice_test = test_voice_listener()
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Microphone Test: {'✅ Passed' if mic_test else '❌ Failed'}")
    print(f"Voice Recognition: {'✅ Passed' if voice_test else '❌ Failed'}")
    
    if mic_test and voice_test:
        print("\n🎉 Voice system is working correctly!")
        print("You can now run: python full_voice_assistant.py")
    else:
        print("\n⚠️  Some issues detected. Check:")
        print("- Microphone permissions")
        print("- Audio device availability")
        print("- Background noise levels")

if __name__ == "__main__":
    main()
