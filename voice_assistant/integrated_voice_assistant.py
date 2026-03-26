"""
Integrated voice assistant with both brightness and volume control.
Production-ready version with fallback volume control.
"""

import json
import signal
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from speech.voice_listener import VoiceListener
from brightness_control.brightness_intent_engine import BrightnessIntentEngine
from brightness_control.brightness_controller import BrightnessController
from volume_control.volume_intent_engine import VolumeIntentEngine
from volume_control.volume_controller import VolumeController
from utils.logger import get_logger


class IntegratedVoiceAssistant:
    """
    Integrated voice assistant for desktop automation.
    Supports both brightness and volume control with fallback mechanisms.
    """
    
    def __init__(self):
        """Initialize integrated voice assistant."""
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
        self.volume_controller = None  # Will be initialized on demand
        
        # Runtime state
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("IntegratedVoiceAssistant initialized")
        self.logger.info("Supported modules: brightness, volume (with fallback)")
    
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
    
    def _initialize_volume_controller(self) -> bool:
        """
        Initialize volume controller with fallback support.
        
        Returns:
            True if successful (either pycaw or fallback), False otherwise
        """
        if self.volume_controller is not None:
            return True
        
        try:
            # Try to import and initialize pycaw controller
            from controllers.volume_controller import VolumeController
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
        self.volume_controller = FallbackVolumeController()
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
            
            else:
                self.logger.warning(f"Unknown intent type: {intent_type}")
                return False
                
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e), f"Text: {text}")
            return False
    
    def start(self):
        """Start the integrated voice assistant."""
        self.logger.info("Starting integrated voice assistant...")
        
        # Start voice listener
        if not self.voice_listener.start_listening():
            self.logger.error("Failed to start voice listener!")
            return
        
        self.is_running = True
        self.logger.info("Integrated voice assistant started successfully")
        self.logger.info(f"Listening for wake words: {', '.join(self.config['wake_words'])}")
        print("🎤 Integrated Voice Assistant Started")
        print("Supported: Brightness + Volume Control")
        print(f"Wake words: {', '.join(self.config['wake_words'])}")
        print("Say 'hey assistant' followed by a command...")
        
        try:
            while self.is_running:
                # Listen for wake word
                result = self.voice_listener.listen_for_wake_word()
                
                if result["status"] == "wake_word_detected":
                    wake_word = result.get("wake_word", "unknown")
                    confidence = result.get("confidence", 0.0)
                    
                    self.logger.info(f"Wake word detected: '{wake_word}' (confidence: {confidence:.2f})")
                    print(f"🎯 Wake word: {wake_word}")
                    
                    # Enter active listening mode for command
                    command_result = self.voice_listener.listen_for_command(
                        timeout=self.config["recognition"]["active_listening_timeout"]
                    )
                    
                    if command_result["status"] == "success":
                        command_text = command_result.get("text", "").strip()
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
                    
                    elif command_result["status"] == "timeout":
                        self.logger.info("Active listening timeout")
                        print("⏰ Timeout: No command received")
                    
                    elif command_result["status"] == "error":
                        error = command_result.get("text", "Unknown error")
                        self.logger.log_error("CommandError", error)
                        print(f"🔴 Error: {error}")
                
                elif result["status"] == "error":
                    error = result.get("text", "Unknown error")
                    self.logger.log_error("WakeWordError", error)
                    print(f"🔴 Wake word error: {error}")
                
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
        self.logger.info("Shutting down integrated voice assistant...")
        
        # Stop voice listener
        self.voice_listener.stop_listening()
        
        # Cleanup controllers
        if hasattr(self.brightness_controller, 'cleanup'):
            self.brightness_controller.cleanup()
        
        if self.volume_controller and hasattr(self.volume_controller, 'cleanup'):
            self.volume_controller.cleanup()
        
        self.logger.info("Integrated voice assistant shutdown complete")


