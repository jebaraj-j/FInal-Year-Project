#!/usr/bin/env python3
"""
Production-ready voice assistant with optimized speech recognition.
Uses enhanced audio processing and intelligent command detection.
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
from typing import Dict, Any, List
from fuzzywuzzy import fuzz

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


class ProductionVoiceAssistant:
    """
    Production-ready voice assistant with optimized speech recognition.
    """
    
    def __init__(self):
        """Initialize production voice assistant."""
        # Load configuration
        self.config = self._load_config()
        
        # Initialize logger
        log_level = self.config["logging"]["level"]
        log_dir = Path(__file__).parent / "logs"
        self.logger = get_logger(str(log_dir), log_level)
        
        # Initialize controllers
        self.brightness_controller = BrightnessController()
        self.volume_controller = None
        self.app_launcher = ApplicationLauncher()
        self.system_controller = SystemController()
        
        # Initialize intent engines
        commands_config = self._load_commands_config()
        self.brightness_intent_engine = BrightnessIntentEngine(
            commands_config,
            self.config["noise_words"]
        )
        self.volume_intent_engine = None
        self.app_intent_engine = AppIntentEngine(
            commands_config,
            self.config["noise_words"],
            self.app_launcher.get_available_apps()
        )
        self.system_intent_engine = SystemIntentEngine(
            commands_config,
            self.config["noise_words"]
        )
        
        # Command patterns for intelligent matching
        self.command_patterns = self._load_command_patterns()
        
        # Runtime state
        self.is_running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("ProductionVoiceAssistant initialized")
    
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
    
    def _load_command_patterns(self) -> Dict[str, List[str]]:
        """Load command patterns with variations."""
        return {
            "brightness": {
                "increase": ["increase brightness", "brightness up", "brighter", "more brightness", "increase bright"],
                "decrease": ["decrease brightness", "brightness down", "dimmer", "less brightness", "decrease bright"],
                "set": ["set brightness", "brightness", "bright", "set bright"]
            },
            "volume": {
                "increase": ["increase volume", "volume up", "louder", "more volume", "increase sound"],
                "decrease": ["decrease volume", "volume down", "quieter", "less volume", "decrease sound"],
                "set": ["set volume", "volume", "sound", "set sound"]
            },
            "app_launch": {
                "chrome": ["open chrome", "start chrome", "launch chrome", "chrome"],
                "code": ["open code", "start code", "launch code", "code", "vs code"],
                "notepad": ["open notepad", "start notepad", "launch notepad", "notepad"],
                "settings": ["open settings", "start settings", "launch settings", "settings"],
                "explorer": ["open explorer", "start explorer", "launch explorer", "explorer", "file explorer"]
            },
            "system_control": {
                "shutdown": ["shutdown system", "turn off computer", "shutdown", "turn off"],
                "restart": ["restart system", "reboot computer", "restart", "reboot"],
                "sleep": ["sleep system", "sleep computer", "sleep"],
                "lock": ["lock system", "lock computer", "lock"]
            }
        }
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def _intelligent_command_match(self, text: str) -> Dict[str, Any]:
        """
        Intelligent command matching with multiple strategies.
        
        Args:
            text: Recognized speech text
            
        Returns:
            Dictionary with matched command info
        """
        text_lower = text.lower().strip()
        best_match = {"category": None, "action": None, "confidence": 0.0}
        
        # Strategy 1: Direct pattern matching
        for category, actions in self.command_patterns.items():
            for action, patterns in actions.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        confidence = len(pattern) / len(text_lower) if len(text_lower) > 0 else 0
                        if confidence > best_match["confidence"]:
                            best_match = {
                                "category": category,
                                "action": action,
                                "confidence": confidence,
                                "matched_pattern": pattern
                            }
        
        # Strategy 2: Key word matching
        if best_match["confidence"] < 0.7:
            for category, actions in self.command_patterns.items():
                for action, patterns in actions.items():
                    # Count matching key words
                    pattern_words = set()
                    for pattern in patterns:
                        pattern_words.update(pattern.split())
                    
                    text_words = set(text_lower.split())
                    common_words = pattern_words & text_words
                    
                    if common_words:
                        confidence = len(common_words) / max(len(pattern_words), 1)
                        if confidence > best_match["confidence"] and confidence > 0.3:
                            best_match = {
                                "category": category,
                                "action": action,
                                "confidence": confidence,
                                "matched_words": list(common_words)
                            }
        
        # Strategy 3: Fuzzy matching for close matches
        if best_match["confidence"] < 0.6:
            for category, actions in self.command_patterns.items():
                for action, patterns in actions.items():
                    for pattern in patterns:
                        score = fuzz.ratio(text_lower, pattern.lower()) / 100.0
                        if score > best_match["confidence"] and score > 0.5:
                            best_match = {
                                "category": category,
                                "action": action,
                                "confidence": score,
                                "fuzzy_pattern": pattern
                            }
        
        return best_match
    
    def _optimized_recognition(self, timeout: float = 6.0) -> Dict[str, Any]:
        """
        Optimized speech recognition with better audio processing.
        
        Args:
            timeout: Recognition timeout
            
        Returns:
            Recognition result
        """
        try:
            # Initialize VOSK if not already done
            if not hasattr(self, 'model'):
                model_path = self.config["recognition"]["model_path"]
                if not os.path.exists(model_path):
                    return {"status": "error", "text": "VOSK model not found"}
                
                self.model = vosk.Model(model_path)
                self.recognizer = vosk.KaldiRecognizer(self.model, self.config["audio"]["sample_rate"])
                self.audio = pyaudio.PyAudio()
            
            # Open audio stream with optimized settings
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.config["audio"]["channels"],
                rate=self.config["audio"]["sample_rate"],
                input=True,
                input_device_index=self.config["audio"]["input_device_index"],
                frames_per_buffer=self.config["audio"]["chunk_size"]
            )
            
            print("🎤 Listening...")
            
            # Record with energy-based speech detection
            audio_buffer = []
            speech_detected = False
            silence_start = None
            energy_threshold = 500  # Adjust based on your microphone
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    data = stream.read(self.config["audio"]["chunk_size"], exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    
                    # Calculate energy
                    energy = np.sqrt(np.mean(audio_chunk.astype(float)**2))
                    
                    # Speech detection
                    if energy > energy_threshold:
                        if not speech_detected:
                            speech_detected = True
                            print("🗣️ Speech detected...")
                        silence_start = None
                        audio_buffer.append(data)
                    elif speech_detected and silence_start is None:
                        silence_start = time.time()
                    elif speech_detected and silence_start is not None:
                        if time.time() - silence_start > 1.0:  # 1 second of silence
                            break
                    elif speech_detected:
                        audio_buffer.append(data)
                    
                    # Try real-time recognition
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '')
                        if text:
                            stream.stop_stream()
                            stream.close()
                            return {"status": "success", "text": text, "confidence": 1.0}
                            
                except Exception as e:
                    self.logger.log_error("AudioProcessingError", str(e))
                    break
            
            # Process final audio
            if audio_buffer:
                final_result = self.recognizer.FinalResult()
                result = json.loads(final_result)
                text = result.get('text', '')
                
                if text:
                    stream.stop_stream()
                    stream.close()
                    return {"status": "success", "text": text, "confidence": 1.0}
            
            stream.stop_stream()
            stream.close()
            return {"status": "timeout", "text": "", "confidence": 0.0}
            
        except Exception as e:
            self.logger.log_error("OptimizedRecognitionError", str(e))
            return {"status": "error", "text": str(e), "confidence": 0.0}
    
    def _process_command(self, text: str) -> bool:
        """Process recognized voice command."""
        try:
            print(f"🔍 Analyzing: '{text}'")
            
            # Intelligent command matching
            match = self._intelligent_command_match(text)
            
            if match["confidence"] > 0.6:
                category = match["category"]
                action = match["action"]
                confidence = match["confidence"]
                
                print(f"✅ Detected: {category} - {action} (confidence: {confidence:.2f})")
                
                # Route to appropriate handler
                if category == "brightness":
                    if action == "increase":
                        return self.brightness_controller.execute_action("relative_increase")
                    elif action == "decrease":
                        return self.brightness_controller.execute_action("relative_decrease")
                    elif action == "set":
                        # Try to extract value from text
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            value = int(numbers[0])
                            return self.brightness_controller.execute_action("set_value", value)
                        else:
                            print("⚠️  Please specify a brightness value (0-100)")
                            return False
                
                elif category == "volume":
                    if not self.volume_controller:
                        from volume_control.volume_controller import VolumeController
                        self.volume_controller = VolumeController()
                    
                    if not self.volume_intent_engine:
                        self.volume_intent_engine = VolumeIntentEngine(
                            self._load_commands_config(),
                            self.config["noise_words"]
                        )
                    
                    if action == "increase":
                        return self.volume_controller.execute_action("relative_increase")
                    elif action == "decrease":
                        return self.volume_controller.execute_action("relative_decrease")
                    elif action == "set":
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            value = int(numbers[0])
                            return self.volume_controller.execute_action("set_value", value)
                        else:
                            print("⚠️  Please specify a volume value (0-100)")
                            return False
                
                elif category == "app_launch":
                    # Map action to app name
                    app_mapping = {
                        "chrome": "chrome",
                        "code": "code", 
                        "notepad": "notepad",
                        "settings": "settings",
                        "explorer": "explorer"
                    }
                    
                    app_name = app_mapping.get(action)
                    if app_name:
                        return self.app_launcher.execute_action(app_name)
                
                elif category == "system_control":
                    # Map action to system action
                    system_mapping = {
                        "shutdown": "shutdown",
                        "restart": "restart",
                        "sleep": "sleep",
                        "lock": "lock"
                    }
                    
                    system_action = system_mapping.get(action)
                    if system_action:
                        # Handle system control with confirmation
                        requires_confirmation = self.system_intent_engine.requires_confirmation(system_action)
                        
                        if requires_confirmation:
                            confirmation_message = self.system_controller._get_confirmation_message(system_action)
                            print(f"\n🚨 {confirmation_message}")
                            print("⏰ Say 'yes' or 'no' within 5 seconds...")
                            
                            confirmation_result = self._optimized_recognition(timeout=5.0)
                            
                            if confirmation_result["status"] == "success":
                                response_text = confirmation_result.get("text", "").strip().lower()
                                if response_text in ["yes", "yeah", "yep", "sure", "ok"]:
                                    success = self.system_controller.execute_confirmed_action(system_action)
                                    if success:
                                        print("✅ System action executed successfully")
                                        return True
                                else:
                                    print("❌ System action cancelled")
                                    return False
                            else:
                                print("❌ System action cancelled (timeout)")
                                return False
                        else:
                            success = self.system_controller.execute_action(system_action, require_confirmation=False)
                            if success:
                                print("✅ System action executed successfully")
                                return True
            
            # Fallback to intent engines
            print("🔍 Trying intent engines...")
            
            # Try brightness intent engine
            intent = self.brightness_intent_engine.parse_intent(text)
            if intent["action"]:
                print(f"✅ Brightness intent: {intent['action']}")
                return self.brightness_controller.execute_action(intent["action"], intent.get("value"))
            
            # Try app intent engine
            intent = self.app_intent_engine.parse_intent(text)
            if intent["app"]:
                print(f"✅ App intent: {intent['app']}")
                return self.app_launcher.execute_action(intent["app"])
            
            # Try system intent engine
            intent = self.system_intent_engine.parse_intent(text)
            if intent["action"]:
                print(f"✅ System intent: {intent['action']}")
                return self.system_controller.execute_action(intent["action"])
            
            print(f"❓ No command detected in: '{text}'")
            print("💡 Try speaking clearly or check the command list")
            return False
            
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e))
            print(f"❌ Error processing command: {e}")
            return False
    
    def start(self):
        """Start the production voice assistant."""
        if self.is_running:
            self.logger.warning("Voice assistant is already running")
            return
        
        self.logger.info("Starting production voice assistant...")
        
        self.is_running = True
        self.logger.info("Production voice assistant started successfully")
        
        # Display available commands
        print("🎤 Production Voice Assistant Started")
        print("=" * 50)
        print("📱 Supported Commands:")
        print("  • Brightness: 'increase brightness', 'brightness up', 'set brightness 70'")
        print("  • Volume: 'increase volume', 'volume up', 'set volume 50'")
        print("  • Apps: 'open chrome', 'open code', 'open notepad', 'open settings'")
        print("  • System: 'shutdown system', 'restart system', 'sleep system', 'lock system'")
        print("=" * 50)
        print("💡 Speak clearly and directly - optimized for accuracy")
        print("🎯 Intelligent command detection with fuzzy matching")
        print("⚠️  System commands require confirmation for safety!")
        print("🛑 Press Ctrl+C to stop")
        
        # Main execution loop
        self._main_loop()
    
    def _main_loop(self):
        """Main execution loop."""
        while self.is_running:
            try:
                print("\n🎤 Ready for command...")
                
                # Optimized recognition
                result = self._optimized_recognition(timeout=6.0)
                
                if result["status"] == "success":
                    command_text = result.get("text", "").strip()
                    
                    if command_text:
                        self.logger.info(f"Command received: '{command_text}'")
                        print(f"📝 Recognized: {command_text}")
                        
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
                
                elif result["status"] == "error":
                    error = result.get("text", "Unknown error")
                    self.logger.log_error("CommandError", error)
                    print(f"🔴 Error: {error}")
                    time.sleep(1.0)
                
                else:
                    print("⏰ Timeout: No command detected")
                    # Normal timeout, continue listening
                    continue
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.log_error("MainLoopError", str(e))
                print(f"❌ Error: {e}")
                time.sleep(2.0)
        
        self.shutdown()
    
    def shutdown(self):
        """Shutdown the voice assistant."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Shutting down production voice assistant...")
        
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
        
        self.logger.info("Production voice assistant shutdown complete")
        print("👋 Voice assistant shutdown complete")


def main():
    """Main entry point."""
    assistant = ProductionVoiceAssistant()
    assistant.start()


if __name__ == "__main__":
    main()
