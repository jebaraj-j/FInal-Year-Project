"""
Core voice listener engine using VOSK for offline speech recognition.
Provides reusable passive and active listening modes with wake word detection.
"""

import json
import queue
import threading
import time
import re
from difflib import SequenceMatcher
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

        # Stop words that deactivate listening until wake word is said again
        self.stop_words = ["stop nora", "nora stop", "stop listening"]
        self.on_stop_word = None   # optional callback: fn() called when stop word heard
        
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
            # Keep raw stream continuity for VOSK stability.
            # Aggressive waveform transforms can cause transcript artifacts.
            self.recognition_queue.put(in_data)
        
        return (in_data, pyaudio.paContinue)
    
    def _listening_loop(self) -> None:
        """Main listening loop for voice interaction."""
        while not self.stop_event.is_set():
            try:
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
                        cleaned_text = self._clean_transcript(text)
                        if cleaned_text:
                            if self.is_active_mode:
                                print(f"\rFinal: {cleaned_text}")
                            self._process_recognition_result(cleaned_text)
                else:
                    if self.is_active_mode:
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get("partial", "").strip()
                        if partial_text:
                            cleaned_partial = self._clean_transcript(partial_text)
                            if cleaned_partial:
                                print(f"\rListening: {cleaned_partial}...", end="", flush=True)
                
                # No timeout in direct command mode
                
            except Exception as e:
                self.logger.log_error("ListeningLoopError", str(e))
                time.sleep(0.1)

    def _process_recognition_result(self, text: str) -> None:
        """Process finalized speech text with wake-word gating."""
        try:
            self._process_recognition_result_safe(text)
        except Exception as e:
            self.logger.log_error("RecognitionResultError", str(e))

    def _process_recognition_result_safe(self, text: str) -> None:
        """Inner implementation - exceptions caught by caller."""
        normalized = self._clean_transcript(text)
        if not normalized:
            return

        # Stop word check — works in both passive and active mode
        for sw in self.stop_words:
            if sw in normalized or normalized == sw:
                self.is_active_mode = False
                self.logger.log_audio_event("Stop word detected", sw)
                print("\nNora stopped. Say a wake word to start again.")
                if self.on_stop_word:
                    self.on_stop_word()
                return

        # Passive mode: only wake words are accepted.
        if not self.is_active_mode:
            detected, wake_word, confidence = self._detect_wake_word_strict(normalized)
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
            if command_text and not self._is_wake_residue(command_text):
                self._handle_command_recognition(command_text)
                self.is_active_mode = False
            return

        # Active mode: accept one command, then return to passive mode.
        command_text = self._strip_wake_words(normalized)
        if not command_text:
            # Wake phrase repeated while active: keep waiting for command.
            self.active_listening_start = time.time()
            return
        if self._is_wake_residue(command_text):
            # Ignore wake residue/noise terms without exiting active mode.
            self.active_listening_start = time.time()
            return
        self._handle_command_recognition(command_text)
        # Stay in active mode - user can give next command without wake word
        self.active_listening_start = time.time()


    def _clean_transcript(self, text: str) -> str:
        """Normalize transcript and remove VOSK suffix-echo artifacts."""
        raw = (text or "").lower().strip()
        if not raw:
            return ""
        tokens = re.findall(r"[a-z0-9]+", raw)
        if not tokens:
            return ""
        cleaned = []
        for tok in tokens:
            cleaned.append(self._remove_suffix_echo(tok))
        # Collapse consecutive identical tokens
        collapsed = []
        for t in cleaned:
            if collapsed and collapsed[-1] == t:
                continue
            collapsed.append(t)
        return " ".join(collapsed)

    def _remove_suffix_echo(self, tok: str) -> str:
        """Remove VOSK suffix-echo artifacts.
        Handles: 'chromerome'->'chrome', 'shutdowndown'->'shutdown', 'zoomzoom'->'zoom'.
        """
        n = len(tok)
        # Try every tail length from 3 up to len//2
        for tail_len in range(3, n // 2 + 1):
            tail = tok[n - tail_len:]
            base = tok[:n - tail_len]
            if base and base.endswith(tail):
                return base
        return tok

    def _contains_phrase_whole(self, text: str, phrase: str) -> bool:
        return f" {phrase} " in f" {text} "

    def _detect_wake_word_strict(self, text: str):
        """
        Strict wake detection:
        1) whole-phrase match first
        2) high similarity fallback (>=0.85) for multi-word input only
        """
        wake_words = [" ".join(str(w).lower().split()) for w in self.config.get("wake_words", [])]
        for wake in wake_words:
            if wake and self._contains_phrase_whole(text, wake):
                return True, wake, 1.0

        if len(text.split()) < 2:
            return False, None, 0.0

        best_wake = None
        best_score = 0.0
        for wake in wake_words:
            if not wake:
                continue
            score = SequenceMatcher(None, text, wake).ratio()
            if score > best_score:
                best_score = score
                best_wake = wake
        if best_wake and best_score >= 0.85:
            return True, best_wake, best_score
        return False, None, best_score

    def _strip_wake_words(self, text: str) -> str:
        cleaned = f" {text} "
        for wake in self.config.get("wake_words", []):
            w = " ".join(str(wake).lower().split())
            if w:
                cleaned = cleaned.replace(f" {w} ", " ")
        tokens = cleaned.split()
        residue_tokens = {"hey", "ok", "hi", "hello", "nora", "on"}
        # Common wake-word corruption artifact in transcripts.
        residue_tokens.add("ona")
        # Trim wake residue from beginning/end without touching middle command words.
        while tokens and tokens[0] in residue_tokens:
            tokens.pop(0)
        while tokens and tokens[-1] in residue_tokens:
            tokens.pop()
        return " ".join(tokens)

    def _is_wake_residue(self, text: str) -> bool:
        """
        Detect common wake/noise residue so it does not consume active mode.
        """
        tokens = [t for t in text.split() if t]
        if not tokens:
            return True
        residue_tokens = {"hey", "ok", "hi", "hello", "nora", "on", "ona"}
        return all(t in residue_tokens for t in tokens)

    def _enter_active_mode(self) -> None:
        """Switch to active command listening mode."""
        self.is_active_mode = True
        self.active_listening_start = time.time()
        self.logger.log_audio_event("Entered active listening mode")
        print("\nHow can I help you?")

    def _handle_command_recognition(self, text: str) -> None:
        """Store command result for processing."""
        self.logger.log_command_received(text)
        if self.command_buffer_delay > 0:
            time.sleep(self.command_buffer_delay)
        self.last_result = {"status": "success", "text": text}
        print(f"\rHeard: '{text}'")

    def _handle_timeout(self) -> None:
        """Handle listening timeout."""
        self.logger.log_audio_event("Active listening timeout")
        self.last_result = {"status": "timeout", "text": ""}
        self.is_active_mode = False
        print("\nListening timed out.")
    
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
