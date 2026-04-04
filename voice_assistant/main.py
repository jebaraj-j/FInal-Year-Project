"""
Main execution loop for voice-controlled automation.
Coordinates voice listener, unified intent engine, and all controllers.
"""

import json
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from speech.voice_listener import VoiceListener
from nlp.unified_intent_engine import UnifiedIntentEngine
from brightness_control.brightness_controller import BrightnessController
from volume_control.volume_controller import VolumeController
from app_control.app_launcher import ApplicationLauncher
from system_control.system_controller import SystemController
from utils.logger import get_logger

try:
    from extensions.voice_shortcut_commands import check_and_execute as shortcut_check
    from extensions.voice_shortcut_commands import ADDITIONAL_PHRASES as SHORTCUT_PHRASES
except Exception:
    shortcut_check = None
    SHORTCUT_PHRASES = []


class VoiceAssistant:
    """
    Main voice assistant class for all control types.
    Manages the complete workflow from wake word detection to command execution.
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
        self.intent_engine = UnifiedIntentEngine(
            self._load_commands_config(),
            self.config["noise_words"]
        )
        self.command_confidence_threshold = self.config["recognition"].get("command_confidence_threshold", 0.7)
        
        # Initialize all controllers
        self.brightness_controller = BrightnessController()
        self.volume_controller = VolumeController()
        self.app_controller = ApplicationLauncher()
        self.system_controller = SystemController()
        
        # Map categories to controllers
        self.controllers = {
            "brightness": self.brightness_controller,
            "volume": self.volume_controller,
            "app_launcher": self.app_controller,
            "system_control": self.system_controller
        }
        
        # Runtime state
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.log_system_start()
        self.logger.info("VoiceAssistant initialized")
    
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
            
    def _get_compiled_grammar(self) -> list:
        """
        Extract all possible phrases from commands and settings for VOSK grammar.
        Forces the speech engine to 'overfit' to these specific commands.
        """
        grammar = set()
        
        # 1. Add all wake words
        for ww in self.config.get("wake_words", []):
            grammar.add(ww.lower())
            
        # 2. Add all command patterns from commands.json
        cmd_config = self._load_commands_config()
        for category in cmd_config.values():
            actions = category.get("actions", {})
            for action in actions.values():
                patterns = action.get("patterns", [])
                for pattern in patterns:
                    # Clean up pattern (handle placeholders)
                    clean_pattern = pattern.lower().replace("{value}", "").strip()
                    if clean_pattern:
                        grammar.add(clean_pattern)
                    
                    # Split patterns into individual words to allow more flexibility
                    # e.g., 'set', 'brightness'
                    for word in clean_pattern.split():
                        grammar.add(word)
        
        # 3. Add numbers (supports {value} patterns)
        numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                   "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", 
                   "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", 
                   "eighty", "ninety", "hundred"]
        for num in numbers:
            grammar.add(num)
        # NOTE: We skip str(i) digits as the small Vosk model only supports spelled-out words
            
        # 4. Add the specific switch command and its variations
        grammar.add("switch to gesture")
        grammar.add("switch gesture")
        grammar.add("switch mode")

        # 4.5 Add additional shortcut phrases (modular extension layer)
        for phrase in SHORTCUT_PHRASES:
            p = phrase.lower().strip()
            if p:
                grammar.add(p)
                for word in p.split():
                    grammar.add(word)
        
        # 5. Add common noise/pre-filler words
        for noise in self.config.get("noise_words", []):
            grammar.add(noise.lower())
            
        # 6. Add [unk] for noise rejection if supported
        grammar_list = sorted(list(grammar))
        # Filtering: remove any entries that look like symbols or digits to avoid Vosk initialization errors
        grammar_list = [g for g in grammar_list if any(c.isalpha() for c in g)]
        
        return grammar_list
    
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
        
        # Test all controllers
        self._test_all_controllers()
        
        # Start voice listener with compiled grammar (The 'Overfit')
        grammar = self._get_compiled_grammar()
        if not self.voice_listener.start_listening(grammar=grammar):
            self.logger.error("Failed to start voice listener with grammar")
            return
        
        self.is_running = True
        self.logger.info("Voice assistant started successfully")
        self.logger.info("Listening for wake words: 'hey assistant', 'ok assistant', 'hello system'")
        
        # Main execution loop
        self._main_loop()
    
    def _test_all_controllers(self) -> None:
        """Test all controllers and report their status."""
        results = {}
        
        # Test brightness controller
        brightness_info = self.brightness_controller.get_brightness_info()
        results["brightness"] = brightness_info.get("supported", False)
        
        # Test volume controller
        try:
            volume_info = self.volume_controller.get_volume_info()
            results["volume"] = volume_info.get("supported", False)
        except:
            results["volume"] = False
        
        # App controller and system controller should always work
        results["app_launcher"] = True
        results["system_control"] = True
        
        # Report results
        for controller, supported in results.items():
            if supported:
                self.logger.info(f"{controller} controller: ✅ Supported")
            else:
                self.logger.warning(f"{controller} controller: ❌ Not supported")
    
    def _main_loop(self) -> None:
        """Main execution loop."""
        while self.is_running:
            try:
                # Wait for voice command
                result = self.voice_listener.listen(timeout=8.0)
                
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
        """Process recognized voice command."""
        text = command_text.lower()
        
        # Detect mode switch with more flexibility
        if ("switch" in text and "gesture" in text) or ("switch" in text and "mode" in text):
            # Show visual confirmation in terminal
            print("\n🔄 [MODE SWITCH] Detected: 'switch to gesture'")
            print("[SYSTEM_SIGNAL]:SWITCH_TO_GESTURE", flush=True)
            time.sleep(0.1) # Tiny pause to ensure the pipe is drained by the launcher
            self.shutdown()
            sys.exit(0)
            
        # Detect help command with high priority
        if any(h in text for h in ["help", "show commands", "what can i say", "how to use"]):
            self._display_voice_help()
            return

        # Additional shortcut command layer (kept modular and non-invasive)
        if shortcut_check:
            handled, msg = shortcut_check(text)
            if handled:
                self.logger.info(f"Shortcut command executed: {msg}")
                return

        try:
            # For debugging, log what we heard even if no intent is found later
            # This helps the user see that the microphone IS working
            self.logger.info(f"Processing command: '{command_text}'")

            # Parse intent
            intent_result = self.intent_engine.parse_intent(command_text)
            
            if intent_result["confidence"] < self.command_confidence_threshold:
                self.logger.log_audio_event("Low confidence command", f"Confidence: {intent_result['confidence']:.2f}")
                return
            
            category = intent_result["category"]
            action = intent_result["action"]
            
            if not category or not action:
                self.logger.log_audio_event("No action detected", f"Command: {command_text}")
                return
            
            if category == "help":
                self._display_voice_help()
                return

            # Get appropriate controller
            controller = self.controllers.get(category)
            if not controller:
                self.logger.log_error("ControllerError", f"No controller found for category: {category}")
                return
            
            # Execute action
            success = controller.execute_action(action, intent_result["value"])
            
            if success:
                self.logger.info(f"Command executed successfully: {category}.{action}")
            else:
                self.logger.log_error("CommandExecutionError", f"Failed to execute: {category}.{action}")
                
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e), f"Command: {command_text}")
    
    def _display_voice_help(self) -> None:
        """Print a formatted list of all available voice commands to the terminal."""
        print("\n" + "="*50)
        print("🎙️  VOICE COMMANDS HELP MENU")
        print("="*50)
        
        commands = self._load_commands_config()
        for category, info in commands.items():
            if category == "help": continue
            
            print(f"\n🔹 {category.upper()}:")
            actions = info.get("actions", {})
            for action_name, action_info in actions.items():
                desc = action_info.get("description", "No description")
                # Show first pattern as example
                example = action_info.get("patterns", [""])[0]
                print(f"  - {desc.ljust(35)} | e.g., \"{example}\"")
        
        print("\n🔄 MODE SWITCHING:")
        print(f"  - {'Switch back to Gesture Mode'.ljust(35)} | Say \"Switch to gesture\"")
        print("="*50 + "\n")
        self.logger.info("Help information displayed to user")

    def shutdown(self) -> None:
        """Shutdown the voice assistant gracefully."""
        if not self.is_running:
            return
        
        self.logger.info("Shutting down voice assistant...")
        self.is_running = False
        
        # Stop voice listener
        if self.voice_listener:
            self.voice_listener.stop_listening()
        
        # Cleanup controllers
        for controller in self.controllers.values():
            if hasattr(controller, 'cleanup'):
                controller.cleanup()
        
        self.logger.log_system_shutdown()
    
    def run_test_mode(self) -> None:
        """Run in test mode to verify components."""
        self.logger.info("Running in test mode...")
        
        # Test all controllers
        print("\n=== Controller Status Test ===")
        self._test_all_controllers()
        
        # Test intent engine
        print("\n=== Intent Engine Test ===")
        test_commands = [
            # Brightness commands
            "brightness up",
            "brightness down",
            "set brightness 75",
            # Volume commands
            "volume up",
            "volume down", 
            "set volume 50",
            # App commands
            "open chrome",
            "open code",
            "open notepad",
            # System commands
            "shutdown system now",
            "restart system now",
            "sleep system now"
        ]
        
        for command in test_commands:
            result = self.intent_engine.test_intent_parsing(command)
            print(f"  Command: '{command}'")
            print(f"    Category: {result['category']}")
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
            status = "PASS" if detected else "FAIL"
            print(f"  {status} '{phrase}' -> {wake_word} ({confidence:.2f})")
        
        print("\nTest mode completed.")


def main():
    """Main entry point."""
    assistant = VoiceAssistant()
    
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
