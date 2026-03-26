"""
Full integrated voice assistant with brightness, volume, and app launcher support.
Production-ready system with comprehensive module integration.
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
from volume_control.volume_intent_engine import VolumeIntentEngine
from volume_control.volume_controller import VolumeController
from app_control.app_intent_engine import AppIntentEngine
from app_control.app_launcher import ApplicationLauncher
from system_control.system_intent_engine import SystemIntentEngine
from system_control.system_controller import SystemController
from utils.logger import get_logger


class FullVoiceAssistant:
    """
    Full-featured voice assistant for desktop automation.
    Supports brightness, volume, application launching, and system control.
    """
    
    def __init__(self):
        """Initialize full voice assistant."""
        # Load configuration
        self.config = self._load_config()
        
        # Initialize logger
        log_level = self.config["logging"]["level"]
        log_dir = Path(__file__).parent / "logs"
        self.logger = get_logger(str(log_dir), log_level)
        
        # Initialize voice listener
        self.voice_listener = VoiceListener(self.config)
        
        # Initialize controllers
        self.brightness_controller = BrightnessController()
        self.volume_controller = None  # Lazy initialization
        self.app_launcher = ApplicationLauncher()
        self.system_controller = SystemController()
        
        # Initialize intent engines
        commands_config = self._load_commands_config()
        self.brightness_intent_engine = BrightnessIntentEngine(
            commands_config,
            self.config["noise_words"]
        )
        self.volume_intent_engine = None  # Lazy initialization
        self.app_intent_engine = AppIntentEngine(
            commands_config,
            self.config["noise_words"],
            self.app_launcher.get_available_apps()
        )
        self.system_intent_engine = SystemIntentEngine(
            commands_config,
            self.config["noise_words"]
        )
        
        # Runtime state
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("FullVoiceAssistant initialized")
        self.logger.info("Supported modules: brightness, volume, app_launcher, system_control")
    
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
            Intent type: "brightness", "volume", "app_launch", "system_control", or None
        """
        text_lower = text.lower()
        
        # Check for app launcher keywords first (most specific)
        app_config = self.config.get("commands", {}).get("app_launcher", {})
        app_keywords = app_config.get("keywords", ["open", "start", "launch"])
        
        for keyword in app_keywords:
            if keyword in text_lower:
                return "app_launch"
        
        # Check for system control keywords (highest priority for safety)
        system_config = self.config.get("commands", {}).get("system_control", {})
        system_keywords = system_config.get("keywords", ["system", "computer", "pc"])
        
        for keyword in system_keywords:
            if keyword in text_lower:
                return "system_control"
        
        # Check for brightness keywords
        brightness_config = self.config.get("commands", {}).get("brightness", {})
        brightness_keywords = brightness_config.get("keywords", ["brightness", "bright"])
        
        for keyword in brightness_keywords:
            if keyword in text_lower:
                return "brightness"
        
        # Check for volume keywords
        volume_config = self.config.get("commands", {}).get("volume", {})
        volume_keywords = volume_config.get("keywords", ["volume", "sound"])
        
        for keyword in volume_keywords:
            if keyword in text_lower:
                return "volume"
        
        # If no keywords found, try all intent engines
        brightness_intent = self.brightness_intent_engine.parse_intent(text)
        app_intent = self.app_intent_engine.parse_intent(text)
        system_intent = self.system_intent_engine.parse_intent(text)
        
        # Use the one with highest confidence
        intents = [
            ("system_control", system_intent["confidence"]),
            ("brightness", brightness_intent["confidence"]),
            ("app_launch", app_intent["confidence"])
        ]
        
        # Add volume if available
        if self.volume_intent_engine:
            volume_intent = self.volume_intent_engine.parse_intent(text)
            intents.append(("volume", volume_intent["confidence"]))
        
        best_intent = max(intents, key=lambda x: x[1])
        
        if best_intent[1] > 0.6:  # Confidence threshold
            return best_intent[0]
        
        return None
    
    def _initialize_volume_controller(self) -> bool:
        """
        Initialize volume controller with fallback support.
        
        Returns:
            True if successful, False otherwise
        """
        if self.volume_controller is not None:
            return True
        
        try:
            # Try to import and initialize pycaw controller
            from volume_control.volume_controller import VolumeController
            self.volume_controller = VolumeController()
            
            if self.volume_controller.is_supported:
                self.logger.info("Volume controller initialized with pycaw")
                return True
            else:
                self.logger.warning("pycaw volume controller not supported, using fallback")
                
        except Exception as e:
            self.logger.log_error("VolumeControllerInitError", str(e))
            self.logger.warning("pycaw volume controller failed, using fallback")
        
        # Initialize fallback volume controller
        from integrated_voice_assistant import FallbackVolumeController
        self.volume_controller = FallbackVolumeController()
        
        # Initialize volume intent engine
        commands_config = self._load_commands_config()
        self.volume_intent_engine = VolumeIntentEngine(
            commands_config,
            self.config["noise_words"]
        )
        
        return True
    
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
            
            # Route to appropriate intent engine and controller
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
                # Initialize volume controller if needed
                if not self._initialize_volume_controller():
                    self.logger.error("Failed to initialize volume controller")
                    return False
                
                intent = self.volume_intent_engine.parse_intent(text)
                if intent["action"]:
                    return self.volume_controller.execute_action(
                        intent["action"], 
                        intent["value"]
                    )
                else:
                    self.logger.warning(f"No volume action detected for: '{text}'")
                    return False
            
            elif intent_type == "system_control":
                intent = self.system_intent_engine.parse_intent(text)
                if intent["action"]:
                    # Check if action requires confirmation
                    requires_confirmation = self.system_intent_engine.requires_confirmation(intent["action"])
                    
                    if requires_confirmation:
                        # Start confirmation workflow
                        confirmation_message = self.system_controller._get_confirmation_message(intent["action"])
                        print(f"\n🚨 {confirmation_message}")
                        print("⏰ Say 'yes' or 'no' within 5 seconds...")
                        
                        # Listen for confirmation response
                        def confirmation_callback(result):
                            if result == "confirmed":
                                success = self.system_controller.execute_confirmed_action(intent["action"])
                                if success:
                                    self.logger.info("System action executed successfully")
                                    print("✅ System action executed successfully")
                                else:
                                    self.logger.warning("System action execution failed")
                                    print("❌ System action execution failed")
                            else:
                                self.logger.info("System action cancelled")
                                print("❌ System action cancelled")
                        
                        # Start confirmation workflow and listen for response
                        self.system_controller.start_confirmation_workflow(intent["action"], confirmation_callback)
                        
                        # Listen for confirmation response
                        confirmation_result = self.voice_listener.listen(timeout=5.0)
                        
                        if confirmation_result["status"] == "success":
                            response_text = confirmation_result.get("text", "").strip().lower()
                            self.system_controller.process_confirmation_response(response_text)
                        else:
                            # Timeout or error - cancel
                            self.system_controller.cancel_confirmation()
                        
                        return True  # Confirmation workflow handled
                    else:
                        # Execute directly (safe actions like lock)
                        success = self.system_controller.execute_action(intent["action"], require_confirmation=False)
                        if success:
                            self.logger.info("System action executed successfully")
                            print("✅ System action executed successfully")
                        else:
                            self.logger.warning("System action execution failed")
                            print("❌ System action execution failed")
                        return success
                else:
                    self.logger.warning(f"No system action detected for: '{text}'")
                    return False
            
            elif intent_type == "app_launch":
                intent = self.app_intent_engine.parse_intent(text)
                if intent["app"]:
                    return self.app_launcher.execute_action(intent["app"])
                else:
                    self.logger.warning(f"No app detected for: '{text}'")
                    return False
            
            else:
                self.logger.warning(f"Unknown intent type: {intent_type}")
                return False
                
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e), f"Text: {text}")
            return False
    
    def _get_grammar(self) -> list:
        """
        Collect all valid phrases for VOSK grammar.
        'Super Overfitting' - Forces exact phrase matching from command list.
        Generates all numeric variations for value-based commands.
        """
        grammar = set()
        
        # 1. Add wake words
        for ww in self.config.get("wake_words", []):
            grammar.add(ww.lower())
        
        # 2. Add app launch phrases
        apps = self.app_launcher.get_available_apps()
        for app in apps.keys():
            grammar.add(f"open {app.lower()}")
            grammar.add(f"start {app.lower()}")
            grammar.add(f"launch {app.lower()}")
        
        # 3. Add command phrases from commands.json
        from utils.num_converter import number_to_words
        
        commands_config = self._load_commands_config()
        for module in commands_config.values():
            if not isinstance(module, dict):
                continue
                
            actions = module.get("actions", {})
            if actions:
                # Nested actions (brightness, volume)
                for action in actions.values():
                    for pattern in action.get("patterns", []):
                        if "{value}" in pattern:
                            # Generate both numeric and word-based variations for overfitting
                            for i in range(101):
                                # Digit variation (unreliable in some VOSK models)
                                grammar.add(pattern.replace("{value}", str(i)).lower())
                                # Word variation (preferred by VOSK)
                                grammar.add(pattern.replace("{value}", number_to_words(i)).lower())
                        else:
                            grammar.add(pattern.lower())
            else:
                # Direct lists (system_control)
                for key, val in module.items():
                    if key != "keywords" and isinstance(val, list):
                        for cmd in val:
                            grammar.add(cmd.lower())
        
        # 4. Add confirmation words (exact words)
        grammar.update(["yes", "no", "yeah", "yep", "sure", "ok", "okay", "nope", "cancel", "stop"])
        
        # 5. Add filler words
        for nw in self.config.get("noise_words", []):
            grammar.add(nw.lower())
        
        # Add numbers as individual words (both digits and words)
        for i in range(101):
            grammar.add(str(i))
            grammar.add(number_to_words(i))
            
        return sorted(list(grammar))

    def start(self):
        """Start the full voice assistant."""
        self.logger.info("Starting full voice assistant...")
        
        # Collect grammar and start voice listener
        grammar = self._get_grammar()
        if not self.voice_listener.start_listening(grammar):
            self.logger.error("Failed to start voice listener!")
            return
        
        self.is_running = True
        self.logger.info("Full voice assistant started successfully")
        self.logger.info(f"Listening for wake words: {', '.join(self.config['wake_words'])}")
        
        # Display available commands
        print("🎤 Full Voice Assistant Started — Direct Command Mode")
        print("=" * 50)
        print("📱 Supported Commands:")
        print("  • Brightness: 'increase brightness', 'brightness up', 'set brightness 70'")
        print("  • Volume: 'increase volume', 'volume up', 'set volume 50'")
        print("  • Apps: 'open chrome', 'open code', 'open notepad', 'open settings'")
        print("  • System: 'shutdown system', 'restart system', 'sleep system', 'lock system'")
        print("=" * 50)
        print("🎯 Just speak a command directly — no wake word needed!")
        print("⚠️  System commands require confirmation for safety!")
        
        try:
            while self.is_running:
                # Listen for voice command
                result = self.voice_listener.listen(timeout=10.0)
                
                if result["status"] == "success":
                    command_text = result.get("text", "").strip()
                    if command_text:
                        self.logger.info(f"Command received: '{command_text}'")
                        print(f"📝 Command: {command_text}")
                        
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
                        print("❓ No command detected")
                
                elif result["status"] == "timeout":
                    # Normal timeout, continue listening
                    continue
                
                elif result["status"] == "error":
                    error = result.get("text", "Unknown error")
                    self.logger.log_error("CommandError", error)
                    print(f"🔴 Error: {error}")
                
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
        self.logger.info("Shutting down full voice assistant...")
        
        # Stop voice listener
        self.voice_listener.stop_listening()
        
        # Cleanup controllers
        if hasattr(self.brightness_controller, 'cleanup'):
            self.brightness_controller.cleanup()
        
        if self.volume_controller and hasattr(self.volume_controller, 'cleanup'):
            self.volume_controller.cleanup()
        
        if hasattr(self.app_launcher, 'cleanup'):
            self.app_launcher.cleanup()
        
        if hasattr(self.system_controller, 'cleanup'):
            self.system_controller.cleanup()
        
        self.logger.info("Full voice assistant shutdown complete")
    
    def run_tests(self):
        """Run system tests for all modules."""
        print("=== Full Voice Assistant System Tests ===")
        
        # Test brightness controller
        print("\n--- Brightness Controller Test ---")
        brightness_test = self.brightness_controller.test_brightness_control()
        print(f"Tests passed: {brightness_test['tests_passed']}")
        print(f"Tests failed: {brightness_test['tests_failed']}")
        for detail in brightness_test['details']:
            print(f"  {detail}")
        
        # Test volume controller
        print("\n--- Volume Controller Test ---")
        if self._initialize_volume_controller():
            volume_test = self.volume_controller.test_volume_control()
            print(f"Tests passed: {volume_test['tests_passed']}")
            print(f"Tests failed: {volume_test['tests_failed']}")
            for detail in volume_test['details']:
                print(f"  {detail}")
        else:
            print("❌ Volume controller initialization failed")
        
        # Test app launcher
        print("\n--- App Launcher Test ---")
        app_test = self.app_launcher.test_app_launcher()
        print(f"Tests passed: {app_test['tests_passed']}")
        print(f"Tests failed: {app_test['tests_failed']}")
        for detail in app_test['details']:
            print(f"  {detail}")
        
        # Test intent engines
        print("\n--- Intent Engine Tests ---")
        
        # Brightness commands
        brightness_commands = [
            "increase brightness",
            "brightness up",
            "decrease brightness",
            "brightness down",
            "set brightness 75"
        ]
        
        print("Brightness intent engine:")
        for cmd in brightness_commands:
            result = self.brightness_intent_engine.parse_intent(cmd)
            print(f"  '{cmd}': {result['action']} (confidence: {result['confidence']:.2f})")
        
        # Volume commands
        if self.volume_intent_engine:
            volume_commands = [
                "increase volume",
                "volume up",
                "decrease volume",
                "volume down",
                "set volume 50"
            ]
            
            print("Volume intent engine:")
            for cmd in volume_commands:
                result = self.volume_intent_engine.parse_intent(cmd)
                print(f"  '{cmd}': {result['action']} (confidence: {result['confidence']:.2f})")
        
        # App commands
        app_commands = [
            "open chrome",
            "open code",
            "open notepad",
            "open settings",
            "open explorer"
        ]
        
        print("App intent engine:")
        for cmd in app_commands:
            result = self.app_intent_engine.parse_intent(cmd)
            app = result.get('app', 'None')
            print(f"  '{cmd}': {app} (confidence: {result['confidence']:.2f})")
        
        # System commands
        system_commands = [
            "shutdown system",
            "restart system",
            "sleep system",
            "lock system"
        ]
        
        print("System intent engine:")
        for cmd in system_commands:
            result = self.system_intent_engine.parse_intent(cmd)
            action = result.get('action', 'None')
            requires_conf = self.system_intent_engine.requires_confirmation(action) if action else False
            conf_mark = "🔒" if requires_conf else "🔓"
            print(f"  '{cmd}': {action} (confidence: {result['confidence']:.2f}) {conf_mark}")
        
        print("\n=== Test Results ===")
        total_passed = brightness_test['tests_passed']
        total_failed = brightness_test['tests_failed']
        
        if self.volume_controller:
            total_passed += volume_test['tests_passed']
            total_failed += volume_test['tests_failed']
        
        total_passed += app_test['tests_passed']
        total_failed += app_test['tests_failed']
        
        # Add system controller tests
        system_test = self.system_controller.test_system_controller()
        print(f"\n--- System Controller Test ---")
        print(f"Tests passed: {system_test['tests_passed']}")
        print(f"Tests failed: {system_test['tests_failed']}")
        for detail in system_test['details']:
            print(f"  {detail}")
        
        total_passed += system_test['tests_passed']
        total_failed += system_test['tests_failed']
        
        print(f"Total tests passed: {total_passed}")
        print(f"Total tests failed: {total_failed}")
        
        if total_failed == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Full Voice Assistant for Desktop Automation")
    parser.add_argument("--test", action="store_true", help="Run system tests")
    parser.add_argument("--brightness-only", action="store_true", help="Run brightness-only mode")
    parser.add_argument("--volume-only", action="store_true", help="Run volume-only mode")
    parser.add_argument("--apps-only", action="store_true", help="Run app launcher-only mode")
    
    args = parser.parse_args()
    
    try:
        assistant = FullVoiceAssistant()
        
        if args.test:
            assistant.run_tests()
        elif args.brightness_only:
            # Legacy brightness-only mode
            from main import VoiceBrightnessAssistant
            brightness_assistant = VoiceBrightnessAssistant()
            brightness_assistant.start()
        elif args.volume_only:
            # Volume-only mode
            from integrated_voice_assistant import IntegratedVoiceAssistant
            volume_assistant = IntegratedVoiceAssistant()
            volume_assistant.start()
        elif args.apps_only:
            # App launcher-only mode (placeholder for future implementation)
            print("Apps-only mode not yet implemented")
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
