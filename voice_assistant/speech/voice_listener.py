"""
Core voice listener engine using VOSK for offline speech recognition.
Provides reusable passive and active listening modes with wake word detection.
"""

import json
import queue
import threading
import time
from typing import Dict, Optional, Any
import vosk
import numpy as np
import pyaudio

try:
    from .audio_stream_manager import AudioStreamManager
    from .wake_word_detector import WakeWordDetector
    from ..utils.logger import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from speech.audio_stream_manager import AudioStreamManager
    from speech.wake_word_detector import WakeWordDetector
    from utils.logger import get_logger


class VoiceListener:
    """
    Core voice listener engine with passive and active listening modes.
    Designed as a reusable component for future voice automation modules.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize voice listener.
        
        Args:
            config: Voice listener configuration
        """
        self.config = config
        self.logger = get_logger()
        
        # Initialize components
        self.audio_manager = AudioStreamManager(config["audio"])
        self.wake_word_detector = WakeWordDetector(
            config["wake_words"], 
            config["recognition"]["wake_word_threshold"]
        )
        
        # VOSK model and recognizer
        self.model = None
        self.recognizer = None
        self.model_loaded = False
        
        # Recognition settings
        self.command_confidence_threshold = config["recognition"]["command_confidence_threshold"]
        self.active_listening_timeout = config["recognition"]["active_listening_timeout"]
        self.max_retry_attempts = config["recognition"]["max_retry_attempts"]
        self.command_buffer_delay = config["recognition"].get("command_buffer_delay", 0.25)
        
        # State management
        self.is_listening = False
        self.is_active_mode = False
        self.recognition_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # Threading
        self.listening_thread = None
        
        self.logger.info("VoiceListener initialized")
    
    def load_model(self, grammar: Optional[list] = None) -> bool:
        """
        Load VOSK speech recognition model and initialize recognizer.
        
        Args:
            grammar: Optional list of allowed words/phrases
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            model_path = self.config["recognition"]["model_path"]
            
            # Check if model exists
            import os
            if not os.path.exists(model_path):
                self.logger.log_error("ModelNotFound", f"VOSK model not found at: {model_path}")
                self.logger.info("Please download vosk-model-small-en-us-0.15 and extract to models/ directory")
                self.logger.info("Download from: https://alphacephei.com/vosk/models")
                return False
            
            self.logger.log_audio_event("Loading VOSK model", f"Path: {model_path}")
            
            # Load VOSK model
            self.model = vosk.Model(model_path)
            self.model_loaded = True
            
            # Create recognizer with optional grammar
            if grammar:
                self.recognizer = vosk.KaldiRecognizer(
                    self.model, 
                    self.audio_manager.sample_rate,
                    json.dumps(grammar)
                )
            else:
                self.recognizer = vosk.KaldiRecognizer(
                    self.model, 
                    self.audio_manager.sample_rate
                )
            
            self.logger.log_audio_event("VOSK model loaded successfully", f"Grammar enabled: {grammar is not None}")
            return True
            
        except Exception as e:
            self.logger.log_error("ModelLoadError", str(e))
            return False
    
    def start_listening(self, grammar: Optional[list] = None) -> bool:
        """
        Start passive listening for wake words.
        
        Args:
            grammar: Optional list of allowed words/phrases
            
        Returns:
            True if listening started successfully, False otherwise
        """
        if self.is_listening:
            self.logger.warning("Voice listener is already running")
            return True
        
        # Initialize audio manager first to detect hardware capabilities
        if not self.audio_manager.initialize_audio():
            return False
            
        if not self.model_loaded:
            if not self.load_model(grammar):
                return False
        else:
            # Recreate recognizer to apply grammar or sample rate updates
            if grammar:
                self.recognizer = vosk.KaldiRecognizer(
                    self.model, 
                    self.audio_manager.sample_rate,
                    json.dumps(grammar)
                )
            else:
                self.recognizer = vosk.KaldiRecognizer(
                    self.model, 
                    self.audio_manager.sample_rate
                )
        
        # Start audio streaming
        if not self.audio_manager.start_stream(self._audio_callback):
            return False
        
        # Start listening thread
        self.stop_event.clear()
        self.is_listening = True
        self.listening_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.listening_thread.start()
        
        self.logger.log_audio_event("Voice listening started")
        return True
    
    def stop_listening(self) -> None:
        """Stop voice listening and cleanup resources."""
        if not self.is_listening:
            return
        
        self.logger.log_audio_event("Stopping voice listening")
        
        # Signal stop
        self.stop_event.set()
        self.is_listening = False
        self.is_active_mode = False
        
        # Wait for thread to finish
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=2.0)
        
        # Cleanup audio
        self.audio_manager.cleanup()
        
        self.logger.log_audio_event("Voice listening stopped")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Audio callback for PyAudio streaming.
        
        Args:
            in_data: Audio data
            frame_count: Number of frames
            time_info: Timing information
            status: Stream status
            
        Returns:
            Tuple of (data, flag)
        """
        if self.is_listening:
            # Lightweight denoise while always keeping stream continuity.
            # Important: do not drop silence frames, or VOSK finalization can break.
            try:
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                if audio_data.size == 0:
                    self.recognition_queue.put(in_data)
                    return (in_data, pyaudio.paContinue)

                centered = audio_data.astype(np.float32) - float(np.mean(audio_data))
                cleaned = np.clip(centered, -32768, 32767).astype(np.int16).tobytes()
                self.recognition_queue.put(cleaned)
            except Exception:
                # Fallback to raw audio on preprocessing failure.
                self.recognition_queue.put(in_data)
        
        return (in_data, pyaudio.paContinue)
    
    def _listening_loop(self) -> None:
        """Main listening loop for voice interaction."""
        while not self.stop_event.is_set():
            try:
                if (
                    self.is_active_mode
                    and hasattr(self, "active_listening_start")
                    and (time.time() - self.active_listening_start) > self.active_listening_timeout
                ):
                    self._handle_timeout()
                    continue

                # Get audio data from queue
                try:
                    audio_data = self.recognition_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                
                # Feed to VOSK
                if self.recognizer.AcceptWaveform(audio_data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        print(f"\r🎤 Final: {text}")
                        self._process_recognition_result(text)
                else:
                    # Show partial results
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get("partial", "").strip()
                    if partial_text:
                        print(f"\r📡 Listening: {partial_text}...", end="", flush=True)
                
                # No timeout in direct command mode
                
            except Exception as e:
                self.logger.log_error("ListeningLoopError", str(e))
                time.sleep(0.1)

    def _process_recognition_result(self, text: str) -> None:
        """Process finalized speech text with wake-word gating."""
        normalized = " ".join((text or "").lower().split())
        if not normalized:
            return

        # Passive mode: only wake words are accepted.
        if not self.is_active_mode:
            detected, wake_word, confidence = self.wake_word_detector.detect_wake_word(normalized)
            if not detected:
                return

            self.logger.log_audio_event(
                "Wake word detected",
                f"{wake_word} ({confidence:.2f})",
            )
            self._enter_active_mode()

            # If wake phrase and command came together in one final chunk,
            # remove wake words and execute remaining command immediately.
            command_text = self._strip_wake_words(normalized)
            if command_text:
                self._handle_command_recognition(command_text)
                self.is_active_mode = False
            return

        # Active mode: accept one command, then return to passive mode.
        command_text = self._strip_wake_words(normalized)
        if not command_text:
            return
        self._handle_command_recognition(command_text)
        self.is_active_mode = False

    def _strip_wake_words(self, text: str) -> str:
        cleaned = f" {text} "
        for wake in self.config.get("wake_words", []):
            w = " ".join(str(wake).lower().split())
            if w:
                cleaned = cleaned.replace(f" {w} ", " ")
        return " ".join(cleaned.split())

    def _enter_active_mode(self) -> None:
        """Switch to active command listening mode."""
        self.is_active_mode = True
        self.active_listening_start = time.time()
        self.logger.log_audio_event("Entered active listening mode")
        print("\n✨ How can I help you?")

    def _handle_command_recognition(self, text: str) -> None:
        """Store command result for processing."""
        self.logger.log_command_received(text)
        if self.command_buffer_delay > 0:
            time.sleep(self.command_buffer_delay)
        self.last_result = {"status": "success", "text": text}
        print(f"\r🎙️  Heard: '{text}'")

    def _handle_timeout(self) -> None:
        """Handle listening timeout."""
        self.logger.log_audio_event("Active listening timeout")
        self.last_result = {"status": "timeout", "text": ""}
        self.is_active_mode = False
        print("\n⌛ Listening timed out.")
    
    def listen(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Listen for voice command.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with recognition result
        """
        if not self.is_listening:
            return {
                "status": "error",
                "text": "",
                "confidence": 0.0
            }
        
        # Wait for result
        start_time = time.time()
        timeout = timeout or 10.0
        
        while not hasattr(self, 'last_result') and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if hasattr(self, 'last_result'):
            result = self.last_result.copy()
            delattr(self, 'last_result')
            return result
        else:
            return {
                "status": "timeout",
                "text": "",
                "confidence": 0.0
            }
    
    def is_active(self) -> bool:
        """
        Check if listener is currently active.
        
        Returns:
            True if listening, False otherwise
        """
        return self.is_listening
    
    def cleanup(self) -> None:
        """Cleanup all resources."""
        self.stop_listening()
        
        if self.model:
            del self.model
            self.model = None
            self.model_loaded = False
        
        if self.recognizer:
            del self.recognizer
            self.recognizer = None
