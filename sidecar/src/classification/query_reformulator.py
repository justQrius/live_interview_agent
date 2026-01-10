"""
Query Reformulator for expanding follow-up questions into standalone queries.

Uses conversation history to resolve pronouns and references, making
follow-up questions self-contained for better RAG retrieval.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Patterns that indicate a follow-up question
FOLLOW_UP_INDICATORS = [
    r"^(what about|how about)\s+",
    r"^(and|also)\s+(what|how|why|when|where)",
    r"^(can you|could you)\s+(elaborate|expand|explain more|tell me more)",
    r"^(tell me more|go on|continue)",
    r"^(what were|what are)\s+the\s+(results?|outcomes?)\??$",
    r"\b(that|this|it)\s*\??$",  # Ends with pronoun + optional ?
]

# Templates for expanding follow-ups
EXPANSION_TEMPLATES = {
    r"^what about\s+(.+?)\??$": 
        "What is your experience with {match} in relation to {prev_topic}?",
    r"^how about\s+(.+?)\??$": 
        "How do you handle {match} based on your experience with {prev_topic}?",
    r"^can you elaborate\??$": 
        "Can you elaborate on {prev_topic}?",
    r"^could you elaborate\??$": 
        "Could you elaborate on {prev_topic}?",
    r"^can you expand( on that)?\??$": 
        "Can you expand on {prev_topic}?",
    r"^could you expand( on that)?\??$": 
        "Could you expand on {prev_topic}?",
    r"^can you explain more\??$": 
        "Can you explain more about {prev_topic}?",
    r"^could you explain more\??$": 
        "Could you explain more about {prev_topic}?",
    r"^tell me more\??$": 
        "Tell me more about {prev_topic}.",
    r"^go on\??$": 
        "Please continue explaining {prev_topic}.",
    r"^continue\??$": 
        "Please continue explaining {prev_topic}.",
    r"^(what were|what are) the results?\??$": 
        "What were the results of {prev_topic}?",
    r"^(what were|what are) the outcomes?\??$": 
        "What were the outcomes of {prev_topic}?",
    r"^and (what|how|why)\s+(.+)$":
        "{match2} regarding {prev_topic}?",
    r"^also,?\s+(what|how|why)\s+(.+)$":
        "{match2} regarding {prev_topic}?",
}


class QueryReformulator:
    """
    Expands follow-up questions into standalone queries.
    
    Uses conversation history to resolve references and pronouns,
    creating self-contained questions that can be used for RAG retrieval.
    """
    
    def __init__(self, context_turns: int = 5):
        """
        Initialize the QueryReformulator.
        
        Args:
            context_turns: Number of previous turns to consider for context.
        """
        self.context_turns = context_turns
    
    def reformulate_if_needed(
        self,
        current_question: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> Tuple[str, bool]:
        """
        Expand follow-up questions into standalone questions.
        
        Args:
            current_question: The question to potentially reformulate.
            conversation_history: List of previous exchanges, each with
                'question' and 'answer' keys.
                
        Returns:
            Tuple of (reformulated_question, was_reformulated)
        """
        # Handle edge cases
        if not current_question:
            return current_question, False
        
        current_question = current_question.strip()
        if not current_question:
            return current_question, False
        
        # Normalize history
        history = conversation_history or []
        
        # Check if it's a follow-up
        if not self._is_follow_up(current_question):
            return current_question, False
        
        # Need history to reformulate
        if not history:
            return current_question, False
        
        # Get the most recent valid exchange
        last_exchange = self._get_last_valid_exchange(history)
        if not last_exchange:
            return current_question, False
        
        # Extract topic from previous exchange
        prev_topic = self._extract_topic(last_exchange)
        
        # Try to expand using templates
        expanded = self._expand_with_template(current_question, prev_topic)
        
        if expanded and expanded != current_question:
            logger.info(f"Reformulated '{current_question}' → '{expanded}'")
            return expanded, True
        
        return current_question, False
    
    def _is_follow_up(self, text: str) -> bool:
        """
        Check if text is a follow-up question.
        
        Args:
            text: The question text.
            
        Returns:
            True if it matches follow-up patterns.
        """
        text_lower = text.lower().strip()
        
        for pattern in FOLLOW_UP_INDICATORS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _get_last_valid_exchange(
        self,
        history: List[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """
        Get the most recent exchange with a valid question.
        
        Args:
            history: List of conversation exchanges.
            
        Returns:
            Most recent valid exchange or None.
        """
        # Look through recent history (limited by context_turns)
        recent = history[-self.context_turns:] if len(history) > self.context_turns else history
        
        # Go through in reverse to find most recent valid
        for exchange in reversed(recent):
            if isinstance(exchange, dict) and exchange.get("question"):
                return exchange
        
        return None
    
    def _extract_topic(self, exchange: Dict[str, str]) -> str:
        """
        Extract the main topic from a conversation exchange.
        
        Args:
            exchange: Dictionary with 'question' and optionally 'answer'.
            
        Returns:
            Extracted topic string.
        """
        question = exchange.get("question", "")
        
        if not question:
            return "your previous response"
        
        # Pattern 1: "about X"
        match = re.search(r"about\s+(.+?)(?:\?|$)", question, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Pattern 2: "Tell me about/Describe/Explain X"
        match = re.search(
            r"^(?:tell me about|describe|explain)\s+(.+?)(?:\?|$)",
            question,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        
        # Pattern 3: "your X experience/skills"
        match = re.search(
            r"your\s+(.+?)\s+(experience|skills?|background|work)",
            question,
            re.IGNORECASE
        )
        if match:
            return f"your {match.group(1)} {match.group(2)}"
        
        # Pattern 4: "How do you X" / "What is your X" / "What was your X"
        match = re.search(
            r"(?:how do you|what (?:is|was|are|were) your)\s+(.+?)(?:\?|$)",
            question,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        
        # Fallback
        return "your previous response"
    
    def _expand_with_template(self, question: str, prev_topic: str) -> str:
        """
        Expand a follow-up question using templates.
        
        Args:
            question: The follow-up question.
            prev_topic: The topic from the previous exchange.
            
        Returns:
            Expanded question or original if no template matches.
        """
        question_stripped = question.strip()
        question_lower = question_stripped.lower()
        
        for pattern, template in EXPANSION_TEMPLATES.items():
            match = re.match(pattern, question_lower, re.IGNORECASE)
            if match:
                # Build replacement dict
                replacements = {"prev_topic": prev_topic}
                
                # Add any captured groups - preserve original case from input
                groups = match.groups()
                if groups:
                    # Get original text with preserved case
                    orig_match = re.match(pattern, question_stripped, re.IGNORECASE)
                    orig_groups = orig_match.groups() if orig_match else groups
                    replacements["match"] = orig_groups[0] if orig_groups[0] else ""
                    if len(orig_groups) > 1:
                        replacements["match2"] = orig_groups[1] if orig_groups[1] else ""
                
                try:
                    expanded = template.format(**replacements)
                    # Capitalize first letter
                    if expanded:
                        expanded = expanded[0].upper() + expanded[1:]
                    return expanded
                except (KeyError, IndexError):
                    continue
        
        # No template matched, try generic expansion
        return self._generic_expansion(question, prev_topic)
    
    def _generic_expansion(self, question: str, prev_topic: str) -> str:
        """
        Generic expansion for follow-ups that don't match specific templates.
        
        Args:
            question: The follow-up question.
            prev_topic: The topic from the previous exchange.
            
        Returns:
            Expanded question.
        """
        question_lower = question.lower().strip()
        
        # Handle "What about X?" pattern
        match = re.match(r"^what about\s+(.+?)\??$", question_lower)
        if match:
            subject = match.group(1)
            return f"What is your experience with {subject} in relation to {prev_topic}?"
        
        # Handle "How about X?" pattern
        match = re.match(r"^how about\s+(.+?)\??$", question_lower)
        if match:
            subject = match.group(1)
            return f"How do you handle {subject} based on your experience with {prev_topic}?"
        
        # Handle pronoun endings
        if re.search(r"\b(that|this|it)\s*\??$", question_lower):
            # Replace the pronoun with the topic
            expanded = re.sub(
                r"\b(that|this|it)(\s*\??)$",
                f"{prev_topic}\\2",
                question,
                flags=re.IGNORECASE
            )
            return expanded
        
        return question
