#!/usr/bin/env python3
"""
Audio input diagnostic tool to check microphone and wake word detection.
"""

import sys
import os
import json
import time
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pyaudio
    import vosk
    from speech.wake_word_detector import WakeWordDetector
    from speech.audio_stream_manager import AudioStreamManager
    from utils.logger import get_logger
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class AudioCheck:
    """Diagnostic tool for audio input and wake word detection."""
    
    def __init__(self):
        """Initialize audio check."""
        # Load configuration
        with open('config/voice_settings.json', 'r') as f:
            self.config = json.load(f)
        
        self.logger = get_logger()
        
        # Initialize components
        self.wake_detector = WakeWordDetector(
            self.config['wake_words'],
            self.config['recognition']['wake_word_threshold']
        )
        
        # Audio setup
        self.audio_manager = AudioStreamManager(self.config['audio'])
        self.audio_manager.initialize_audio()
        
        print("=== Audio Input Diagnostic ===")
        print("This will test your microphone and wake word detection.")
        print()
    
    def check_microphone(self):
        """Check microphone input levels."""
        print("🎤 Checking microphone...")
        
        try:
            # Use AudioStreamManager's detection logic
            device_index = self.audio_manager.device_index
            self.audio_manager.list_audio_devices()
            
            print(f"\n🔊 Testing microphone (Device: {device_index})")
            print("Speak into your microphone for 5 seconds...")
            print("Audio level: ", end="", flush=True)
            
            # Start stream using the manager
            def dummy_callback(in_data, frame_count, time_info, status):
                return (None, pyaudio.paContinue)
            
            # Note: We'll read manually for the level test
            self.audio_manager.cleanup() # Reset to open in manual mode
            self.audio_manager.initialize_audio()
            self.audio_manager.stream = self.audio_manager.audio.open(
                format=self.audio_manager.format,
                channels=self.audio_manager.channels,
                rate=self.audio_manager.sample_rate,
                input=True,
                input_device_index=self.audio_manager.device_index,
                frames_per_buffer=self.audio_manager.chunk_size
            )
            self.audio_manager.is_streaming = True
            
            start_time = time.time()
            max_level = 0
            
            while time.time() - start_time < 5.0:
                try:
                    audio_data = self.audio_manager.read_chunk()
                    if audio_data is None: continue
                    
                    normalized = self.audio_manager.get_audio_level(audio_data)
                    
                    max_level = max(max_level, normalized)
                    
                    # Show level indicator
                    if normalized > 0.01:
                        bars = int(normalized * 10)
                        level_bar = "█" * bars + "░" * (10 - bars)
                        print(f"\rAudio level: [{level_bar}] {normalized:.3f}", end="", flush=True)
                
                except Exception as e:
                    print(f"\nAudio read error: {e}")
                    break
            
            print(f"\n\nMaximum audio level detected: {max_level:.3f}")
            
            if max_level < 0.01:
                print("⚠️  Very low audio level detected!")
                print("💡 Suggestions:")
                print("   - Check if microphone is muted")
                print("   - Speak closer to microphone")
                print("   - Check Windows microphone permissions")
                print("   - Try a different microphone")
            elif max_level < 0.05:
                print("⚠️  Low audio level - try speaking louder or closer")
            else:
                print("✅ Microphone working properly")
            
            return max_level > 0.01
            
        except Exception as e:
            print(f"❌ Microphone test failed: {e}")
            return False
    
    def check_vosk_recognition(self):
        """Check VOSK speech recognition."""
        print("\n🧠 Checking VOSK speech recognition...")
        
        try:
            # Load VOSK model
            model_path = self.config['recognition']['model_path']
            if not os.path.exists(model_path):
                print(f"❌ VOSK model not found: {model_path}")
                return False
            
            model = vosk.Model(model_path)
            recognizer = vosk.KaldiRecognizer(model, self.audio_manager.sample_rate)
            
            print("✅ VOSK model loaded successfully")
            
            # Test recognition
            print("🗣️  Say something (like 'hello world')...")
            captured_chunks = []
            start_time = time.time()
            
            # Use AudioStreamManager to read
            self.audio_manager.cleanup()
            self.audio_manager.initialize_audio()
            self.audio_manager.stream = self.audio_manager.audio.open(
                format=self.audio_manager.format,
                channels=self.audio_manager.channels,
                rate=self.audio_manager.sample_rate,
                input=True,
                input_device_index=self.audio_manager.device_index,
                frames_per_buffer=self.audio_manager.chunk_size
            )
            self.audio_manager.is_streaming = True
            
            while time.time() - start_time < 3.0:
                try:
                    chunk = self.audio_manager.read_chunk()
                    if chunk is not None:
                        captured_chunks.append(chunk.tobytes())
                        print(".", end="", flush=True)
                except:
                    break
            
            if captured_chunks:
                audio_bytes = b''.join(captured_chunks)
                
                if recognizer.AcceptWaveform(audio_bytes):
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        print(f"\n✅ Recognized: '{text}'")
                        return True
                    else:
                        print("\n❌ No speech recognized")
                        return False
                else:
                    partial = json.loads(recognizer.PartialResult())
                    partial_text = partial.get('partial', '')
                    print(f"\n🔄 Partial: '{partial_text}'")
                    return len(partial_text) > 0
            else:
                print("\n❌ No audio captured")
                return False
                
        except Exception as e:
            print(f"❌ VOSK test failed: {e}")
            return False
    
    def check_wake_words(self):
        """Check wake word detection."""
        print("\n🎯 Checking wake word detection...")
        
        test_phrases = [
            "hey assistant",
            "ok assistant",
            "hello system",
            "hello there",
            "hey computer"
        ]
        
        print("Testing wake word detection with sample phrases:")
        
        for phrase in test_phrases:
            detected, wake_word, confidence = self.wake_detector.detect_wake_word(phrase)
            status = "✅ DETECTED" if detected else "❌ NOT DETECTED"
            print(f"  '{phrase}': {status} (confidence: {confidence:.2f})")
            if detected:
                print(f"    → Matched: '{wake_word}'")
        
        return True
    
    def run_diagnostics(self):
        """Run all diagnostics."""
        try:
            # Check microphone
            mic_ok = self.check_microphone()
            
            # Check VOSK
            vosk_ok = self.check_vosk_recognition()
            
            # Check wake words
            wake_ok = self.check_wake_words()
            
            print("\n" + "="*50)
            print("📊 DIAGNOSTIC RESULTS:")
            print(f"Microphone: {'✅ OK' if mic_ok else '❌ ISSUE'}")
            print(f"VOSK Recognition: {'✅ OK' if vosk_ok else '❌ ISSUE'}")
            print(f"Wake Word Detection: {'✅ OK' if wake_ok else '❌ ISSUE'}")
            
            if mic_ok and vosk_ok and wake_ok:
                print("\n🎉 All systems working! The voice assistant should work properly.")
                print("💡 If it still doesn't respond, try:")
                print("   - Speaking more clearly")
                print("   - Reducing background noise")
                print("   - Using the main.py with optimized settings")
            else:
                print("\n⚠️  Issues detected. Check the failed components above.")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'audio_manager'):
            self.audio_manager.cleanup()

def main():
    """Run audio diagnostics."""
    try:
        checker = AudioCheck()
        checker.run_diagnostics()
    except Exception as e:
        print(f"Diagnostic error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
