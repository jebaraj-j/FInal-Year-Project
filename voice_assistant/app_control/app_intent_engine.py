"""
App launch intent engine for parsing voice commands.
Uses fuzzy matching to detect application launch intent and extract app names.
"""

import re
import json
from typing import Dict, Any, Optional, Tuple
try:
    from ..utils.fuzzy_compat import fuzz
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.fuzzy_compat import fuzz
try:
    from ..utils.logger import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger


class AppIntentEngine:
    """
    Parses application launch commands from recognized text.
    Supports fuzzy matching and app name extraction.
    """
    
    def __init__(self, commands_config: Dict[str, Any], noise_words: list, available_apps: Dict[str, str]):
        """
        Initialize app intent engine.
        
        Args:
            commands_config: Commands configuration dictionary
            noise_words: List of noise words to filter out
            available_apps: Dictionary of available applications
        """
        self.commands_config = commands_config
        self.noise_words = [word.lower() for word in noise_words]
        self.available_apps = {app.lower(): path for app, path in available_apps.items()}
        self.logger = get_logger()
        
        # Extract app launcher commands
        self.app_config = commands_config.get("app_launcher", {})
        self.open_commands = self.app_config.get("open", [])
        
        # Precompile regex patterns for better performance
        self._compile_patterns()
        
        # Create app name variations for fuzzy matching
        self._create_app_variations()
        
        self.logger.info("AppIntentEngine initialized")
        self.logger.info(f"Loaded {len(self.open_commands)} open commands")
        self.logger.info(f"Available apps: {list(self.available_apps.keys())}")
    
    def _compile_patterns(self) -> None:
        """Precompile regex patterns for open commands."""
        self.compiled_patterns = []
        
        for command in self.open_commands:
            # Create regex pattern for open command + app name
            pattern = re.compile(
                rf'\b{re.escape(command)}\s+(.+?)\b',
                re.IGNORECASE
            )
            self.compiled_patterns.append(pattern)
    
    def _create_app_variations(self) -> None:
        """Create variations of app names for fuzzy matching."""
        self.app_variations = {}
        
        for app_name in self.available_apps.keys():
            variations = set()
            
            # Add original name
            variations.add(app_name)
            
            # Add common variations
            if app_name == "chrome":
                variations.update(["google chrome", "browser", "web browser"])
            elif app_name == "code":
                variations.update(["vs code", "visual studio code", "vscode", "editor"])
            elif app_name == "notepad":
                variations.update(["notepad", "text editor", "editor"])
            elif app_name == "settings":
                variations.update(["windows settings", "system settings", "settings"])
            elif app_name == "explorer":
                variations.update(["file explorer", "windows explorer", "explorer", "files"])
            
            self.app_variations[app_name] = variations
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for intent recognition.
        
        Args:
            text: Input text
            
        Returns:
            Preprocessed text
        """
        # Convert to lowercase and remove extra whitespace
        text = ' '.join(text.lower().split())
        
        # Remove noise words
        words = text.split()
        filtered_words = [word for word in words if word not in self.noise_words]
        text = ' '.join(filtered_words)
        
        return text.strip()
    
    def _extract_app_name_from_pattern(self, text: str) -> Optional[str]:
        """
        Extract app name using regex patterns.
        
        Args:
            text: Preprocessed text
            
        Returns:
            Extracted app name or None if not found
        """
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                app_name = match.group(1).strip()
                return app_name
        
        return None
    
    def _match_app_name_fuzzy(self, app_text: str) -> Tuple[Optional[str], float]:
        """
        Match app name using fuzzy matching.
        
        Args:
            app_text: Text containing app name
            
        Returns:
            Tuple of (matched_app, confidence_score)
        """
        best_match = None
        best_score = 0.0
        
        app_text_lower = app_text.lower().strip()
        
        # Direct matching first
        if app_text_lower in self.available_apps:
            return app_text_lower, 1.0
        
        # Check variations
        for app_name, variations in self.app_variations.items():
            for variation in variations:
                score = fuzz.ratio(app_text_lower, variation) / 100.0
                
                if score > best_score and score >= 0.7:  # Fuzzy threshold
                    best_score = score
                    best_match = app_name
        
        return best_match, best_score
    
    def _detect_open_intent(self, text: str) -> bool:
        """
        Detect if text contains open intent.
        
        Args:
            text: Preprocessed text
            
        Returns:
            True if open intent detected, False otherwise
        """
        text_lower = text.lower()
        
        # Check for open commands
        for command in self.open_commands:
            if command in text_lower:
                return True
        
        # Fuzzy matching for open commands
        for command in self.open_commands:
            score = fuzz.ratio(text_lower, command) / 100.0
            if score >= 0.8:  # High threshold for open commands
                return True
        
        return False
    
    def parse_intent(self, text: str) -> Dict[str, Any]:
        """
        Parse intent from recognized text.
        
        Args:
            text: Recognized speech text
            
        Returns:
            Intent result dictionary
        """
        if not text or not text.strip():
            return {
                "intent": "app_launch",
                "app": None,
                "confidence": 0.0
            }
        
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Check for open intent
        if not self._detect_open_intent(processed_text):
            self.logger.log_intent_detected("app_launch", None, None, 0.0)
            return {
                "intent": "app_launch",
                "app": None,
                "confidence": 0.0
            }
        
        # Try to extract app name using patterns
        app_name = self._extract_app_name_from_pattern(processed_text)
        
        if app_name:
            # Match app name using fuzzy matching
            matched_app, confidence = self._match_app_name_fuzzy(app_name)
            
            if matched_app and confidence >= 0.7:
                self.logger.log_intent_detected("app_launch", matched_app, None, confidence)
                return {
                    "intent": "app_launch",
                    "app": matched_app,
                    "confidence": confidence
                }
        
        # Try fuzzy matching on entire text
        matched_app, confidence = self._match_app_name_fuzzy(processed_text)
        
        if matched_app and confidence >= 0.6:  # Lower threshold for full text
            self.logger.log_intent_detected("app_launch", matched_app, None, confidence)
            return {
                "intent": "app_launch",
                "app": matched_app,
                "confidence": confidence
            }
        
        # No app detected
        self.logger.log_intent_detected("app_launch", None, None, 0.0)
        
        return {
            "intent": "app_launch",
            "app": None,
            "confidence": 0.0
        }
    
    def get_app_description(self, app_name: str) -> str:
        """
        Get description for an application.
        
        Args:
            app_name: Application name
            
        Returns:
            Application description
        """
        app_path = self.available_apps.get(app_name.lower())
        
        if not app_path:
            return "Unknown application"
        
        # Create human-readable description
        if app_name == "chrome":
            return "Google Chrome web browser"
        elif app_name == "code":
            return "Visual Studio Code editor"
        elif app_name == "notepad":
            return "Windows Notepad text editor"
        elif app_name == "settings":
            return "Windows Settings"
        elif app_name == "explorer":
            return "File Explorer"
        else:
            return f"Application: {app_name}"
    
    def list_supported_apps(self) -> Dict[str, str]:
        """
        Get list of supported applications with descriptions.
        
        Returns:
            Dictionary of app_name -> description
        """
        return {
            app: self.get_app_description(app)
            for app in self.available_apps.keys()
        }
    
    def test_intent_parsing(self, test_text: str) -> Dict[str, Any]:
        """
        Test intent parsing with sample text.
        
        Args:
            test_text: Text to test
            
        Returns:
            Parsing result with additional debug info
        """
        result = self.parse_intent(test_text)
        
        # Add debug information
        result.update({
            "original_text": test_text,
            "processed_text": self._preprocess_text(test_text),
            "app_description": self.get_app_description(result["app"]) if result["app"] else None,
            "open_intent_detected": self._detect_open_intent(self._preprocess_text(test_text))
        })
        
        return result
