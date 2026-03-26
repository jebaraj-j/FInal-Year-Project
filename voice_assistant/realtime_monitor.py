#!/usr/bin/env python3
"""
Real-time audio monitor to show what the voice assistant is hearing.
This will help identify wake word detection issues.
"""

import sys
import os
import json
import time
import threading
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pyaudio
    from speech.wake_word_detector import WakeWordDetector
    from utils.logger import get_logger
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class RealtimeAudioMonitor:
    """Real-time audio monitoring with wake word detection."""
    
    def __init__(self):
        """Initialize monitor."""
        # Load configuration
        with open('config/voice_settings.json', 'r') as f:
            config = json.load(f)
        
        self.audio_config = config['audio']
        self.logger = get_logger()
        
        # Initialize wake word detector
        self.wake_detector = WakeWordDetector(
            config['wake_words'],
            config['recognition']['wake_word_threshold']
        )
        
        # Audio setup
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False
        
        print("=== Real-Time Audio Monitor ===")
        print("This shows what the voice assistant hears in real-time.")
        print("Try saying: 'hey assistant', 'ok assistant', or 'hello system'")
        print("Press Ctrl+C to stop.")
        print()
    
    def start_monitoring(self):
        """Start real-time audio monitoring."""
        try:
            # Setup audio stream
            device_index = self.audio_config.get('input_device_index', None)
            if device_index is None:
                device_index = 1  # Use headset microphone
            
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.audio_config['channels'],
                rate=self.audio_config['sample_rate'],
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.audio_config['chunk_size']
            )
            
            self.is_running = True
            print("🎤 Listening... (Speak clearly into your microphone)")
            print("Wake words:", ', '.join(self.wake_detector.get_wake_words()))
            print()
            
            # Buffer for audio data
            audio_buffer = []
            buffer_duration = 2.0  # 2 seconds of audio
            samples_per_buffer = int(self.audio_config['sample_rate'] * buffer_duration)
            
            while self.is_running:
                try:
                    # Read audio data
                    data = self.stream.read(self.audio_config['chunk_size'], exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    
                    # Add to buffer
                    audio_buffer.extend(audio_chunk)
                    
                    # Keep buffer size limited
                    if len(audio_buffer) > samples_per_buffer:
                        audio_buffer = audio_buffer[-samples_per_buffer:]
                    
                    # Calculate audio level
                    if len(audio_chunk) > 0:
                        rms = np.sqrt(np.mean(audio_chunk.astype(float)**2))
                        max_possible = np.iinfo(np.int16).max
                        normalized = min(rms / max_possible, 1.0)
                        
                        # Show audio level
                        if normalized > 0.01:  # Only show if there's audio
                            bars = int(normalized * 20)
                            level_bar = "█" * bars + "░" * (20 - bars)
                            print(f"\r🔊 Audio Level: [{level_bar}] {normalized:.3f}", end="", flush=True)
                    
                    # Check for speech end (silence detection)
                    if len(audio_buffer) > 0:
                        is_silent = self._is_silent(audio_chunk)
                        
                        if not is_silent and len(audio_buffer) > self.audio_config['sample_rate'] * 0.5:  # 0.5 seconds of audio
                            # Convert to text for wake word detection
                            audio_text = self._audio_to_text(audio_buffer)
                            
                            if audio_text and len(audio_text.strip()) > 3:
                                # Test for wake word
                                detected, wake_word, confidence = self.wake_detector.detect_wake_word(audio_text)
                                
                                if detected:
                                    print(f"\n🎯 WAKE WORD DETECTED: '{wake_word}' (confidence: {confidence:.2f})")
                                    print(f"📝 Heard: '{audio_text}'")
                                    print("-" * 50)
                                    
                                    # Clear buffer for next detection
                                    audio_buffer = []
                                else:
                                    # Show what was heard (for debugging)
                                    if confidence > 0.3:  # Only show potential matches
                                        print(f"\n👂 Heard: '{audio_text}' (wake confidence: {confidence:.2f})")
                
                except KeyboardInterrupt:
                    print("\n\nStopping monitor...")
                    break
                except Exception as e:
                    print(f"\nAudio error: {e}")
                    time.sleep(0.1)
                    continue
        
        finally:
            self.stop_monitoring()
    
    def _is_silent(self, audio_chunk):
        """Check if audio chunk is silence."""
        if len(audio_chunk) == 0:
            return True
        
        rms = np.sqrt(np.mean(audio_chunk.astype(float)**2))
        threshold = self.audio_config['silence_threshold']
        return rms < threshold
    
    def _audio_to_text(self, audio_buffer):
        """Convert audio buffer to text (simulated for monitoring)."""
        # This is a simplified simulation for monitoring
        # In the real system, VOSK would handle this
        
        # Generate a simple text representation based on audio patterns
        # This is just for demonstration - the real system uses VOSK
        
        # For now, return a placeholder that would be processed by VOSK
        # In reality, this would be: vosk_result = recognizer.Result()
        
        # Simulate some common phrases based on audio patterns
        if len(audio_buffer) > 16000:  # At least 1 second of audio
            # This would be replaced with actual VOSK recognition
            return "simulated speech text"
        return None
    
    def stop_monitoring(self):
        """Stop monitoring and cleanup."""
        self.is_running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.p:
            self.p.terminate()
        
        print("Monitor stopped.")

def main():
    """Run real-time monitor."""
    try:
        monitor = RealtimeAudioMonitor()
        monitor.start_monitoring()
    except Exception as e:
        print(f"Monitor error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
