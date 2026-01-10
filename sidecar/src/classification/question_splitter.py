"""
Question Splitter for detecting and splitting compound questions.

Ensures all parts of multi-part interview questions are addressed by
splitting them into individual answerable units.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)


# Patterns that indicate a compound question
COMPOUND_INDICATORS = [
    r"\band\b\s+(what|how|why|when|where|tell|describe|explain)",
    r"\?\s*\S+.*\?",  # Multiple question marks with content between
    r"(first|second|also|additionally)\s+(what|how|tell)",
    r"(one|another|other)\s+(thing|question)",
    r",\s*(and|also)\s+(what|how|can|could)",
    r"\badditionally\s*,?\s*(what|how|tell|describe)",  # "additionally, what about"
]

# Conjunctions that can precede new question parts
SPLIT_CONJUNCTIONS = ["and", "also", "additionally", "plus"]

# Question starters
QUESTION_WORDS = [
    "what", "how", "why", "when", "where", "who", "which",
    "can", "could", "would", "will", "should",
    "tell", "describe", "explain", "give",
]


class QuestionSplitter:
    """
    Splits compound questions into individual answerable questions.
    
    Handles patterns like:
    - "What is X and how do you Y?" -> ["What is X?", "How do you Y?"]
    - "Tell me A? Also, tell me B?" -> ["Tell me A?", "Tell me B?"]
    """
    
    def split_questions(self, text: str) -> List[str]:
        """
        Split compound questions into individual questions.
        
        Args:
            text: The potentially compound question.
            
        Returns:
            List of individual questions. Single-item list if not compound.
            Empty list if input is empty/whitespace.
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        # Check if compound
        if not self._is_compound(text):
            return [text]
        
        # Try splitting by multiple question marks first
        if self._has_multiple_questions(text):
            questions = self._split_by_question_marks(text)
            if len(questions) > 1:
                return [self._ensure_question_form(q) for q in questions if q.strip()]
        
        # Try splitting by conjunctions + question words
        questions = self._split_by_conjunctions(text)
        
        # Normalize each question
        normalized = [self._ensure_question_form(q) for q in questions if q.strip()]
        
        return normalized if normalized else [text]
    
    def _is_compound(self, text: str) -> bool:
        """
        Detect if text contains multiple questions.
        
        Args:
            text: The question text.
            
        Returns:
            True if compound question detected.
        """
        for pattern in COMPOUND_INDICATORS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _has_multiple_questions(self, text: str) -> bool:
        """
        Check if text has multiple question marks.
        
        Args:
            text: The question text.
            
        Returns:
            True if multiple question marks present.
        """
        return text.count('?') > 1
    
    def _split_by_question_marks(self, text: str) -> List[str]:
        """
        Split text by question marks.
        
        Args:
            text: The question text.
            
        Returns:
            List of question segments.
        """
        # Split by ? and keep the ?
        parts = re.split(r'(\?)', text)
        
        questions = []
        current = ""
        
        for part in parts:
            if part == '?':
                current += '?'
                if current.strip():
                    questions.append(current.strip())
                current = ""
            else:
                current += part
        
        # Don't forget trailing text
        if current.strip():
            questions.append(current.strip())
        
        return questions
    
    def _split_by_conjunctions(self, text: str) -> List[str]:
        """
        Split on conjunctions that precede question words.
        
        Args:
            text: The question text.
            
        Returns:
            List of question segments.
        """
        # Build pattern: conjunction followed by question word
        conj_pattern = "|".join(SPLIT_CONJUNCTIONS)
        qword_pattern = "|".join(QUESTION_WORDS)
        
        # Pattern: (conjunction) with optional commas, followed by (question word)
        # Use lookahead to keep the question word
        pattern = rf"\s*,?\s*\b({conj_pattern})\s*,?\s*(?=({qword_pattern})\b)"
        
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        
        # Filter out the conjunctions and empty parts
        questions = []
        for part in parts:
            if part is None:
                continue
            part = part.strip()
            if not part:
                continue
            # Skip standalone conjunctions
            if part.lower() in SPLIT_CONJUNCTIONS:
                continue
            # Skip single question words that got separated
            if part.lower() in QUESTION_WORDS:
                continue
            questions.append(part)
        
        return questions if questions else [text]
    
    def _ensure_question_form(self, text: str) -> str:
        """
        Ensure text is a proper question.
        
        Args:
            text: Raw question text.
            
        Returns:
            Normalized question string.
        """
        if not text:
            return ""
        
        text = text.strip()
        
        # Remove leading conjunctions
        conj_pattern = "|".join(SPLIT_CONJUNCTIONS)
        text = re.sub(rf"^({conj_pattern})[,\s]+", "", text, flags=re.IGNORECASE)
        
        # Remove leading punctuation
        text = re.sub(r"^[,.\s]+", "", text)
        
        text = text.strip()
        if not text:
            return ""
        
        # Capitalize first letter
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        
        # Add question mark if it looks like a question and doesn't have one
        if not text.endswith('?') and self._looks_like_question(text):
            text += '?'
        
        return text
    
    def _looks_like_question(self, text: str) -> bool:
        """
        Check if text appears to be a question.
        
        Args:
            text: The text to check.
            
        Returns:
            True if it looks like a question.
        """
        text_lower = text.lower().strip()
        
        # Check for question words at start
        for word in QUESTION_WORDS:
            if text_lower.startswith(word + " ") or text_lower.startswith(word + "'"):
                return True
        
        return False
