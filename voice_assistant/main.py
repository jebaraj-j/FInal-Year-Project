"""
Main execution loop for voice-controlled brightness automation.
Coordinates voice listener, intent engine, and brightness controller.
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
from utils.logger import get_logger


class VoiceBrightnessAssistant:
    """
    Main voice assistant class for brightness control.
    Manages the complete workflow from wake word detection to brightness adjustment.
    """
    
    def __init__(self):
        """Initialize voice brightness assistant."""
        # Load configuration
        self.config = self._load_config()
        
        # Initialize logger
        log_level = self.config["logging"]["level"]
        log_dir = Path(__file__).parent / "logs"
        self.logger = get_logger(str(log_dir), log_level)
        
        # Initialize components
        self.voice_listener = VoiceListener(self.config)
        self.intent_engine = BrightnessIntentEngine(
            self._load_commands_config(),
            self.config["noise_words"]
        )
        self.brightness_controller = BrightnessController()
        
        # Runtime state
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.log_system_start()
        self.logger.info("VoiceBrightnessAssistant initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load voice settings configuration.
        
        Returns:
            Configuration dictionary
        """
        config_path = Path(__file__).parent / "config" / "voice_settings.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def _load_commands_config(self) -> Dict[str, Any]:
        """
        Load commands configuration.
        
        Returns:
            Commands configuration dictionary
        """
        commands_path = Path(__file__).parent / "config" / "commands.json"
        
        try:
            with open(commands_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading commands configuration: {e}")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def start(self) -> None:
        """Start the voice assistant."""
        if self.is_running:
            self.logger.warning("Voice assistant is already running")
            return
        
        self.logger.info("Starting voice assistant...")
        
        # Test brightness controller
        brightness_info = self.brightness_controller.get_brightness_info()
        if not brightness_info.get("supported", False):
            self.logger.error("Brightness control is not supported on this system")
            self.logger.error("Please ensure you have a compatible display and drivers")
            return
        
        # Start voice listener
        if not self.voice_listener.start_listening():
            self.logger.error("Failed to start voice listener")
            return
        
        self.is_running = True
        self.logger.info("Voice assistant started successfully")
        self.logger.info("Listening for wake words: 'hey assistant', 'ok assistant', 'hello system'")
        
        # Main execution loop
        self._main_loop()
    
    def _main_loop(self) -> None:
        """Main execution loop."""
        while self.is_running:
            try:
                # Wait for voice command
                result = self.voice_listener.listen(timeout=10.0)
                
                if result["status"] == "success":
                    self._process_command(result["text"])
                elif result["status"] == "timeout":
                    # Normal timeout, continue listening
                    continue
                elif result["status"] == "error":
                    self.logger.log_error("VoiceError", "Voice recognition error")
                    time.sleep(1.0)  # Brief pause before retry
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.log_error("MainLoopError", str(e))
                time.sleep(2.0)  # Pause before retry
        
        self.shutdown()
    
    def _process_command(self, command_text: str) -> None:
        """
        Process recognized voice command.
        
        Args:
            command_text: Recognized command text
        """
        try:
            # Parse intent
            intent_result = self.intent_engine.parse_intent(command_text)
            
            if intent_result["confidence"] < 0.6:
                self.logger.log_audio_event("Low confidence command", f"Confidence: {intent_result['confidence']:.2f}")
                return
            
            if not intent_result["action"]:
                self.logger.log_audio_event("No action detected", f"Command: {command_text}")
                return
            
            # Execute brightness action
            success = self.brightness_controller.execute_action(
                intent_result["action"],
                intent_result["value"]
            )
            
            if success:
                self.logger.info(f"Command executed successfully: {intent_result['action']}")
            else:
                self.logger.log_error("CommandExecutionError", f"Failed to execute: {intent_result['action']}")
                
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e), f"Command: {command_text}")
    
    def shutdown(self) -> None:
        """Shutdown the voice assistant gracefully."""
        if not self.is_running:
            return
        
        self.logger.info("Shutting down voice assistant...")
        self.is_running = False
        
        # Stop voice listener
        if self.voice_listener:
            self.voice_listener.stop_listening()
        
        self.logger.log_system_shutdown()
    
    def run_test_mode(self) -> None:
        """Run in test mode to verify components."""
        self.logger.info("Running in test mode...")
        
        # Test brightness controller
        print("\n=== Brightness Controller Test ===")
        brightness_test = self.brightness_controller.test_brightness_control()
        
        for detail in brightness_test["details"]:
            print(f"  {detail}")
        
        print(f"\nTests passed: {brightness_test['tests_passed']}")
        print(f"Tests failed: {brightness_test['tests_failed']}")
        
        # Test intent engine
        print("\n=== Intent Engine Test ===")
        test_commands = [
            "increase brightness",
            "brightness up",
            "decrease brightness", 
            "brightness down",
            "set brightness 75",
            "brightness 50"
        ]
        
        for command in test_commands:
            result = self.intent_engine.test_intent_parsing(command)
            print(f"  Command: '{command}'")
            print(f"    Action: {result['action']}")
            print(f"    Value: {result['value']}")
            print(f"    Confidence: {result['confidence']:.2f}")
            print()
        
        # Test wake word detector
        print("=== Wake Word Detector Test ===")
        from speech.wake_word_detector import WakeWordDetector
        
        wake_detector = WakeWordDetector(
            self.config["wake_words"],
            self.config["recognition"]["wake_word_threshold"]
        )
        
        test_wake_phrases = [
            "hey assistant",
            "ok assistant",
            "hello system",
            "hey computer",
            "hello there"
        ]
        
        for phrase in test_wake_phrases:
            detected, wake_word, confidence = wake_detector.detect_wake_word(phrase)
            status = "✓" if detected else "✗"
            print(f"  {status} '{phrase}' -> {wake_word} ({confidence:.2f})")
        
        print("\nTest mode completed.")


def main():
    """Main entry point."""
    assistant = VoiceBrightnessAssistant()
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        assistant.run_test_mode()
        return
    
    try:
        assistant.start()
    except Exception as e:
        assistant.logger.log_error("SystemError", str(e))
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
