#!/usr/bin/env python3
"""
Real-time monitoring mode to see what the voice assistant is hearing and processing.
"""

import sys
import os
import time
import json
import threading
import queue
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from speech.voice_listener import VoiceListener
from brightness_control.brightness_intent_engine import BrightnessIntentEngine
from brightness_control.brightness_controller import BrightnessController
from utils.logger import get_logger

class VoiceMonitor:
    """Real-time voice assistant monitor with detailed feedback."""
    
    def __init__(self):
        """Initialize monitor."""
        # Load configuration
        with open('config/voice_settings.json', 'r') as f:
            voice_config = json.load(f)
        with open('config/commands.json', 'r') as f:
            commands_config = json.load(f)
        
        # Initialize components
        self.voice_listener = VoiceListener(voice_config)
        self.intent_engine = BrightnessIntentEngine(
            commands_config, 
            voice_config['noise_words']
        )
        self.brightness_controller = BrightnessController()
        self.logger = get_logger()
        
        # Monitoring state
        self.is_running = False
        self.audio_queue = queue.Queue()
        
        print("=== Voice Assistant Monitor Mode ===")
        print("This will show real-time audio processing and recognition results.")
        print()
    
    def start_monitoring(self):
        """Start real-time monitoring."""
        print("Starting voice assistant monitoring...")
        print("Speak clearly into your microphone.")
        print("Try saying: 'hey assistant' followed by 'increase brightness'")
        print("Press Ctrl+C to stop.")
        print()
        
        # Start voice listener
        if not self.voice_listener.start_listening():
            print("Failed to start voice listener!")
            return
        
        self.is_running = True
        
        try:
            while self.is_running:
                # Listen for commands with shorter timeout for responsive monitoring
                result = self.voice_listener.listen(timeout=2.0)
                
                if result["status"] == "success":
                    print(f"🎤 RECOGNIZED: '{result['text']}' (confidence: {result['confidence']:.2f})")
                    
                    # Parse intent
                    intent = self.intent_engine.parse_intent(result['text'])
                    print(f"🧠 INTENT: {intent['action']} (confidence: {intent['confidence']:.2f})")
                    
                    if intent['action']:
                        # Execute command
                        success = self.brightness_controller.execute_action(
                            intent['action'], 
                            intent['value']
                        )
                        if success:
                            print(f"✅ EXECUTED: {intent['action']}")
                        else:
                            print(f"❌ FAILED: {intent['action']}")
                    else:
                        print("❓ NO INTENT DETECTED")
                    
                    print("-" * 50)
                    
                elif result["status"] == "timeout":
                    # Show we're still listening
                    print(".", end="", flush=True)
                    
                elif result["status"] == "error":
                    print(f"🔴 ERROR: {result.get('text', 'Unknown error')}")
                
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.is_running = False
        self.voice_listener.stop_listening()
        print("Monitor stopped.")

def main():
    """Run monitor mode."""
    try:
        monitor = VoiceMonitor()
        monitor.start_monitoring()
    except Exception as e:
        print(f"Monitor error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
