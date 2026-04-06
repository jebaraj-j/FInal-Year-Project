"""
Unified Intent Engine for all voice commands.
Handles brightness, volume, app launcher, and system control commands.
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
    from ..utils.num_converter import words_to_number
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger
    from utils.num_converter import words_to_number


class UnifiedIntentEngine:
    """
    Unified intent engine for all voice command types.
    Supports brightness, volume, app launcher, and system control.
    """
    
    def __init__(self, commands_config: Dict[str, Any], noise_words: list):
        """
        Initialize unified intent engine.
        
        Args:
            commands_config: Complete commands configuration dictionary
            noise_words: List of noise words to filter out
        """
        self.commands_config = commands_config
        self.noise_words = [word.lower() for word in noise_words]
        self.logger = get_logger()
        
        # Dynamically load all categories from config
        self.categories = {
            cat_name: cat_config for cat_name, cat_config in commands_config.items()
            if isinstance(cat_config, dict) and "actions" in cat_config
        }
        
        # Precompile patterns for all categories
        self._compile_all_patterns()
        
        total_actions = sum(len(cat.get("actions", {})) for cat in self.categories.values())
        self.logger.info("UnifiedIntentEngine initialized")
        self.logger.info(f"Loaded {total_actions} total actions across {len(self.categories)} categories")
    
    def _compile_all_patterns(self) -> None:
        """Precompile regex patterns for all categories and actions."""
        self.compiled_patterns = {}
        
        for category_name, category_config in self.categories.items():
            self.compiled_patterns[category_name] = {}
            actions = category_config.get("actions", {})
            
            for action_name, action_config in actions.items():
                patterns = action_config.get("patterns", [])
                compiled = []
                
                for pattern in patterns:
                    # Convert pattern to regex
                    regex_pattern = self._pattern_to_regex(pattern)
                    try:
                        compiled.append(re.compile(regex_pattern, re.IGNORECASE))
                    except re.error as e:
                        self.logger.log_error("PatternCompilationError", str(e), 
                                            f"Category: {category_name}, Action: {action_name}, Pattern: {pattern}")
                
                self.compiled_patterns[category_name][action_name] = compiled
    
    def _pattern_to_regex(self, pattern: str) -> str:
        """
        Convert command pattern to regex.
        
        Args:
            pattern: Command pattern with placeholders
            
        Returns:
            Regex pattern string
        """
        # Escape special regex characters except our placeholders
        pattern = re.escape(pattern)
        
        # Replace escaped placeholders back to regex groups
        # Matches digits or words like "fifty five"
        pattern = pattern.replace(r'\{value\}', r'(\d+|[a-z\s-]+)')
        
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
        
        # Remove noise words
        words = text.split()
        filtered_words = [word for word in words if word not in self.noise_words]
        text = ' '.join(filtered_words)
        
        return text.strip()
    
    def _extract_numeric_value(self, text: str) -> Optional[int]:
        """
        Extract numeric value from text.
        
        Args:
            text: Input text
            
        Returns:
            Extracted number or None if not found
        """
        # 1. Try to find digits first
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            return int(numbers[0])
            
        # 2. Try to extract from words using num_converter
        return words_to_number(text)
    
    def _match_category_patterns(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Match text against all category patterns.
        
        Args:
            text: Preprocessed text
            
        Returns:
            Tuple of (category, action, extracted_value) or (None, None, None)
        """
        for category_name, category_patterns in self.compiled_patterns.items():
            for action_name, patterns in category_patterns.items():
                for pattern in patterns:
                    match = pattern.fullmatch(text)
                    if match:
                        # Extract numeric value if present
                        if match.groups():
                            try:
                                value = words_to_number(match.group(1))
                                return category_name, action_name, value
                            except (ValueError, IndexError):
                                pass
                        
                        return category_name, action_name, None
        
        return None, None, None
    
    def _fuzzy_match_all(self, text: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Fuzzy match text against all patterns.
        
        Args:
            text: Preprocessed text
            
        Returns:
            Tuple of (best_category, best_action, confidence_score)
        """
        best_category = None
        best_action = None
        best_score = 0.0
        
        for category_name, category_config in self.categories.items():
            actions = category_config.get("actions", {})
            
            for action_name, action_config in actions.items():
                patterns = action_config.get("patterns", [])
                
                for pattern in patterns:
                    # Remove placeholders for fuzzy matching
                    clean_pattern = re.sub(r'\{.*?\}', '', pattern)
                    clean_pattern = clean_pattern.lower().strip()
                    
                    # Calculate fuzzy match score
                    score = fuzz.ratio(text, clean_pattern) / 100.0
                    
                    if score > best_score:
                        best_score = score
                        best_category = category_name
                        best_action = action_name
        
        return best_category, best_action, best_score
    
    def _validate_action_value(self, category: str, action: str, value: Optional[int]) -> Optional[int]:
        """
        Validate and clamp action value.
        
        Args:
            category: Category name
            action: Action name
            value: Extracted value
            
        Returns:
            Validated value or None
        """
        if value is None:
            return None
        
        action_config = self.categories.get(category, {}).get("actions", {}).get(action, {})
        
        # Check if action has value range
        value_range = action_config.get("value_range")
        if value_range and isinstance(value_range, list) and len(value_range) == 2:
            min_val, max_val = value_range
            return max(min_val, min(max_val, value))
        
        # Default range for most controls
        return max(0, min(100, value))
    
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
                "intent": None,
                "category": None,
                "action": None,
                "value": None,
                "confidence": 0.0
            }
        
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Try exact pattern matching first
        category, action, extracted_value = self._match_category_patterns(processed_text)
        
        if category and action:
            # Validate extracted value
            validated_value = self._validate_action_value(category, action, extracted_value)
            
            self.logger.log_intent_detected(category, action, validated_value, 1.0)
            
            return {
                "intent": category,
                "category": category,
                "action": action,
                "value": validated_value,
                "confidence": 1.0
            }
        
        # Try fuzzy matching as fallback
        best_category, best_action, confidence = self._fuzzy_match_all(processed_text)
        
        if best_category and best_action and confidence >= 0.4:  # Even lower threshold for better recognition
            # Try to extract numeric value
            numeric_value = self._extract_numeric_value(text)
            validated_value = self._validate_action_value(best_category, best_action, numeric_value)
            
            self.logger.log_intent_detected(best_category, best_action, validated_value, confidence)
            
            return {
                "intent": best_category,
                "category": best_category,
                "action": best_action,
                "value": validated_value,
                "confidence": confidence
            }
        
        # No intent detected
        self.logger.log_intent_detected("unknown", None, None, 0.0)
        
        return {
            "intent": None,
            "category": None,
            "action": None,
            "value": None,
            "confidence": 0.0
        }
    
    def get_action_description(self, category: str, action: str) -> str:
        """
        Get description for an action.
        
        Args:
            category: Category name
            action: Action name
            
        Returns:
            Action description
        """
        action_config = self.categories.get(category, {}).get("actions", {}).get(action, {})
        return action_config.get("description", "Unknown action")
    
    def list_supported_actions(self) -> Dict[str, Dict[str, str]]:
        """
        Get list of supported actions with descriptions.
        
        Returns:
            Dictionary of category -> {action: description}
        """
        result = {}
        for category_name, category_config in self.categories.items():
            actions = category_config.get("actions", {})
            result[category_name] = {
                action: config.get("description", "No description")
                for action, config in actions.items()
            }
        return result
    
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
            "action_description": self.get_action_description(result["category"], result["action"]) 
                                 if result["category"] and result["action"] else None
        })
        
        return result
