"""
Main execution loop for voice-controlled desktop automation.
Coordinates voice listener, intent engines, and controllers for brightness and volume.
"""

import json
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from speech.voice_listener import VoiceListener
from brightness_control.brightness_intent_engine import BrightnessIntentEngine
from brightness_control.brightness_controller import BrightnessController
from nlp.volume_intent_engine import VolumeIntentEngine
from controllers.volume_controller import VolumeController
from utils.logger import get_logger


class VoiceAssistant:
    """
    Main voice assistant class for desktop automation.
    Manages complete workflow from wake word detection to system control.
    Supports both brightness and volume control.
    """
    
    def __init__(self):
        """Initialize voice assistant."""
        # Load configuration
        self.config = self._load_config()
        
        # Initialize logger
        log_level = self.config["logging"]["level"]
        log_dir = Path(__file__).parent / "logs"
        self.logger = get_logger(str(log_dir), log_level)
        
        # Initialize components
        self.voice_listener = VoiceListener(self.config)
        
        # Initialize intent engines
        commands_config = self._load_commands_config()
        self.brightness_intent_engine = BrightnessIntentEngine(
            commands_config,
            self.config["noise_words"]
        )
        self.volume_intent_engine = VolumeIntentEngine(
            commands_config,
            self.config["noise_words"]
        )
        
        # Initialize controllers
        self.brightness_controller = BrightnessController()
        self.volume_controller = VolumeController()
        
        # Runtime state
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("VoiceAssistant initialized")
        self.logger.info("Supported modules: brightness, volume")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load voice settings configuration."""
        try:
            with open('config/voice_settings.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.log_error("ConfigLoadError", str(e))
            sys.exit(1)
    
    def _load_commands_config(self) -> Dict[str, Any]:
        """Load commands configuration."""
        try:
            with open('config/commands.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.log_error("CommandsConfigLoadError", str(e))
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def _detect_intent_type(self, text: str) -> str:
        """
        Detect which intent type the command belongs to.
        
        Args:
            text: Recognized speech text
            
        Returns:
            Intent type: "brightness", "volume", or None
        """
        text_lower = text.lower()
        
        # Check for brightness keywords
        brightness_config = self.config.get("commands", {}).get("brightness", {})
        brightness_keywords = brightness_config.get("keywords", ["brightness", "bright"])
        
        # Check for volume keywords
        volume_config = self.config.get("commands", {}).get("volume", {})
        volume_keywords = volume_config.get("keywords", ["volume", "sound"])
        
        # Priority-based detection
        for keyword in brightness_keywords:
            if keyword in text_lower:
                return "brightness"
        
        for keyword in volume_keywords:
            if keyword in text_lower:
                return "volume"
        
        # If no keywords found, try both intent engines
        brightness_intent = self.brightness_intent_engine.parse_intent(text)
        volume_intent = self.volume_intent_engine.parse_intent(text)
        
        # Use the one with higher confidence
        if brightness_intent["confidence"] > volume_intent["confidence"]:
            return "brightness" if brightness_intent["action"] else None
        elif volume_intent["confidence"] > 0.6:
            return "volume"
        
        return None
    
    def _process_command(self, text: str) -> bool:
        """
        Process voice command and execute appropriate action.
        
        Args:
            text: Recognized speech text
            
        Returns:
            True if command was processed successfully, False otherwise
        """
        try:
            # Detect intent type
            intent_type = self._detect_intent_type(text)
            
            if not intent_type:
                self.logger.warning(f"No intent type detected for: '{text}'")
                return False
            
            # Route to appropriate intent engine
            if intent_type == "brightness":
                intent = self.brightness_intent_engine.parse_intent(text)
                if intent["action"]:
                    return self.brightness_controller.execute_action(
                        intent["action"], 
                        intent["value"]
                    )
                else:
                    self.logger.warning(f"No brightness action detected for: '{text}'")
                    return False
            
            elif intent_type == "volume":
                intent = self.volume_intent_engine.parse_intent(text)
                if intent["action"]:
                    return self.volume_controller.execute_action(
                        intent["action"], 
                        intent["value"]
                    )
                else:
                    self.logger.warning(f"No volume action detected for: '{text}'")
                    return False
            
            else:
                self.logger.warning(f"Unknown intent type: {intent_type}")
                return False
                
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e), f"Text: {text}")
            return False
    
    def start(self):
        """Start the voice assistant."""
        self.logger.info("Starting voice assistant...")
        
        # Start voice listener
        if not self.voice_listener.start_listening():
            self.logger.error("Failed to start voice listener!")
            return
        
        self.is_running = True
        self.logger.info("Voice assistant started successfully")
        self.logger.info(f"Listening for wake words: {', '.join(self.config['wake_words'])}")
        
        try:
            while self.is_running:
                # Listen for wake word
                result = self.voice_listener.listen_for_wake_word()
                
                if result["status"] == "wake_word_detected":
                    wake_word = result.get("wake_word", "unknown")
                    confidence = result.get("confidence", 0.0)
                    
                    self.logger.info(f"Wake word detected: '{wake_word}' (confidence: {confidence:.2f})")
                    print(f"Wake word detected: {wake_word}")
                    
                    # Enter active listening mode for command
                    command_result = self.voice_listener.listen_for_command(
                        timeout=self.config["recognition"]["active_listening_timeout"]
                    )
                    
                    if command_result["status"] == "success":
                        command_text = command_result.get("text", "").strip()
                        if command_text:
                            self.logger.info(f"Command received: '{command_text}'")
                            print(f"Command: {command_text}")
                            
                            # Process the command
                            success = self._process_command(command_text)
                            
                            if success:
                                self.logger.info("Command executed successfully")
                                print("✅ Command executed successfully")
                            else:
                                self.logger.warning("Command execution failed")
                                print("❌ Command execution failed")
                        else:
                            self.logger.info("No command detected")
                            print("No command detected")
                    
                    elif command_result["status"] == "timeout":
                        self.logger.info("Active listening timeout")
                        print("Timeout: No command received")
                    
                    elif command_result["status"] == "error":
                        error = command_result.get("text", "Unknown error")
                        self.logger.log_error("CommandError", error)
                        print(f"Error: {error}")
                
                elif result["status"] == "error":
                    error = result.get("text", "Unknown error")
                    self.logger.log_error("WakeWordError", error)
                    print(f"Wake word error: {error}")
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the voice assistant gracefully."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Shutting down voice assistant...")
        
        # Stop voice listener
        self.voice_listener.stop_listening()
        
        # Cleanup controllers
        if hasattr(self.volume_controller, 'cleanup'):
            self.volume_controller.cleanup()
        
        self.logger.info("Voice assistant shutdown complete")
    
    def run_tests(self):
        """Run system tests for all modules."""
        print("=== Voice Assistant System Tests ===")
        
        # Test brightness controller
        print("\n--- Brightness Controller Test ---")
        brightness_test = self.brightness_controller.test_brightness_control()
        print(f"Tests passed: {brightness_test['tests_passed']}")
        print(f"Tests failed: {brightness_test['tests_failed']}")
        for detail in brightness_test['details']:
            print(f"  {detail}")
        
        # Test volume controller
        print("\n--- Volume Controller Test ---")
        volume_test = self.volume_controller.test_volume_control()
        print(f"Tests passed: {volume_test['tests_passed']}")
        print(f"Tests failed: {volume_test['tests_failed']}")
        for detail in volume_test['details']:
            print(f"  {detail}")
        
        # Test intent engines
        print("\n--- Brightness Intent Engine Test ---")
        brightness_commands = [
            "increase brightness",
            "brightness up",
            "decrease brightness",
            "brightness down",
            "set brightness 75"
        ]
        
        for cmd in brightness_commands:
            result = self.brightness_intent_engine.parse_intent(cmd)
            print(f"'{cmd}': {result['action']} (confidence: {result['confidence']:.2f})")
        
        print("\n--- Volume Intent Engine Test ---")
        volume_commands = [
            "increase volume",
            "volume up",
            "decrease volume",
            "volume down",
            "set volume 50"
        ]
        
        for cmd in volume_commands:
            result = self.volume_intent_engine.parse_intent(cmd)
            print(f"'{cmd}': {result['action']} (confidence: {result['confidence']:.2f})")
        
        print("\n=== Test Results ===")
        total_passed = brightness_test['tests_passed'] + volume_test['tests_passed']
        total_failed = brightness_test['tests_failed'] + volume_test['tests_failed']
        print(f"Total tests passed: {total_passed}")
        print(f"Total tests failed: {total_failed}")
        
        if total_failed == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Assistant for Desktop Automation")
    parser.add_argument("--test", action="store_true", help="Run system tests")
    parser.add_argument("--brightness-only", action="store_true", help="Run brightness-only mode")
    parser.add_argument("--volume-only", action="store_true", help="Run volume-only mode")
    
    args = parser.parse_args()
    
    try:
        assistant = VoiceAssistant()
        
        if args.test:
            assistant.run_tests()
        elif args.brightness_only:
            # Legacy brightness-only mode
            from main import VoiceBrightnessAssistant
            brightness_assistant = VoiceBrightnessAssistant()
            brightness_assistant.start()
        elif args.volume_only:
            # Volume-only mode (placeholder for future implementation)
            print("Volume-only mode not yet implemented")
        else:
            # Full voice assistant mode
            assistant.start()
    
    except KeyboardInterrupt:
        print("\nVoice assistant stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
