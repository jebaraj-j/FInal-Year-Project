#!/usr/bin/env python3
"""
Quick responsive test for voice commands with optimized settings.
"""

import sys
import os
import json
import time
import threading
import queue
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from speech.voice_listener import VoiceListener
from brightness_control.brightness_intent_engine import BrightnessIntentEngine
from brightness_control.brightness_controller import BrightnessController
from utils.logger import get_logger

class QuickVoiceTest:
    """Quick and responsive voice test with minimal lag."""
    
    def __init__(self):
        """Initialize quick test."""
        # Load optimized configuration
        with open('config/voice_settings.json', 'r') as f:
            self.config = json.load(f)
        
        # Override with even more responsive settings
        self.config['audio']['chunk_size'] = 256  # Smaller chunks for less lag
        self.config['audio']['silence_timeout'] = 0.3  # Faster detection
        self.config['recognition']['wake_word_threshold'] = 0.6  # More sensitive
        
        # Initialize components
        self.voice_listener = VoiceListener(self.config)
        self.intent_engine = BrightnessIntentEngine(
            self._load_commands_config(),
            self.config['noise_words']
        )
        self.brightness_controller = BrightnessController()
        self.logger = get_logger()
        
        print("=== Quick Voice Test (Optimized for Speed) ===")
        print("Wake words:", ', '.join(self.config['wake_words']))
        print("Commands: 'increase brightness', 'brightness up', 'set brightness 70', etc.")
        print("Press Ctrl+C to stop.")
        print()
    
    def _load_commands_config(self):
        """Load commands configuration."""
        with open('config/commands.json', 'r') as f:
            return json.load(f)
    
    def start_test(self):
        """Start quick voice test."""
        print("🚀 Starting optimized voice test...")
        
        # Start voice listener
        if not self.voice_listener.start_listening():
            print("❌ Failed to start voice listener!")
            return
        
        try:
            print("✅ Voice listener started - Say wake word now!")
            print("💡 Try speaking clearly and close to microphone")
            print()
            
            command_count = 0
            
            while True:
                # Listen with shorter timeout for responsiveness
                result = self.voice_listener.listen(timeout=1.5)
                
                if result["status"] == "success":
                    command_count += 1
                    print(f"🎤 Command #{command_count}: '{result['text']}'")
                    
                    # Parse intent
                    intent = self.intent_engine.parse_intent(result['text'])
                    
                    if intent['action']:
                        print(f"🧠 Action: {intent['action']} (confidence: {intent['confidence']:.2f})")
                        
                        # Execute command
                        success = self.brightness_controller.execute_action(
                            intent['action'], 
                            intent['value']
                        )
                        
                        if success:
                            print(f"✅ Executed: {intent['action']}")
                        else:
                            print(f"❌ Failed: {intent['action']}")
                    else:
                        print("❓ No valid intent detected")
                    
                    print("-" * 40)
                    
                elif result["status"] == "timeout":
                    # Show we're still listening
                    print(".", end="", flush=True)
                    
                elif result["status"] == "error":
                    print(f"🔴 Error: {result.get('text', 'Unknown error')}")
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\nStopping test...")
        finally:
            self.stop_test()
    
    def stop_test(self):
        """Stop test and cleanup."""
        self.voice_listener.stop_listening()
        print("Test stopped.")

def main():
    """Run quick voice test."""
    try:
        test = QuickVoiceTest()
        test.start_test()
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
