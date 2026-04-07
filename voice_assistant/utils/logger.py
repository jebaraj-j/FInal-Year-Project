"""
Centralized logging system for voice assistant.
Provides rotating file logging and console output with different log levels.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


class VoiceAssistantLogger:
    """Logger class for voice assistant with file rotation and console output."""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        """
        Initialize logger with file and console handlers.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_dir = Path(log_dir)
        
        # Ensure parent directories exist
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"WARNING: Could not create log directory {self.log_dir}: {e}")
        
        # Create logger
        self.logger = logging.getLogger("voice_assistant")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_file_handler()
            self._setup_console_handler()
    
    def _setup_file_handler(self):
        """Setup rotating file handler for persistent logging."""
        try:
            log_file = self.log_dir / "assistant.log"
            
            # Rotating file handler (10MB max, keep 5 backup files)
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file),  # Convert Path to string
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            # File format: timestamp, level, message
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"WARNING: Could not setup file handler: {e}")
            print(f"Log file path: {self.log_dir / 'assistant.log'}")
    
    def _setup_console_handler(self):
        """Setup console handler for real-time monitoring."""
        console_handler = logging.StreamHandler()
        
        # Console format: simpler, level-based coloring
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log critical message."""
        self.logger.critical(message)
    
    def log_system_start(self):
        """Log system startup."""
        self.info("=" * 50)
        self.info("VOICE ASSISTANT SYSTEM STARTING")
        self.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info("=" * 50)
    
    def log_system_shutdown(self):
        """Log system shutdown."""
        self.info("=" * 50)
        self.info("VOICE ASSISTANT SYSTEM SHUTTING DOWN")
        self.info(f"Shutdown time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info("=" * 50)
    
    def log_wake_word_detected(self, wake_word: str):
        """Log wake word detection."""
        self.info(f"WAKE WORD DETECTED: '{wake_word}'")
    
    def log_command_received(self, command_text: str):
        """Log received command."""
        self.info(f"COMMAND RECEIVED: '{command_text}'")
    
    def log_intent_detected(self, intent: str, action: str, value=None, confidence: float = 0.0):
        """Log intent detection result."""
        value_str = f", value: {value}" if value is not None else ""
        self.info(f"INTENT DETECTED: {intent}, action: {action}, confidence: {confidence:.2f}{value_str}")
    
    def log_brightness_change(self, old_value: int, new_value: int, action: str):
        """Log brightness change."""
        self.info(f"BRIGHTNESS CHANGE: {old_value}% → {new_value}% (action: {action})")
    
    def log_volume_change(self, old_value: int, new_value: int, action: str):
        """Log volume change."""
        self.info(f"VOLUME CHANGE: {old_value}% → {new_value}% (action: {action})")
    
    def log_app_launch(self, app_name: str, app_path: str):
        """Log application launch."""
        self.info(f"APP LAUNCH: {app_name} (path: {app_path})")
    
    def log_system_action_attempt(self, action: str):
        """Log system action attempt."""
        self.info(f"SYSTEM ACTION ATTEMPT: {action}")
    
    def log_system_action_success(self, action: str):
        """Log successful system action."""
        self.info(f"SYSTEM ACTION SUCCESS: {action}")
    
    def log_system_action_failure(self, action: str, reason: str):
        """Log failed system action."""
        self.error(f"SYSTEM ACTION FAILURE: {action} - {reason}")
    
    def log_system_confirmation(self, action: str, result: str):
        """Log system action confirmation result."""
        self.info(f"SYSTEM CONFIRMATION: {action} - {result}")
    
    def log_error(self, error_type: str, error_message: str, context: str = ""):
        """Log error with context."""
        context_str = f" | Context: {context}" if context else ""
        self.error(f"{error_type}: {error_message}{context_str}")
    
    def log_audio_event(self, event_type: str, details: str = ""):
        """Log audio-related events."""
        details_str = f" | {details}" if details else ""
        self.info(f"AUDIO EVENT: {event_type}{details_str}")


# Global logger instance
_logger_instance = None


def get_logger(log_dir: str = "logs", log_level: str = "INFO") -> VoiceAssistantLogger:
    """
    Get singleton logger instance.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        
    Returns:
        VoiceAssistantLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = VoiceAssistantLogger(log_dir, log_level)
    return _logger_instance


def setup_logger(log_dir: str = "logs", log_level: str = "INFO") -> VoiceAssistantLogger:
    """
    Setup and return logger instance.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        
    Returns:
        VoiceAssistantLogger instance
    """
    return VoiceAssistantLogger(log_dir, log_level)
