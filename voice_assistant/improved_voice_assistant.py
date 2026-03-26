#!/usr/bin/env python3
"""
Improved voice assistant with better speech recognition accuracy.
Uses multiple recognition attempts and fuzzy matching for command detection.
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


class ImprovedVoiceAssistant:
    """
    Improved voice assistant with better speech recognition accuracy.
    Uses multiple attempts and fuzzy matching for reliable command detection.
    """
    
    def __init__(self):
        """Initialize improved voice assistant."""
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
        
        # Command patterns for fuzzy matching
        self.command_patterns = self._load_command_patterns()
        
        # Runtime state
        self.is_running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("ImprovedVoiceAssistant initialized")
    
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
        """Load all command patterns for fuzzy matching."""
        patterns = {
            "brightness": [
                "increase brightness", "brightness up", "decrease brightness", "brightness down",
                "set brightness", "brighter", "dimmer", "more brightness", "less brightness",
                "maximum brightness", "minimum brightness", "full brightness", "turn off brightness"
            ],
            "volume": [
                "increase volume", "volume up", "decrease volume", "volume down",
                "set volume", "louder", "quieter", "more volume", "less volume",
                "maximum volume", "minimum volume", "full volume", "turn off volume",
                "sound up", "sound down", "increase sound", "decrease sound"
            ],
            "app_launch": [
                "open chrome", "open code", "open notepad", "open settings", "open explorer",
                "start chrome", "start code", "start notepad", "start settings", "start explorer",
                "launch chrome", "launch code", "launch notepad", "launch settings", "launch explorer",
                "chrome", "code", "notepad", "settings", "explorer"
            ],
            "system_control": [
                "shutdown system", "restart system", "sleep system", "lock system",
                "turn off computer", "reboot computer", "sleep computer", "lock computer",
                "shutdown", "restart", "sleep", "lock"
            ]
        }
        return patterns
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def _fuzzy_match_command(self, text: str) -> Dict[str, Any]:
        """
        Use fuzzy matching to detect commands from recognized text.
        
        Args:
            text: Recognized speech text
            
        Returns:
            Dictionary with matched command and confidence
        """
        text_lower = text.lower().strip()
        best_match = {"category": None, "command": None, "confidence": 0.0}
        
        # Try fuzzy matching against all command patterns
        for category, patterns in self.command_patterns.items():
            for pattern in patterns:
                # Calculate fuzzy match score
                score = fuzz.ratio(text_lower, pattern.lower()) / 100.0
                
                # Also check if pattern is contained in text
                if pattern.lower() in text_lower:
                    score = max(score, 0.8)  # Boost score for containment
                
                # Check for partial matches (key words)
                key_words = pattern.split()
                matched_words = sum(1 for word in key_words if word in text_lower)
                if matched_words > 0:
                    partial_score = matched_words / len(key_words)
                    score = max(score, partial_score * 0.7)  # Weight partial matches lower
                
                if score > best_match["confidence"] and score > 0.6:  # Minimum threshold
                    best_match = {
                        "category": category,
                        "command": pattern,
                        "confidence": score
                    }
        
        return best_match
    
    def _enhanced_recognition(self, timeout: float = 8.0) -> List[Dict[str, Any]]:
        """
        Perform enhanced speech recognition with multiple attempts.
        
        Args:
            timeout: Total timeout for recognition
            
        Returns:
            List of recognition results
        """
        results = []
        
        try:
            # Initialize VOSK if not already done
            if not hasattr(self, 'model'):
                model_path = self.config["recognition"]["model_path"]
                if not os.path.exists(model_path):
                    return [{"status": "error", "text": "VOSK model not found"}]
                
                self.model = vosk.Model(model_path)
                self.recognizer = vosk.KaldiRecognizer(self.model, self.config["audio"]["sample_rate"])
                self.audio = pyaudio.PyAudio()
            
            # Multiple short recognition attempts
            attempt_timeout = timeout / 3  # Divide time into 3 attempts
            
            for attempt in range(3):
                try:
                    # Open audio stream
                    stream = self.audio.open(
                        format=pyaudio.paInt16,
                        channels=self.config["audio"]["channels"],
                        rate=self.config["audio"]["sample_rate"],
                        input=True,
                        input_device_index=self.config["audio"]["input_device_index"],
                        frames_per_buffer=self.config["audio"]["chunk_size"]
                    )
                    
                    print(f"🎤 Attempt {attempt + 1}/3 - Listening...")
                    
                    # Record and recognize
                    start_time = time.time()
                    audio_data = []
                    
                    while time.time() - start_time < attempt_timeout:
                        try:
                            data = stream.read(self.config["audio"]["chunk_size"], exception_on_overflow=False)
                            audio_data.append(data)
                            
                            # Try to recognize in real-time
                            if self.recognizer.AcceptWaveform(data):
                                result = json.loads(self.recognizer.Result())
                                text = result.get('text', '')
                                if text:
                                    results.append({
                                        "status": "success",
                                        "text": text,
                                        "confidence": 1.0,
                                        "attempt": attempt + 1
                                    })
                                    break
                                    
                        except Exception as e:
                            self.logger.log_error("AudioReadError", str(e))
                            break
                    
                    # Process final result for this attempt
                    if audio_data and not any(r["status"] == "success" and r["attempt"] == attempt + 1 for r in results):
                        final_result = self.recognizer.FinalResult()
                        result = json.loads(final_result)
                        text = result.get('text', '')
                        
                        if text:
                            results.append({
                                "status": "success",
                                "text": text,
                                "confidence": 1.0,
                                "attempt": attempt + 1
                            })
                    
                    stream.stop_stream()
                    stream.close()
                    
                    # If we got a good result, stop trying
                    if results:
                        best_result = max(results, key=lambda x: len(x["text"]))
                        if len(best_result["text"].split()) >= 2:  # At least 2 words
                            break
                
                except Exception as e:
                    self.logger.log_error("RecognitionAttemptError", str(e))
                    continue
            
        except Exception as e:
            self.logger.log_error("EnhancedRecognitionError", str(e))
            return [{"status": "error", "text": str(e)}]
        
        return results if results else [{"status": "timeout", "text": "", "confidence": 0.0}]
    
    def _process_command(self, text: str) -> bool:
        """Process recognized voice command."""
        try:
            print(f"🔍 Processing: '{text}'")
            
            # Try fuzzy matching first
            fuzzy_match = self._fuzzy_match_command(text)
            
            if fuzzy_match["confidence"] > 0.7:
                category = fuzzy_match["category"]
                print(f"✅ Fuzzy matched: {category} (confidence: {fuzzy_match['confidence']:.2f})")
                
                # Route to appropriate handler
                if category == "brightness":
                    intent = self.brightness_intent_engine.parse_intent(text)
                    if intent["action"]:
                        return self.brightness_controller.execute_action(
                            intent["action"],
                            intent.get("value")
                        )
                
                elif category == "volume":
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
                
                elif category == "app_launch":
                    intent = self.app_intent_engine.parse_intent(text)
                    if intent["app"]:
                        return self.app_launcher.execute_action(intent["app"])
                
                elif category == "system_control":
                    intent = self.system_intent_engine.parse_intent(text)
                    if intent["action"]:
                        # Handle system control with confirmation
                        requires_confirmation = self.system_intent_engine.requires_confirmation(intent["action"])
                        
                        if requires_confirmation:
                            confirmation_message = self.system_controller._get_confirmation_message(intent["action"])
                            print(f"\n🚨 {confirmation_message}")
                            print("⏰ Say 'yes' or 'no' within 5 seconds...")
                            
                            confirmation_result = self._enhanced_recognition(timeout=5.0)
                            
                            if confirmation_result and confirmation_result[0]["status"] == "success":
                                response_text = confirmation_result[0].get("text", "").strip().lower()
                                if response_text in ["yes", "yeah", "yep", "sure", "ok"]:
                                    success = self.system_controller.execute_confirmed_action(intent["action"])
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
                            success = self.system_controller.execute_action(intent["action"], require_confirmation=False)
                            if success:
                                print("✅ System action executed successfully")
                                return True
            
            # If fuzzy matching failed, try intent engines
            print("🔍 Trying intent engines...")
            
            # Try brightness
            intent = self.brightness_intent_engine.parse_intent(text)
            if intent["action"]:
                print(f"✅ Brightness intent detected: {intent['action']}")
                return self.brightness_controller.execute_action(intent["action"], intent.get("value"))
            
            # Try app launcher
            intent = self.app_intent_engine.parse_intent(text)
            if intent["app"]:
                print(f"✅ App intent detected: {intent['app']}")
                return self.app_launcher.execute_action(intent["app"])
            
            # Try system control
            intent = self.system_intent_engine.parse_intent(text)
            if intent["action"]:
                print(f"✅ System intent detected: {intent['action']}")
                return self.system_controller.execute_action(intent["action"])
            
            print(f"❓ No command detected in: '{text}'")
            return False
            
        except Exception as e:
            self.logger.log_error("CommandProcessError", str(e))
            print(f"❌ Error processing command: {e}")
            return False
    
    def start(self):
        """Start the improved voice assistant."""
        if self.is_running:
            self.logger.warning("Voice assistant is already running")
            return
        
        self.logger.info("Starting improved voice assistant...")
        
        self.is_running = True
        self.logger.info("Improved voice assistant started successfully")
        
        # Display available commands
        print("🎤 Improved Voice Assistant Started")
        print("=" * 50)
        print("📱 Supported Commands:")
        print("  • Brightness: 'increase brightness', 'brightness up', 'set brightness 70'")
        print("  • Volume: 'increase volume', 'volume up', 'set volume 50'")
        print("  • Apps: 'open chrome', 'open code', 'open notepad', 'open settings'")
        print("  • System: 'shutdown system', 'restart system', 'sleep system', 'lock system'")
        print("=" * 50)
        print("💡 Speak clearly and directly - no wake word needed")
        print("🎯 Uses fuzzy matching for better accuracy")
        print("⚠️  System commands require confirmation for safety!")
        print("🛑 Press Ctrl+C to stop")
        
        # Main execution loop
        self._main_loop()
    
    def _main_loop(self):
        """Main execution loop."""
        while self.is_running:
            try:
                print("\n🎤 Ready for command...")
                
                # Enhanced recognition with multiple attempts
                results = self._enhanced_recognition(timeout=8.0)
                
                if results and results[0]["status"] == "success":
                    # Get the best result
                    best_result = max(results, key=lambda x: len(x["text"]))
                    command_text = best_result.get("text", "").strip()
                    
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
                
                elif results and results[0]["status"] == "error":
                    error = results[0].get("text", "Unknown error")
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
        self.logger.info("Shutting down improved voice assistant...")
        
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
        
        self.logger.info("Improved voice assistant shutdown complete")
        print("👋 Voice assistant shutdown complete")


def main():
    """Main entry point."""
    assistant = ImprovedVoiceAssistant()
    assistant.start()


if __name__ == "__main__":
    main()
