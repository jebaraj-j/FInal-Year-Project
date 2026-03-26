#!/usr/bin/env python3
"""
Direct voice test to bypass silence detection and test VOSK directly.
"""

import sys
import os
import json
import time
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyaudio
import vosk

def test_direct_vosk():
    """Test VOSK directly with microphone input."""
    print("=== Direct VOSK Test ===")
    print("Testing VOSK recognition without silence detection...")
    print("Speak clearly when prompted (5 seconds)")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Load config
        with open('config/voice_settings.json', 'r') as f:
            config = json.load(f)
        
        # Initialize VOSK
        model_path = config["recognition"]["model_path"]
        if not os.path.exists(model_path):
            print(f"❌ VOSK model not found at: {model_path}")
            return False
        
        model = vosk.Model(model_path)
        recognizer = vosk.KaldiRecognizer(model, config["audio"]["sample_rate"])
        
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Open audio stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=config["audio"]["channels"],
            rate=config["audio"]["sample_rate"],
            input=True,
            input_device_index=config["audio"]["input_device_index"],
            frames_per_buffer=config["audio"]["chunk_size"]
        )
        
        print("✅ VOSK and audio stream initialized")
        print("🎤 Recording for 5 seconds... Speak now!")
        
        # Record audio
        audio_data = []
        start_time = time.time()
        
        while time.time() - start_time < 5:
            try:
                data = stream.read(config["audio"]["chunk_size"], exception_on_overflow=False)
                audio_data.append(data)
                
                # Try to recognize in real-time
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '')
                    if text:
                        print(f"🎯 Real-time recognition: '{text}'")
                        return True
                        
            except Exception as e:
                print(f"❌ Audio read error: {e}")
                break
        
        # Process final audio
        if audio_data:
            print("🔄 Processing recorded audio...")
            final_result = recognizer.FinalResult()
            result = json.loads(final_result)
            text = result.get('text', '')
            
            if text:
                print(f"✅ Speech recognized: '{text}'")
                return True
            else:
                print("❌ No speech detected in final result")
                print(f"Debug: {result}")
                return False
        else:
            print("❌ No audio data recorded")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            stream.stop_stream()
            stream.close()
            p.terminate()
        except:
            pass

def test_microphone_levels():
    """Test microphone audio levels."""
    print("\n=== Microphone Level Test ===")
    
    try:
        import pyaudio
        import numpy as np
        
        p = pyaudio.PyAudio()
        
        # Open stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=0,
            frames_per_buffer=1024
        )
        
        print("🎤 Testing microphone levels for 3 seconds...")
        print("Speak normally and watch the levels:")
        
        start_time = time.time()
        max_level = 0
        
        while time.time() - start_time < 3:
            try:
                data = stream.read(1024, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate RMS
                rms = np.sqrt(np.mean(audio_data.astype(float)**2))
                max_possible = np.iinfo(np.int16).max
                normalized = min(rms / max_possible, 1.0)
                
                # Update max level
                max_level = max(max_level, normalized)
                
                # Show level bar
                bar_length = int(normalized * 50)
                bar = '█' * bar_length + '░' * (50 - bar_length)
                print(f"Level: [{bar}] {normalized:.3f}")
                
            except Exception as e:
                print(f"❌ Error reading audio: {e}")
                break
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        print(f"\n📊 Maximum level detected: {max_level:.3f}")
        
        if max_level > 0.001:
            print("✅ Microphone is working and picking up sound")
            return True
        else:
            print("❌ Microphone levels too low - check microphone")
            return False
            
    except Exception as e:
        print(f"❌ Level test failed: {e}")
        return False

def main():
    """Run direct voice tests."""
    print("Direct Voice Recognition Test")
    print("=" * 40)
    
    # Test microphone levels
    level_test = test_microphone_levels()
    
    # Test VOSK directly
    vosk_test = test_direct_vosk()
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Microphone Levels: {'✅ Passed' if level_test else '❌ Failed'}")
    print(f"VOSK Recognition: {'✅ Passed' if vosk_test else '❌ Failed'}")
    
    if level_test and vosk_test:
        print("\n🎉 Direct voice recognition is working!")
        print("The issue might be in the silence detection logic.")
    elif level_test:
        print("\n⚠️  Microphone works but VOSK has issues")
        print("Check VOSK model and audio format compatibility")
    else:
        print("\n❌ Microphone issues detected")
        print("Check microphone permissions and device selection")

if __name__ == "__main__":
    main()
