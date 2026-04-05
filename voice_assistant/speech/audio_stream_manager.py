"""
Audio stream manager for voice assistant.
Handles microphone detection, audio streaming, and error recovery.
"""

import pyaudio
import numpy as np
import time
from typing import Optional, Callable, Dict, Any
try:
    from ..utils.logger import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger


class AudioStreamManager:
    """Manages audio input streaming with automatic device detection and error recovery."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize audio stream manager.
        
        Args:
            config: Audio configuration dictionary
        """
        self.config = config
        self.logger = get_logger()
        self.audio = None
        self.stream = None
        self.is_streaming = False
        self.retry_count = 0
        self.max_retries = config.get("max_retry_attempts", 3)
        
        # Audio parameters
        self.sample_rate = config.get("sample_rate", 16000)
        self.chunk_size = config.get("chunk_size", 1024)
        self.channels = config.get("channels", 1)
        self.format = pyaudio.paInt16
        self.silence_threshold = config.get("silence_threshold", 500)
        self.silence_timeout = config.get("silence_timeout", 1.0)
        
        # Device management
        self.device_index = config.get("input_device_index", None)
        self.auto_detect_device = config.get("auto_detect_device", True)
        
        self.logger.log_audio_event("AudioStreamManager initialized")
    
    def initialize_audio(self) -> bool:
        """
        Initialize PyAudio instance and detect audio device.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.audio = pyaudio.PyAudio()
            
            if self.auto_detect_device and self.device_index is None:
                self.device_index = self._detect_default_device()
                if self.device_index is not None:
                    device_info = self.audio.get_device_info_by_index(self.device_index)
                    self.logger.log_audio_event("Auto-detected audio device", 
                                              f"{device_info['name']} (Index: {self.device_index})")
                else:
                    self.logger.log_error("AudioDeviceError", "No suitable audio device found")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.log_error("AudioInitializationError", str(e))
            return False
    
    def _detect_default_device(self) -> Optional[int]:
        """
        Detect the best input device.
        Prioritizes devices with 'Microphone' in name and avoids virtual mappers.
        
        Returns:
            Device index or None if not found
        """
        try:
            devices = []
            for i in range(self.audio.get_device_count()):
                try:
                    info = self.audio.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        devices.append(info)
                except:
                    continue

            # Bluetooth hands-free profile is often unstable for low-latency capture
            # and can cause [Errno -9999] Unanticipated host error on stream start.
            # Prefer wired/built-in microphone devices first.
            def _is_unstable_handsfree(device_name: str) -> bool:
                n = device_name.lower()
                return (
                    "hands-free" in n
                    or "bthhfenum" in n
                    or ("bluetooth" in n and "headset" in n)
                )

            # 1. Try PyAudio's official default input first (if stable)
            try:
                default_info = self.audio.get_default_input_device_info()
                default_name = default_info['name']
                if (
                    "Mapping" not in default_name
                    and "Mapper" not in default_name
                    and not _is_unstable_handsfree(default_name)
                ):
                    if self._is_rate_supported(default_info['index'], self.sample_rate):
                        return default_info['index']
            except:
                pass

            # 2. Then try microphone/array devices (excluding unstable hands-free)
            for info in devices:
                name = info['name'].lower()
                if any(k in name for k in ["microphone", "input", "array"]):
                    if (
                        "mapper" not in name
                        and "virtual" not in name
                        and not _is_unstable_handsfree(name)
                    ):
                        if self._is_rate_supported(info['index'], self.sample_rate):
                            return info['index']
            
            # 3. Fallback for other microphones with rate negotiation
            for info in devices:
                name = info['name'].lower()
                if any(k in name for k in ["microphone", "input", "array"]):
                    if _is_unstable_handsfree(name):
                        continue
                    for rate in [16000, 44100, 48000, 8000]:
                        if self._is_rate_supported(info['index'], rate):
                            self.sample_rate = rate
                            self.logger.warning(f"Using alternate sample rate {rate}Hz for device {info['name']}")
                            return info['index']

            # 4. Try headset devices (but still avoid unstable hands-free profile)
            for info in devices:
                name = info['name'].lower()
                if "headset" in name and not _is_unstable_handsfree(name):
                    self.logger.info(f"Checking headset candidate: {info['name']}")
                    for rate in [self.sample_rate, 16000, 44100, 48000, 8000]:
                        if self._is_rate_supported(info['index'], rate):
                            if rate != self.sample_rate:
                                self.sample_rate = rate
                                self.logger.warning(f"Using fallback sample rate {rate}Hz for headset {info['name']}")
                            return info['index']

            # 5. Fallback to any non-handsfree hardware device that supports our rate
            for info in devices:
                name = info['name'].lower()
                if _is_unstable_handsfree(name):
                    continue
                if self._is_rate_supported(info['index'], self.sample_rate):
                    return info['index']
            
            # 6. Absolute fallback: find a rate that works for first non-handsfree device
            if devices:
                for info in devices:
                    if _is_unstable_handsfree(info['name'].lower()):
                        continue
                    for rate in [16000, 44100, 48000, 8000]:
                        if self._is_rate_supported(info['index'], rate):
                            self.sample_rate = rate
                            self.logger.warning(f"Using fallback sample rate: {rate}Hz")
                            return info['index']
                        
        except Exception as e:
            self.logger.log_error("DeviceDetectionError", str(e))
        
        return None

    def _is_rate_supported(self, device_index: int, rate: int) -> bool:
        """Check if a sample rate is supported by a device."""
        try:
            return self.audio.is_format_supported(
                rate,
                input_device=device_index,
                input_channels=self.channels,
                input_format=self.format
            )
        except:
            return False
    
    def list_audio_devices(self) -> None:
        """List all available audio devices."""
        if not self.audio:
            self.audio = pyaudio.PyAudio()
        
        self.logger.info("Available audio devices:")
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    self.logger.info(f"  [{i}] {device_info['name']} - {device_info['maxInputChannels']} channels")
            except:
                continue
    
    def start_stream(self, audio_callback: Callable) -> bool:
        """
        Start audio streaming with callback.
        
        Args:
            audio_callback: Callback function for audio data
            
        Returns:
            True if stream started successfully, False otherwise
        """
        if not self.audio:
            if not self.initialize_audio():
                return False
        
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=audio_callback
            )
            
            self.stream.start_stream()
            self.is_streaming = True
            self.retry_count = 0
            
            self.logger.log_audio_event("Audio stream started", f"Device: {self.device_index}")
            return True
            
        except Exception as e:
            self.logger.log_error("StreamStartError", str(e))
            return self._retry_stream_start(audio_callback)
    
    def _retry_stream_start(self, audio_callback: Callable) -> bool:
        """
        Retry starting audio stream with error recovery.
        
        Args:
            audio_callback: Callback function for audio data
            
        Returns:
            True if successful, False otherwise
        """
        while self.retry_count < self.max_retries:
            self.retry_count += 1
            self.logger.log_audio_event("Retrying stream start", f"Attempt {self.retry_count}/{self.max_retries}")
            
            # Wait before retry
            time.sleep(1.0)
            
            # Try to reinitialize audio
            self.cleanup()
            if self.initialize_audio():
                try:
                    self.stream = self.audio.open(
                        format=self.format,
                        channels=self.channels,
                        rate=self.sample_rate,
                        input=True,
                        input_device_index=self.device_index,
                        frames_per_buffer=self.chunk_size,
                        stream_callback=audio_callback
                    )
                    
                    self.stream.start_stream()
                    self.is_streaming = True
                    
                    self.logger.log_audio_event("Stream start successful on retry", f"Attempt {self.retry_count}")
                    return True
                    
                except Exception as e:
                    self.logger.log_error("RetryStreamError", str(e), f"Attempt {self.retry_count}")
                    continue
        
        self.logger.log_error("StreamStartFailed", f"Failed after {self.max_retries} attempts")
        return False
    
    def stop_stream(self) -> None:
        """Stop audio streaming."""
        if self.stream and self.is_streaming:
            try:
                self.stream.stop_stream()
                self.is_streaming = False
                self.logger.log_audio_event("Audio stream stopped")
            except Exception as e:
                self.logger.log_error("StreamStopError", str(e))
    
    def read_chunk(self) -> Optional[np.ndarray]:
        """
        Read a single chunk of audio data.
        
        Returns:
            Audio data as numpy array or None if error
        """
        if not self.stream or not self.is_streaming:
            return None
        
        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            return audio_data
        except Exception as e:
            self.logger.log_error("AudioReadError", str(e))
            return None
    
    def calculate_rms(self, audio_data: np.ndarray) -> float:
        """
        Calculate RMS energy of audio data.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            RMS energy value
        """
        if len(audio_data) == 0:
            return 0.0
        
        return np.sqrt(np.mean(audio_data.astype(float)**2))
    
    def is_silence(self, audio_data: np.ndarray) -> bool:
        """
        Check if audio data represents silence.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            True if silence, False otherwise
        """
        rms = self.calculate_rms(audio_data)
        return rms < self.silence_threshold
    
    def get_audio_level(self, audio_data: np.ndarray) -> float:
        """
        Get normalized audio level (0-1).
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Normalized audio level
        """
        rms = self.calculate_rms(audio_data)
        max_possible = np.iinfo(np.int16).max
        return min(rms / max_possible, 1.0)
    
    def cleanup(self, log_event: bool = True) -> None:
        """Clean up audio resources."""
        try:
            if self.stream:
                if self.is_streaming:
                    self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                self.is_streaming = False
            
            if self.audio:
                self.audio.terminate()
                self.audio = None
                
            if log_event:
                self.logger.log_audio_event("Audio resources cleaned up")
            
        except Exception as e:
            if log_event:
                self.logger.log_error("AudioCleanupError", str(e))
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            # Avoid logger usage during interpreter teardown.
            self.cleanup(log_event=False)
        except Exception:
            pass
