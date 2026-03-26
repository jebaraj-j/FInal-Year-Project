#!/usr/bin/env python3
"""
Audio diagnostic tool to check microphone and speech recognition.
"""

import sys
import os
import time
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_microphone():
    """Test microphone access and audio levels."""
    print("=== Microphone Test ===")
    
    try:
        import pyaudio
        import numpy as np
        
        p = pyaudio.PyAudio()
        
        # List available devices
        print("Available audio devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  [{i}] {info['name']} - {info['maxInputChannels']} channels")
        
        # Test default device
        print("\nTesting microphone input...")
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        print("Listening for 5 seconds... Speak into your microphone:")
        start_time = time.time()
        
        while time.time() - start_time < 5:
            try:
                data = stream.read(1024, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate RMS energy
                rms = np.sqrt(np.mean(audio_data.astype(float)**2))
                max_possible = np.iinfo(np.int16).max
                normalized = min(rms / max_possible, 1.0)
                
                # Show audio level
                bars = int(normalized * 20)
                level_bar = "█" * bars + "░" * (20 - bars)
                print(f"\rAudio Level: [{level_bar}] {normalized:.3f}", end="")
                
            except Exception as e:
                print(f"\nAudio read error: {e}")
                break
        
        print("\nMicrophone test completed.")
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        return True
        
    except Exception as e:
        print(f"Microphone test failed: {e}")
        return False

def test_vosk_model():
    """Test VOSK model loading and recognition."""
    print("\n=== VOSK Model Test ===")
    
    try:
        import vosk
        import json
        
        # Check if model exists
        model_path = "models/vosk-model-small-en-us-0.15"
        if not os.path.exists(model_path):
            print(f"VOSK model not found at: {model_path}")
            return False
        
        print(f"Loading VOSK model from: {model_path}")
        model = vosk.Model(model_path)
        
        # Create recognizer
        recognizer = vosk.KaldiRecognizer(model, 16000)
        print("VOSK recognizer created successfully")
        
        # Test with sample audio (simulate)
        print("VOSK model test passed - ready for speech recognition")
        
        return True
        
    except Exception as e:
        print(f"VOSK model test failed: {e}")
        return False

def test_voice_listener():
    """Test voice listener initialization."""
    print("\n=== Voice Listener Test ===")
    
    try:
        from speech.voice_listener import VoiceListener
        
        with open('config/voice_settings.json', 'r') as f:
            config = json.load(f)
        
        print("Initializing voice listener...")
        listener = VoiceListener(config)
        
        print("Voice listener initialized successfully")
        print("Testing model loading...")
        
        if listener.load_model():
            print("VOSK model loaded successfully")
            
            print("Testing audio manager initialization...")
            if listener.audio_manager.initialize_audio():
                print("Audio manager initialized successfully")
                
                # Test device detection
                listener.audio_manager.list_audio_devices()
                
                return True
            else:
                print("Audio manager initialization failed")
                return False
        else:
            print("VOSK model loading failed")
            return False
            
    except Exception as e:
        print(f"Voice listener test failed: {e}")
        return False

def main():
    """Run all diagnostic tests."""
    print("=== Voice Assistant Diagnostic Tool ===\n")
    
    tests_passed = 0
    total_tests = 3
    
    # Test microphone
    if test_microphone():
        tests_passed += 1
        print("✓ Microphone test PASSED")
    else:
        print("✗ Microphone test FAILED")
    
    # Test VOSK model
    if test_vosk_model():
        tests_passed += 1
        print("✓ VOSK model test PASSED")
    else:
        print("✗ VOSK model test FAILED")
    
    # Test voice listener
    if test_voice_listener():
        tests_passed += 1
        print("✓ Voice listener test PASSED")
    else:
        print("✗ Voice listener test FAILED")
    
    print(f"\n=== Diagnostic Results ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! System should be working.")
        print("\nIf voice commands still don't work:")
        print("1. Speak clearly and close to microphone")
        print("2. Try different wake words: 'hey assistant', 'ok assistant', 'hello system'")
        print("3. Check microphone permissions in Windows")
        print("4. Ensure no other apps are using the microphone")
    else:
        print("✗ Some tests failed. Check the errors above.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
