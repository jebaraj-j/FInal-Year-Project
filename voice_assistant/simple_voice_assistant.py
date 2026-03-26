#!/usr/bin/env python3
"""
Simple voice assistant that works with direct VOSK recognition.
Bypasses the complex voice listener for reliable operation.
"""

import sys
import os
import json
import time
import signal
import numpy as np
import pyaudio
import vosk
from pathlib import Path
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from brightness_control.brightness_controller import BrightnessController
from volume_control.volume_controller import VolumeController
from app_control.app_launcher import ApplicationLauncher
from system_control.system_controller import SystemController
from brightness_control.brightness_intent_engine import BrightnessIntentEngine
from volume_control.volume_intent_engine import VolumeIntentEngine
from app_control.app_intent_engine import AppIntentEngine
from system_control.system_intent_engine import SystemIntentEngine
from utils.logger import get_logger


class SimpleVoiceAssistant:
    """
    Simple voice assistant using direct VOSK recognition.
    More reliable than the complex voice listener.
    """
    
    def __init__(self):
        """Initialize simple voice assistant."""
        # Load configuration
        self.config = self._load_config()
        
        # Initialize logger
        log_level = self.config["logging"]["level"]
        log_dir = Path(__file__).parent / "logs"
        self.logger = get_logger(str(log_dir), log_level)
        
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
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("SimpleVoiceAssistant initialized")
        self.logger.info("Supported modules: brightness, volume, app_launcher, system_control")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load voice settings configuration."""
        try:
            with open('config/voice_settings.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def _load_commands_config(self) -> Dict[str, Any]:
        """Load commands configuration."""
        try:
            with open('config/commands.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading commands configuration: {e}")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def _detect_intent_type(self, text: str) -> str:
        """Detect which intent type the command belongs to."""
        text_lower = text.lower()
        
        # Handle VOSK misinterpretations of "hey assistant"
        if "assistant" in text_lower or "has his assistant" in text_lower or "has his tent" in text_lower:
            # This is likely a wake word variation, treat as general command
            pass
        
        # Check for system control keywords (highest priority for safety)
        system_config = self.config.get("commands", {}).get("system_control", {})
        system_keywords = system_config.get("keywords", ["system", "computer", "pc"])
        
        for keyword in system_keywords:
            if keyword in text_lower:
                return "system_control"
        
        # Check for app launcher keywords
        app_config = self.config.get("commands", {}).get("app_launcher", {})
        app_keywords = app_config.get("keywords", ["open", "start", "launch"])
        
        for keyword in app_keywords:
            if keyword in text_lower:
                return "app_launch"
        
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
        
        # Check for specific command patterns
        if any(word in text_lower for word in ["shutdown", "restart", "sleep", "lock"]):
            return "system_control"
        
        if any(word in text_lower for word in ["chrome", "code", "notepad", "settings", "explorer"]):
            return "app_launch"
        
        if any(word in text_lower for word in ["increase", "decrease", "up", "down"]):
            # Could be brightness or volume, check for context
            if "bright" in text_lower:
                return "brightness"
            elif "volume" in text_lower or "sound" in text_lower:
                return "volume"
        
        return None
    
    def _process_command(self, text: str) -> bool:
        """Process recognized voice command."""
        try:
            # Detect intent type
            intent_type = self._detect_intent_type(text)
            
            if not intent_type:
                self.logger.warning(f"No intent detected for: '{text}'")
                print(f"❓ Unknown command: {text}")
                return False
            
            # Route to appropriate handler
            if intent_type == "brightness":
                intent = self.brightness_intent_engine.parse_intent(text)
                if intent["action"]:
                    return self.brightness_controller.execute_action(
                        intent["action"],
                        intent.get("value")
                    )
                else:
                    self.logger.warning(f"No brightness action detected for: '{text}'")
                    return False
            
            elif intent_type == "volume":
                if not self.volume_controller:
                    from volume_control.volume_controller import VolumeController
                    self.volume_controller = VolumeController()
                
                if not self.volume_intent_engine:
                    self.volume_intent_engine = VolumeIntentEngine(
                        self._load_commands_config(),
                        self.config["noise_words"]
                    )
                
                intent = self.volume_intent_engine.parse_intent(text)
                if intent["action"]:
                    return self.volume_controller.execute_action(
                        intent["action"],
                        intent.get("value")
                    )
                else:
                    self.logger.warning(f"No volume action detected for: '{text}'")
                    return False
            
            elif intent_type == "app_launch":
                intent = self.app_intent_engine.parse_intent(text)
                if intent["app"]:
                    return self.app_launcher.execute_action(intent["app"])
                else:
                    self.logger.warning(f"No app detected for: '{text}'")
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
                        confirmation_result = self._listen_for_response(timeout=5.0)
                        
                        if confirmation_result["status"] == "success":
                            response_text = confirmation_result.get("text", "").strip().lower()
                            if response_text in ["yes", "yeah", "yep", "sure", "ok"]:
                                success = self.system_controller.execute_confirmed_action(intent["action"])
                                if success:
                                    self.logger.info("System action executed successfully")
                                    print("✅ System action executed successfully")
                                else:
                                    self.logger.warning("System action execution failed")
                                    print("❌ System action execution failed")
                                return success
                            else:
                                self.logger.info("System action cancelled")
                                print("❌ System action cancelled")
                                return False
                        else:
                            # Timeout or error - cancel
                            self.system_controller.cancel_confirmation()
                            print("❌ System action cancelled (timeout)")
                            return False
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
            
            else:
                self.logger.warning(f"Unknown intent type: {intent_type}")
                return False
                
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e))
            print(f"❌ Error processing command: {e}")
            return False
    
    def _listen_for_response(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Listen for a simple response (yes/no)."""
        return self._listen_for_speech(timeout)
    
    def _listen_for_speech(self, timeout: float = 10.0) -> Dict[str, Any]:
        """Listen for speech using direct VOSK recognition."""
        try:
            # Initialize VOSK if not already done
            if not hasattr(self, 'model'):
                model_path = self.config["recognition"]["model_path"]
                if not os.path.exists(model_path):
                    return {"status": "error", "text": "VOSK model not found"}
                
                self.model = vosk.Model(model_path)
                self.recognizer = vosk.KaldiRecognizer(self.model, self.config["audio"]["sample_rate"])
                
                # Initialize PyAudio
                self.audio = pyaudio.PyAudio()
            
            # Open audio stream
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.config["audio"]["channels"],
                rate=self.config["audio"]["sample_rate"],
                input=True,
                input_device_index=self.config["audio"]["input_device_index"],
                frames_per_buffer=self.config["audio"]["chunk_size"]
            )
            
            print("🎤 Listening...")
            
            # Record and recognize
            start_time = time.time()
            audio_data = []
            
            while time.time() - start_time < timeout:
                try:
                    data = stream.read(self.config["audio"]["chunk_size"], exception_on_overflow=False)
                    audio_data.append(data)
                    
                    # Try to recognize in real-time
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '')
                        if text:
                            stream.stop_stream()
                            return {"status": "success", "text": text, "confidence": 1.0}
                            
                except Exception as e:
                    self.logger.log_error("AudioReadError", str(e))
                    break
            
            # Process final result
            if audio_data:
                final_result = self.recognizer.FinalResult()
                result = json.loads(final_result)
                text = result.get('text', '')
                
                if text:
                    return {"status": "success", "text": text, "confidence": 1.0}
            
            stream.stop_stream()
            stream.close()
            
            return {"status": "timeout", "text": "", "confidence": 0.0}
            
        except Exception as e:
            self.logger.log_error("SpeechRecognitionError", str(e))
            return {"status": "error", "text": str(e), "confidence": 0.0}
    
    def start(self):
        """Start the voice assistant."""
        if self.is_running:
            self.logger.warning("Voice assistant is already running")
            return
        
        self.logger.info("Starting simple voice assistant...")
        
        # Test brightness controller
        brightness_info = self.brightness_controller.get_brightness_info()
        if not brightness_info.get("supported", False):
            self.logger.error("Brightness control is not supported on this system")
            print("❌ Brightness control is not supported on this system")
        
        self.is_running = True
        self.logger.info("Simple voice assistant started successfully")
        
        # Display available commands
        print("🎤 Simple Voice Assistant Started")
        print("=" * 50)
        print("📱 Supported Commands:")
        print("  • Brightness: 'increase brightness', 'brightness up', 'set brightness 70'")
        print("  • Volume: 'increase volume', 'volume up', 'set volume 50'")
        print("  • Apps: 'open chrome', 'open code', 'open notepad', 'open settings'")
        print("  • System: 'shutdown system', 'restart system', 'sleep system', 'lock system'")
        print("=" * 50)
        print("💡 Say a command directly (no wake word needed)...")
        print("⚠️  System commands require confirmation for safety!")
        print("🛑 Press Ctrl+C to stop")
        
        # Main execution loop
        self._main_loop()
    
    def _main_loop(self):
        """Main execution loop."""
        while self.is_running:
            try:
                print("\n🎤 Ready for command...")
                
                # Listen for command
                result = self._listen_for_speech(timeout=10.0)
                
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
                    print("⏰ Timeout: No command detected")
                    # Normal timeout, continue listening
                    continue
                
                elif result["status"] == "error":
                    error = result.get("text", "Unknown error")
                    self.logger.log_error("CommandError", error)
                    print(f"🔴 Error: {error}")
                    time.sleep(1.0)  # Brief pause before retry
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.log_error("MainLoopError", str(e))
                print(f"❌ Error: {e}")
                time.sleep(2.0)  # Pause before retry
        
        self.shutdown()
    
    def shutdown(self):
        """Shutdown the voice assistant."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Shutting down simple voice assistant...")
        
        # Cleanup resources
        if hasattr(self, 'audio'):
            try:
                self.audio.terminate()
            except:
                pass
        
        # Cleanup controllers
        if hasattr(self.brightness_controller, 'cleanup'):
            self.brightness_controller.cleanup()
        
        if self.volume_controller and hasattr(self.volume_controller, 'cleanup'):
            self.volume_controller.cleanup()
        
        if hasattr(self.app_launcher, 'cleanup'):
            self.app_launcher.cleanup()
        
        if hasattr(self.system_controller, 'cleanup'):
            self.system_controller.cleanup()
        
        self.logger.info("Simple voice assistant shutdown complete")
        print("👋 Voice assistant shutdown complete")


def main():
    """Main entry point."""
    assistant = SimpleVoiceAssistant()
    assistant.start()


if __name__ == "__main__":
    main()
