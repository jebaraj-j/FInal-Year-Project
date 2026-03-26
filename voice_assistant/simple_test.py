#!/usr/bin/env python3
"""
Simple voice test to debug recognition issues.
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def simple_voice_test():
    """Test voice recognition with detailed feedback."""
    print("=== Simple Voice Recognition Test ===")
    print("This will test if VOSK can recognize your speech.")
    print("Press Enter to start recording, speak, then press Enter again.")
    print()
    
    try:
        import vosk
        import pyaudio
        import numpy as np
        
        # Load config
        with open('config/voice_settings.json', 'r') as f:
            config = json.load(f)
        
        # Initialize VOSK
        model_path = config['recognition']['model_path']
        print(f"Loading VOSK model: {model_path}")
        model = vosk.Model(model_path)
        recognizer = vosk.KaldiRecognizer(model, 16000)
        
        # Initialize audio
        p = pyaudio.PyAudio()
        
        # Use the same device as main app
        device_index = config['audio'].get('input_device_index', None)
        if device_index is None:
            device_index = 1  # Use headset microphone by default
        
        print(f"Using audio device: {device_index}")
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        
        print("\n🎤 Ready to test!")
        print("1. Press Enter to start recording")
        print("2. Say a command like 'increase brightness'")
        print("3. Press Enter again to stop recording")
        print("4. Press Ctrl+C to exit")
        print()
        
        while True:
            input("Press Enter to start recording...")
            print("🔴 Recording... Speak now!")
            
            # Start recording
            audio_data = []
            start_time = time.time()
            max_duration = 5.0  # 5 seconds max
            
            while time.time() - start_time < max_duration:
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    audio_data.append(data)
                    
                    # Show recording indicator
                    print(".", end="", flush=True)
                    
                except Exception as e:
                    print(f"\nRecording error: {e}")
                    break
            
            print("\n🔵 Processing speech...")
            
            # Process the recorded audio
            if audio_data:
                audio_bytes = b''.join(audio_data)
                
                if recognizer.AcceptWaveform(audio_bytes):
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        print(f"✅ RECOGNIZED: '{text}'")
                        
                        # Test intent parsing
                        from brightness_control.brightness_intent_engine import BrightnessIntentEngine
                        with open('config/commands.json', 'r') as f:
                            commands_config = json.load(f)
                        
                        intent_engine = BrightnessIntentEngine(
                            commands_config, 
                            config['noise_words']
                        )
                        
                        intent = intent_engine.parse_intent(text)
                        print(f"🧠 INTENT: {intent['action']} (confidence: {intent['confidence']:.2f})")
                        
                        if intent['action']:
                            print(f"✅ This would execute: {intent['action']} with value: {intent['value']}")
                        else:
                            print("❌ No valid intent detected")
                    else:
                        print("❌ No speech recognized")
                else:
                    partial = json.loads(recognizer.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        print(f"🔄 Partial recognition: '{partial_text}'")
                    else:
                        print("❌ No speech recognized")
            else:
                print("❌ No audio recorded")
            
            print("\n" + "="*50 + "\n")
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            stream.stop_stream()
            stream.close()
            p.terminate()
        except:
            pass

if __name__ == "__main__":
    simple_voice_test()