class FallbackVolumeController:
    """
    Fallback volume controller using Windows PowerShell.
    Used when pycaw is not available.
    """
    
    def __init__(self):
        """Initialize fallback volume controller."""
        from utils.logger import get_logger
        self.logger = get_logger()
        self.min_volume = 0
        self.max_volume = 100
        self.is_supported = True
        
        self.logger.info("FallbackVolumeController initialized (PowerShell)")
    
    def get_current(self) -> int:
        """Get current volume using PowerShell."""
        try:
            result = subprocess.run([
                'powershell', '-Command',
                '(Get-AudioDevice -PlaybackDevice).Volume'
            ], capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                volume_str = result.stdout.strip()
                if volume_str:
                    return int(float(volume_str) * 100)
            return 50  # Default fallback
        except Exception as e:
            self.logger.log_error("VolumeGetError", str(e))
            return 50
    
    def set(self, value: int) -> bool:
        """Set volume using PowerShell."""
        try:
            # Clamp value
            clamped_value = max(self.min_volume, min(self.max_volume, value))
            
            # Convert to decimal for PowerShell
            volume_decimal = clamped_value / 100.0
            
            result = subprocess.run([
                'powershell', '-Command',
                f'Set-AudioDevice -PlaybackDeviceVolume {volume_decimal}'
            ], capture_output=True, text=True, check=True)
            
            success = result.returncode == 0
            if success:
                self.logger.log_volume_change(self.get_current(), clamped_value, "set")
                print(f"🔊 Volume set to {clamped_value}%")
            
            return success
        except Exception as e:
            self.logger.log_error("VolumeSetError", str(e))
            return False
    
    def increase(self, step: int = 2) -> bool:
        """Increase volume using PowerShell."""
        current = self.get_current()
        return self.set(current + step)
    
    def decrease(self, step: int = 2) -> bool:
        """Decrease volume using PowerShell."""
        current = self.get_current()
        return self.set(current - step)
    
    def execute_action(self, action: str, value: int = None) -> bool:
        """Execute volume action using PowerShell."""
        try:
            if action == "absolute_increase":
                success = self.set(100)
                self.logger.info(f"Executed absolute increase to 100%")
            elif action == "absolute_decrease":
                success = self.set(0)
                self.logger.info(f"Executed absolute decrease to 0%")
            elif action == "relative_increase":
                success = self.increase(2)
                self.logger.info(f"Executed relative increase by 2%")
            elif action == "relative_decrease":
                success = self.decrease(2)
                self.logger.info(f"Executed relative decrease by 2%")
            elif action == "set_value":
                if value is not None:
                    success = self.set(value)
                    self.logger.info(f"Executed set value to {value}%")
                else:
                    self.logger.log_error("VolumeExecuteError", "set_value action requires a value")
                    success = False
            else:
                self.logger.log_error("VolumeExecuteError", f"Unknown action: {action}")
                success = False
            
            return success
        except Exception as e:
            self.logger.log_error("VolumeExecuteError", str(e))
            return False
    
    def test_volume_control(self) -> Dict[str, Any]:
        """Test volume control functionality."""
        test_results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
        
        # Test getting current volume
        try:
            current = self.get_current()
            test_results["details"].append(f"✓ Get current volume: {current}%")
            test_results["tests_passed"] += 1
        except Exception as e:
            test_results["details"].append(f"✗ Get current volume failed: {e}")
            test_results["tests_failed"] += 1
        
        # Test setting volume
        try:
            original = self.get_current()
            
            if original < 100:
                # Test increase
                if self.increase(5):
                    new_volume = self.get_current()
                    test_results["details"].append("✓ Increase volume test passed")
                    test_results["tests_passed"] += 1
                    
                    # Restore original
                    self.set(original)
                else:
                    test_results["details"].append("✗ Increase volume test failed")
                    test_results["tests_failed"] += 1
            else:
                # Test decrease
                if self.decrease(5):
                    new_volume = self.get_current()
                    test_results["details"].append("✓ Decrease volume test passed")
                    test_results["tests_passed"] += 1
                    
                    # Restore original
                    self.set(original)
                else:
                    test_results["details"].append("✗ Decrease volume test failed")
                    test_results["tests_failed"] += 1
                    
        except Exception as e:
            test_results["details"].append(f"✗ Volume change test failed: {e}")
            test_results["tests_failed"] += 1
        
        return test_results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Integrated Voice Assistant for Desktop Automation")
    parser.add_argument("--test", action="store_true", help="Run system tests")
    parser.add_argument("--brightness-only", action="store_true", help="Run brightness-only mode")
    
    args = parser.parse_args()
    
    try:
        assistant = IntegratedVoiceAssistant()
        
        if args.test:
            # Run tests for both modules
            print("=== Integrated System Tests ===")
            
            # Test brightness
            brightness_test = assistant.brightness_controller.test_brightness_control()
            print(f"Brightness tests: {brightness_test['tests_passed']}/{brightness_test['tests_passed'] + brightness_test['tests_failed']}")
            
            # Test volume intent engine
            assistant._initialize_volume_controller()
            volume_commands = [
                "increase volume", "volume up", "set volume 50"
            ]
            print("Volume intent engine tests:")
            for cmd in volume_commands:
                intent = assistant.volume_intent_engine.parse_intent(cmd)
                print(f"  '{cmd}': {intent['action']} (confidence: {intent['confidence']:.2f})")
            
            print("✅ Integrated system tests completed")
            
        elif args.brightness_only:
            # Legacy brightness-only mode
            from main import VoiceBrightnessAssistant
            brightness_assistant = VoiceBrightnessAssistant()
            brightness_assistant.start()
        else:
            # Full integrated voice assistant mode
            assistant.start()
    
    except KeyboardInterrupt:
        print("\nVoice assistant stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
