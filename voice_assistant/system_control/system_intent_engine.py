"""
System control intent engine for parsing voice commands.
Uses fuzzy matching to detect system control intent and extract actions.
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


class SystemIntentEngine:
    """
    Parses system control commands from recognized text.
    Supports fuzzy matching and action extraction.
    """
    
    def __init__(self, commands_config: Dict[str, Any], noise_words: list):
        """
        Initialize system intent engine.
        
        Args:
            commands_config: Commands configuration dictionary
            noise_words: List of noise words to filter out
        """
        self.commands_config = commands_config
        self.noise_words = [word.lower() for word in noise_words]
        self.logger = get_logger()
        
        # Extract system control commands
        self.system_config = commands_config.get("system_control", {})
        self.actions = self.system_config
        
        # Precompile regex patterns for better performance
        self._compile_patterns()
        
        self.logger.info("SystemIntentEngine initialized")
        self.logger.info(f"Loaded {len(self.actions)} system actions")
    
    def _compile_patterns(self) -> None:
        """Precompile regex patterns for all actions."""
        self.compiled_patterns = {}
        
        # Handle system_control structure which is different from other modules
        for action_name, patterns in self.actions.items():
            if isinstance(patterns, list):
                # system_control has direct list of patterns
                compiled = []
                for pattern in patterns:
                    # Convert pattern to regex
                    regex_pattern = self._pattern_to_regex(pattern)
                    try:
                        compiled.append(re.compile(regex_pattern, re.IGNORECASE))
                    except re.error as e:
                        self.logger.log_error("PatternCompilationError", str(e), f"Pattern: {pattern}")
                
                self.compiled_patterns[action_name] = compiled
    
    def _pattern_to_regex(self, pattern: str) -> str:
        """
        Convert command pattern to regex.
        
        Args:
            pattern: Command pattern
            
        Returns:
            Regex pattern string
        """
        # Escape special regex characters
        pattern = re.escape(pattern)
        
        # Allow for word boundaries and flexible spacing
        pattern = r'\b' + pattern + r'\b'
        
        # Replace escaped spaces with flexible whitespace
        pattern = pattern.replace(r'\ ', r'\s+')
        
        return pattern
    
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
        
        # For system commands, be more conservative with noise filtering
        # Only remove obvious filler words, keep system keywords
        conservative_noise = ["please", "can you", "would you", "could you", "assistant", "now", "quickly"]
        words = text.split()
        filtered_words = [word for word in words if word not in conservative_noise]
        text = ' '.join(filtered_words)
        
        return text.strip()
    
    def _match_action_patterns(self, text: str) -> Optional[str]:
        """
        Match text against action patterns.
        
        Args:
            text: Preprocessed text
            
        Returns:
            Matched action name or None if not found
        """
        # Prioritize actual actions over keywords
        priority_actions = ["shutdown", "restart", "sleep", "lock"]
        
        # Check priority actions first
        for action_name in priority_actions:
            if action_name in self.actions:
                patterns = self.actions[action_name]
                for pattern in patterns:
                    if pattern.lower() in text.lower():
                        return action_name
        
        # Check keywords last (only if no action matched)
        if "keywords" in self.actions:
            patterns = self.actions["keywords"]
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    return "keywords"
        
        return None
    
    def _fuzzy_match_actions(self, text: str) -> Tuple[Optional[str], float]:
        """
        Fuzzy match text against action patterns.
        
        Args:
            text: Preprocessed text
            
        Returns:
            Tuple of (best_action, confidence_score)
        """
        best_action = None
        best_score = 0.0
        
        for action_name, patterns in self.actions.items():
            for pattern in patterns:
                # Calculate fuzzy match score
                score = fuzz.ratio(text, pattern.lower()) / 100.0
                
                if score > best_score:
                    best_score = score
                    best_action = action_name
        
        return best_action, best_score
    
    def _detect_system_intent(self, text: str) -> bool:
        """
        Detect if text contains system control intent.
        
        Args:
            text: Preprocessed text
            
        Returns:
            True if system intent detected, False otherwise
        """
        text_lower = text.lower()
        
        # Check for system keywords
        system_keywords = ["system", "computer", "pc", "shutdown", "restart", "sleep", "lock"]
        
        for keyword in system_keywords:
            if keyword in text_lower:
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
                "intent": "system_control",
                "action": None,
                "confidence": 0.0
            }
        
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Check for system intent
        if not self._detect_system_intent(processed_text):
            self.logger.log_intent_detected("system_control", None, None, 0.0)
            return {
                "intent": "system_control",
                "action": None,
                "confidence": 0.0
            }
        
        # Try exact pattern matching first
        action = self._match_action_patterns(processed_text)
        
        if action:
            self.logger.log_intent_detected("system_control", action, None, 1.0)
            
            return {
                "intent": "system_control",
                "action": action,
                "confidence": 1.0
            }
        
        # Try fuzzy matching as fallback
        best_action, confidence = self._fuzzy_match_actions(processed_text)
        
        if best_action and confidence >= 0.7:  # High threshold for system commands
            self.logger.log_intent_detected("system_control", best_action, None, confidence)
            
            return {
                "intent": "system_control",
                "action": best_action,
                "confidence": confidence
            }
        
        # No intent detected
        self.logger.log_intent_detected("system_control", None, None, 0.0)
        
        return {
            "intent": "system_control",
            "action": None,
            "confidence": 0.0
        }
    
    def get_action_description(self, action: str) -> str:
        """
        Get description for an action.
        
        Args:
            action: Action name
            
        Returns:
            Action description
        """
        descriptions = {
            "shutdown": "Shutdown the computer",
            "restart": "Restart the computer",
            "sleep": "Put the computer to sleep",
            "lock": "Lock the screen"
        }
        
        return descriptions.get(action, f"System {action}")
    
    def get_action_safety_level(self, action: str) -> str:
        """
        Get safety level for an action.
        
        Args:
            action: Action name
            
        Returns:
            Safety level: "high", "medium", or "low"
        """
        safety_levels = {
            "shutdown": "high",
            "restart": "high", 
            "sleep": "medium",
            "lock": "low"
        }
        
        return safety_levels.get(action, "medium")
    
    def requires_confirmation(self, action: str) -> bool:
        """
        Check if action requires confirmation.
        
        Args:
            action: Action name
            
        Returns:
            True if confirmation required, False otherwise
        """
        confirmation_required = {
            "shutdown": True,
            "restart": True,
            "sleep": True,
            "lock": False
        }
        
        return confirmation_required.get(action, True)
    
    def list_supported_actions(self) -> Dict[str, str]:
        """
        Get list of supported actions with descriptions.
        
        Returns:
            Dictionary of action_name -> description
        """
        return {
            action: self.get_action_description(action)
            for action in self.actions.keys()
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
            "action_description": self.get_action_description(result["action"]) if result["action"] else None,
            "safety_level": self.get_action_safety_level(result["action"]) if result["action"] else None,
            "requires_confirmation": self.requires_confirmation(result["action"]) if result["action"] else False
        })
        
        return result
