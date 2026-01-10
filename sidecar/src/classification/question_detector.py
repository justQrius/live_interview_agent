"""
Question Detector - Tier 1 Rule-Based Classification.

Implements fast, rule-based classification of interview utterances to determine
whether they require a response. This is the first tier of the cascaded
classification system, designed for <2ms latency.

Classification Types:
- interview_question: Standard interview questions requiring full answers
- follow_up: Questions that reference previous context ("What about...?")
- clarification: Requests for repetition or clarification
- small_talk: Social pleasantries not requiring substantive answers
- statement: Declarative statements from interviewer
- acknowledgment: Brief acknowledgments (ok, great, I see)
"""

import re
from typing import Dict, List, Optional, Pattern, Tuple

# Type alias for classification result
ClassificationResult = Tuple[bool, float, str]


class QuestionDetector:
    """
    Rule-based question detector for interview utterances.
    
    Uses pre-compiled regex patterns for fast classification (<2ms P99).
    Returns (is_actionable_question, confidence, classification_type).
    """

    def __init__(self):
        """Initialize detector with pre-compiled patterns."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile all regex patterns for performance."""
        
        # Interview question patterns - these require full answers
        self._interview_patterns: List[Tuple[Pattern[str], float]] = [
            # WH-questions with question words
            (re.compile(r"^what\s+(is|are|was|were|do|did|would|have|has|can|could|should)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^how\s+(do|did|would|have|has|can|could|should|are|is|was|were)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^why\s+(do|did|would|have|has|are|is|was|were)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^when\s+(do|did|would|have|has|can|could)\b", re.IGNORECASE), 0.85),
            (re.compile(r"^where\s+(do|did|would|have|has|can|could)\b", re.IGNORECASE), 0.85),
            (re.compile(r"^who\s+(do|did|would|have|has|can|could|is|was|are|were)\b", re.IGNORECASE), 0.85),
            
            # Behavioral question starters
            (re.compile(r"^tell\s+me\s+about\b", re.IGNORECASE), 0.95),
            (re.compile(r"^describe\s+(a\s+|your\s+|an\s+|the\s+)?", re.IGNORECASE), 0.90),
            (re.compile(r"^explain\s+(how|what|why|your|the|a|an)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^walk\s+me\s+through\b", re.IGNORECASE), 0.95),
            (re.compile(r"^give\s+me\s+an?\s+example\b", re.IGNORECASE), 0.95),
            (re.compile(r"^share\s+(an?\s+|your\s+)?experience\b", re.IGNORECASE), 0.90),
            
            # Can you / Could you patterns
            (re.compile(r"^can\s+you\s+(tell|describe|explain|walk|share|give)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^could\s+you\s+(tell|describe|explain|walk|share|give)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^would\s+you\s+(tell|describe|explain|walk|share|give|mind)\b", re.IGNORECASE), 0.85),
            
            # Have you ever patterns
            (re.compile(r"^have\s+you\s+(ever\s+)?", re.IGNORECASE), 0.85),
            (re.compile(r"^do\s+you\s+have\s+(any\s+)?experience\b", re.IGNORECASE), 0.90),
            
            # Question mark ending (general fallback)
            (re.compile(r"\?$"), 0.75),
        ]
        
        # Follow-up question patterns - reference previous context
        self._follow_up_patterns: List[Tuple[Pattern[str], float]] = [
            (re.compile(r"^what\s+about\b", re.IGNORECASE), 0.90),
            (re.compile(r"^and\s+what\s+(about|happened|did|was|were)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^can\s+you\s+elaborate\b", re.IGNORECASE), 0.90),
            (re.compile(r"^could\s+you\s+elaborate\b", re.IGNORECASE), 0.90),
            (re.compile(r"^tell\s+me\s+more\b", re.IGNORECASE), 0.90),
            (re.compile(r"^what\s+else\b", re.IGNORECASE), 0.85),
            (re.compile(r"^anything\s+else\b", re.IGNORECASE), 0.80),
            (re.compile(r"^how\s+about\b", re.IGNORECASE), 0.85),
            (re.compile(r"^and\s+then\s*\?", re.IGNORECASE), 0.85),
            (re.compile(r"^what\s+happened\s+next\b", re.IGNORECASE), 0.90),
            (re.compile(r"^go\s+on\b", re.IGNORECASE), 0.75),
            (re.compile(r"^please\s+continue\b", re.IGNORECASE), 0.75),
        ]
        
        # Clarification request patterns
        self._clarification_patterns: List[Tuple[Pattern[str], float]] = [
            (re.compile(r"^what\s+do\s+you\s+mean\b", re.IGNORECASE), 0.95),
            (re.compile(r"^could\s+you\s+repeat\b", re.IGNORECASE), 0.95),
            (re.compile(r"^can\s+you\s+repeat\b", re.IGNORECASE), 0.95),
            (re.compile(r"^(sorry|pardon),?\s*(i\s+)?didn'?t\s+(catch|hear|understand)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^i'?m\s+not\s+sure\s+i\s+understand\b", re.IGNORECASE), 0.85),
            (re.compile(r"^can\s+you\s+(rephrase|clarify)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^what\s+was\s+the\s+question\b", re.IGNORECASE), 0.95),
        ]
        
        # Acknowledgment patterns - interviewer acknowledging candidate's response
        # Note: Single-word patterns like "nice" need negative lookahead to avoid
        # matching small talk like "nice weather"
        self._acknowledgment_patterns: List[Tuple[Pattern[str], float]] = [
            (re.compile(r"^(okay|ok|alright|all\s+right)\b", re.IGNORECASE), 0.95),
            (re.compile(r"^(sure|right|yes|yeah|yep|uh\s*huh)\b", re.IGNORECASE), 0.90),
            # Positive adjectives - but NOT followed by small talk words
            (re.compile(r"^(great|perfect|excellent|good|wonderful|fantastic)(?!\s+(to\s+meet|weather|morning|afternoon|evening))\b", re.IGNORECASE), 0.90),
            # "nice" specifically needs to not be followed by small talk nouns
            (re.compile(r"^nice(?!\s+(weather|to\s+meet|day|morning|afternoon|evening))\b", re.IGNORECASE), 0.90),
            (re.compile(r"^(i\s+see|i\s+understand|understood)\b", re.IGNORECASE), 0.95),
            (re.compile(r"^(got\s+it|gotcha)\b", re.IGNORECASE), 0.95),
            (re.compile(r"^makes\s+sense\b", re.IGNORECASE), 0.95),
            # "that's/that is" + positive adjective
            (re.compile(r"^that'?s\s+(good|great|interesting|helpful|clear|a\s+great|a\s+good|very\s+helpful)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^that\s+is\s+(good|great|interesting|helpful|clear|a\s+great|a\s+good|very\s+helpful)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^(fair\s+enough|noted)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^mm+\s*(hm+)?\b", re.IGNORECASE), 0.85),
            (re.compile(r"^uh\s*huh\b", re.IGNORECASE), 0.90),
        ]
        
        # Statement patterns - declarative statements from interviewer
        self._statement_patterns: List[Tuple[Pattern[str], float]] = [
            (re.compile(r"^let\s+me\b", re.IGNORECASE), 0.90),
            (re.compile(r"^let'?s\b", re.IGNORECASE), 0.90),
            (re.compile(r"^we'?ll\b", re.IGNORECASE), 0.85),
            (re.compile(r"^we\s+will\b", re.IGNORECASE), 0.85),
            (re.compile(r"^i'?ll\b", re.IGNORECASE), 0.80),
            (re.compile(r"^i\s+will\b", re.IGNORECASE), 0.80),
            (re.compile(r"^moving\s+on\b", re.IGNORECASE), 0.95),
            (re.compile(r"^next,?\s*(we|i|let)\b", re.IGNORECASE), 0.90),
            (re.compile(r"^now\s+(let'?s|we|i)\b", re.IGNORECASE), 0.85),
            (re.compile(r"^so\s+basically\b", re.IGNORECASE), 0.85),
            (re.compile(r"^in\s+other\s+words\b", re.IGNORECASE), 0.85),
            (re.compile(r"^to\s+summarize\b", re.IGNORECASE), 0.85),
            (re.compile(r"^(just\s+to|to)\s+clarify\b", re.IGNORECASE), 0.80),
            (re.compile(r"^(before\s+we|after\s+this)\b", re.IGNORECASE), 0.80),
        ]
        
        # Small talk patterns - social pleasantries
        self._small_talk_patterns: List[Tuple[Pattern[str], float]] = [
            (re.compile(r"^thank\s*(s|you)\b", re.IGNORECASE), 0.95),
            (re.compile(r"^(nice|good|great)\s+to\s+meet\b", re.IGNORECASE), 0.95),
            (re.compile(r"^(how|hope)\s+(are|was|is)\s+(you|your|the)\s*(commute|trip|day|doing|weather)?\b", re.IGNORECASE), 0.85),
            (re.compile(r"^nice\s+weather\b", re.IGNORECASE), 0.90),
            (re.compile(r"^did\s+you\s+find\s+(the\s+)?(place|office|building)\b", re.IGNORECASE), 0.85),
            (re.compile(r"^(welcome|pleased)\s+to\b", re.IGNORECASE), 0.90),
            (re.compile(r"^(hello|hi|hey|good\s+(morning|afternoon|evening))\b", re.IGNORECASE), 0.90),
        ]
        
        # Filler/noise patterns - should be ignored entirely
        self._filler_patterns: List[Pattern[str]] = [
            re.compile(r"^(um+|uh+|er+|hmm+|ah+)\s*$", re.IGNORECASE),
            re.compile(r"^\s*$"),
        ]

    def is_actionable_question(
        self,
        text: Optional[str],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ClassificationResult:
        """
        Determine if text is an actionable question requiring a response.
        
        Uses cascaded classification:
        - Tier 1: Fast rule-based (<2ms) - handles obvious cases with high confidence
        - Tier 2: Context-aware (<10ms) - uses history for ambiguous cases
        
        Args:
            text: The utterance text to classify
            conversation_history: Optional list of previous conversation turns
                Each turn should have "speaker" and "text" keys
        
        Returns:
            Tuple of (is_actionable_question, confidence, classification_type)
            - is_actionable_question: True if this requires a response
            - confidence: 0.0-1.0 confidence in the classification
            - classification_type: One of interview_question, follow_up,
                clarification, small_talk, statement, acknowledgment
        """
        # Tier 1: Rule-based (fast, handles obvious cases)
        result = self._rule_based_classification(text)
        
        # If high confidence, return immediately
        if result[1] >= 0.80:
            return result
        
        # Tier 2: Context-aware (use history for ambiguous cases)
        if conversation_history and len(conversation_history) > 0:
            context_result = self._context_aware_classification(text, conversation_history, result)
            if context_result[1] > result[1]:  # Only use if more confident
                return context_result
        
        return result

    def _context_aware_classification(
        self,
        text: Optional[str],
        history: List[Dict[str, str]],
        rule_based_result: ClassificationResult,
    ) -> ClassificationResult:
        """
        Tier 2: Context-aware classification using conversation history.
        
        Analyzes patterns in recent conversation to improve classification
        for ambiguous cases where rule-based matching has low confidence.
        
        Target: <10ms latency, 80-85% accuracy.
        
        Args:
            text: The utterance text to classify
            history: List of previous conversation turns
            rule_based_result: Result from Tier 1 for comparison
        
        Returns:
            ClassificationResult with context-informed classification
        """
        if not text:
            return rule_based_result
        
        text_lower = text.strip().lower()
        
        # Get last 3-5 turns (most recent, limited for performance)
        recent_history = history[-5:] if len(history) > 5 else history
        
        # Check if last turn was candidate's answer
        last_turn_was_answer = self._was_last_turn_candidate_answer(recent_history)
        
        # Check for pronoun references (indicates follow-up)
        has_pronoun_reference = self._has_pronoun_reference(text_lower)
        
        # Check if this is an ambiguous short phrase
        is_short_phrase = len(text_lower.split()) <= 4
        
        # Context-based classification logic
        if last_turn_was_answer:
            # After candidate's answer, short ambiguous phrases are likely acknowledgments
            if is_short_phrase and rule_based_result[2] == "statement":
                return (False, 0.75, "acknowledgment")
            
            # Pronoun references after answer suggest follow-up
            if has_pronoun_reference and rule_based_result[0]:
                return (True, 0.85, "follow_up")
        
        # Check if there's a question in recent history that this could follow
        has_recent_question = self._has_recent_question(recent_history)
        
        if has_recent_question and has_pronoun_reference:
            # Pronoun reference with recent question = likely follow-up
            if rule_based_result[0]:
                return (True, 0.82, "follow_up")
        
        return rule_based_result

    def _was_last_turn_candidate_answer(self, history: List[Dict[str, str]]) -> bool:
        """Check if the last turn in history was a candidate's answer."""
        if not history:
            return False
        
        last_turn = history[-1]
        speaker = last_turn.get("speaker", "").lower()
        text = last_turn.get("text", "")
        
        # Check if speaker is candidate and has substantial text
        return "candidate" in speaker and len(text) > 20

    def _has_pronoun_reference(self, text: str) -> bool:
        """Check if text contains pronouns that reference previous context."""
        pronoun_patterns = [
            r"\bthat\b",
            r"\bthis\b",
            r"\bit\b",
            r"\bthose\b",
            r"\bthese\b",
        ]
        for pattern in pronoun_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_recent_question(self, history: List[Dict[str, str]]) -> bool:
        """Check if there's a question from interviewer in recent history."""
        for turn in reversed(history):
            speaker = turn.get("speaker", "").lower()
            text = turn.get("text", "")
            
            if "interviewer" in speaker and text:
                # Check if it looks like a question
                if "?" in text or any(q in text.lower() for q in ["tell me", "describe", "explain", "what", "how", "why"]):
                    return True
        return False

    def _rule_based_classification(self, text: Optional[str]) -> ClassificationResult:
        """
        Tier 1: Fast rule-based classification using regex patterns.
        
        Target: <2ms P99 latency, 65-75% accuracy.
        """
        # Handle edge cases
        if not text:
            return (False, 0.30, "statement")
        
        # Normalize text
        text = text.strip()
        if not text:
            return (False, 0.30, "statement")
        
        # Check for fillers first (fastest path)
        for pattern in self._filler_patterns:
            if pattern.match(text):
                return (False, 0.40, "statement")
        
        # Check acknowledgments (very common, check early)
        for pattern, confidence in self._acknowledgment_patterns:
            if pattern.search(text):
                return (False, confidence, "acknowledgment")
        
        # Check small talk
        for pattern, confidence in self._small_talk_patterns:
            if pattern.search(text):
                return (False, confidence, "small_talk")
        
        # Check statements (interviewer declarations)
        for pattern, confidence in self._statement_patterns:
            if pattern.search(text):
                return (False, confidence, "statement")
        
        # Check clarification requests (these ARE actionable)
        for pattern, confidence in self._clarification_patterns:
            if pattern.search(text):
                return (True, confidence, "clarification")
        
        # Check follow-up questions (these ARE actionable)
        for pattern, confidence in self._follow_up_patterns:
            if pattern.search(text):
                return (True, confidence, "follow_up")
        
        # Check interview questions (main positive case)
        for pattern, confidence in self._interview_patterns:
            if pattern.search(text):
                return (True, confidence, "interview_question")
        
        # Default: If nothing matched, likely a statement
        # Lower confidence indicates uncertainty
        return (False, 0.55, "statement")

    def get_pattern_stats(self) -> Dict[str, int]:
        """
        Get statistics about compiled patterns for debugging.
        
        Returns:
            Dict with counts of patterns per category
        """
        return {
            "interview_patterns": len(self._interview_patterns),
            "follow_up_patterns": len(self._follow_up_patterns),
            "clarification_patterns": len(self._clarification_patterns),
            "acknowledgment_patterns": len(self._acknowledgment_patterns),
            "statement_patterns": len(self._statement_patterns),
            "small_talk_patterns": len(self._small_talk_patterns),
            "filler_patterns": len(self._filler_patterns),
        }
