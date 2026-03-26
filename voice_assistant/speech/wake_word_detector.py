"""
Wake word detector using fuzzy string matching.
Detects wake words with configurable sensitivity threshold.
"""

import re
from typing import List, Optional, Tuple
from fuzzywuzzy import fuzz
try:
    from ..utils.logger import get_logger
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger


class WakeWordDetector:
    """Detects wake words using fuzzy matching with configurable threshold."""
    
    def __init__(self, wake_words: List[str], threshold: float = 0.75):
        """
        Initialize wake word detector.
        
        Args:
            wake_words: List of wake word phrases
            threshold: Fuzzy matching threshold (0.0-1.0)
        """
        self.wake_words = [word.lower().strip() for word in wake_words]
        self.threshold = threshold
        self.logger = get_logger()
        
        # Preprocess wake words for better matching
        self.processed_wake_words = []
        for word in self.wake_words:
            processed = self._preprocess_text(word)
            self.processed_wake_words.append(processed)
        
        self.logger.info(f"WakeWordDetector initialized with {len(wake_words)} wake words")
        self.logger.info(f"Wake words: {self.wake_words}")
        self.logger.info(f"Detection threshold: {threshold}")
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for better matching.
        
        Args:
            text: Input text
            
        Returns:
            Preprocessed text
        """
        # Remove extra whitespace and convert to lowercase
        text = ' '.join(text.lower().split())
        
        # Remove common filler words that don't affect wake word detection
        filler_words = ['um', 'uh', 'er', 'ah']
        for filler in filler_words:
            text = text.replace(filler, '')
        
        return text.strip()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity ratio (0.0-1.0)
        """
        return fuzz.ratio(text1, text2) / 100.0
    
    def _find_best_match(self, text: str) -> Tuple[Optional[str], float]:
        """
        Find best matching wake word for given text.
        
        Args:
            text: Input text to check
            
        Returns:
            Tuple of (best_wake_word, similarity_score) or (None, 0.0)
        """
        processed_text = self._preprocess_text(text)
        best_match = None
        best_score = 0.0
        
        for wake_word in self.processed_wake_words:
            score = self._calculate_similarity(processed_text, wake_word)
            if score > best_score:
                best_score = score
                best_match = wake_word
        
        return best_match, best_score
    
    def _contains_wake_word_parts(self, text: str) -> Tuple[bool, float]:
        """
        Check if text contains wake word parts (partial matching).
        
        Args:
            text: Input text to check
            
        Returns:
            Tuple of (contains_parts, max_score)
        """
        processed_text = self._preprocess_text(text)
        words = processed_text.split()
        max_score = 0.0
        
        for wake_word in self.processed_wake_words:
            wake_word_parts = wake_word.split()
            
            # Check if wake word parts are present in text
            matches = 0
            for part in wake_word_parts:
                if part in words:
                    matches += 1
            
            # Calculate partial match score
            if matches > 0:
                partial_score = matches / len(wake_word_parts)
                max_score = max(max_score, partial_score)
        
        return max_score > 0.3, max_score
    
    def detect_wake_word(self, text: str) -> Tuple[bool, Optional[str], float]:
        """
        Detect if wake word is present in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Tuple of (is_detected, wake_word, confidence_score)
        """
        if not text or not text.strip():
            return False, None, 0.0
        
        # Try exact fuzzy matching first
        best_match, score = self._find_best_match(text)
        
        if score >= self.threshold:
            self.logger.log_wake_word_detected(best_match)
            return True, best_match, score
        
        # Try partial matching as fallback
        contains_parts, partial_score = self._contains_wake_word_parts(text)
        
        if contains_parts and partial_score >= (self.threshold * 0.8):
            # Find which wake word parts matched
            best_match, score = self._find_best_match(text)
            self.logger.log_wake_word_detected(best_match)
            return True, best_match, partial_score
        
        return False, None, score
    
    def add_wake_word(self, wake_word: str) -> None:
        """
        Add a new wake word to the detector.
        
        Args:
            wake_word: New wake word phrase
        """
        processed = self._preprocess_text(wake_word)
        self.wake_words.append(wake_word.lower().strip())
        self.processed_wake_words.append(processed)
        
        self.logger.info(f"Added wake word: '{wake_word}'")
    
    def remove_wake_word(self, wake_word: str) -> bool:
        """
        Remove a wake word from the detector.
        
        Args:
            wake_word: Wake word phrase to remove
            
        Returns:
            True if removed, False if not found
        """
        wake_word_lower = wake_word.lower().strip()
        
        if wake_word_lower in self.wake_words:
            index = self.wake_words.index(wake_word_lower)
            self.wake_words.pop(index)
            self.processed_wake_words.pop(index)
            
            self.logger.info(f"Removed wake word: '{wake_word}'")
            return True
        
        return False
    
    def set_threshold(self, threshold: float) -> None:
        """
        Set detection threshold.
        
        Args:
            threshold: New threshold (0.0-1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
            self.logger.info(f"Wake word threshold set to: {threshold}")
        else:
            self.logger.log_error("InvalidThreshold", f"Threshold must be between 0.0 and 1.0, got {threshold}")
    
    def get_wake_words(self) -> List[str]:
        """
        Get list of configured wake words.
        
        Returns:
            List of wake words
        """
        return self.wake_words.copy()
    
    def test_detection(self, test_text: str) -> dict:
        """
        Test wake word detection with sample text.
        
        Args:
            test_text: Text to test
            
        Returns:
            Detection result dictionary
        """
        is_detected, wake_word, confidence = self.detect_wake_word(test_text)
        
        return {
            "text": test_text,
            "detected": is_detected,
            "wake_word": wake_word,
            "confidence": confidence,
            "threshold": self.threshold
        }
