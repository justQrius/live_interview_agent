"""
Completeness Detector - Multi-tier detection of utterance completeness.

Implements a 4-tier cascaded detection system to determine whether an
accumulated transcription is a complete utterance ready for question
detection, or if more segments should be accumulated.

Detection Tiers:
- Tier 1: Punctuation-based (<1ms) - "?" or "." with question context
- Tier 2: Syntactic analysis (<5ms) - Complete grammatical structure
- Tier 3: Timing-based (<1ms) - Pause duration threshold
- Tier 4: LLM fallback (~150ms) - Ambiguous cases

This module is part of the Utterance Accumulation feature that buffers
transcription segments until semantically complete.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Pattern, Tuple

from src.classification.accumulator_models import (
    AccumulatorConfig,
    CompletenessResult,
    DetectionTier,
)

logger = logging.getLogger(__name__)


# LLM prompt for completeness detection
LLM_COMPLETENESS_PROMPT = """Determine if this is a complete utterance or still in progress.

Utterance: "{text}"

Recent conversation:
{context}

Reply ONLY with:
- COMPLETE - if this is a finished thought/question
- INCOMPLETE - if the speaker is likely still talking

Your response:"""


class CompletenessDetector:
    """
    Multi-tier detection of utterance completeness.
    
    Uses cascaded detection to balance latency and accuracy:
    - Tier 1: Punctuation check (<1ms) - handles clear endings
    - Tier 2: Syntactic check (<5ms) - handles complete structures
    - Tier 3: Timing check (<1ms) - uses pause duration
    - Tier 4: LLM fallback (~150ms) - handles ambiguous cases
    
    Returns CompletenessResult with decision and metadata.
    
    Example:
        detector = CompletenessDetector(config)
        result = await detector.is_complete("Tell me about your experience?")
        if result.is_complete:
            # Process the utterance
            pass
    """
    
    def __init__(
        self,
        config: AccumulatorConfig,
        llm_provider: Optional[Any] = None
    ):
        """
        Initialize the completeness detector.
        
        Args:
            config: AccumulatorConfig with detection thresholds
            llm_provider: Optional LLM provider for Tier 4 fallback.
                         Must implement async generate_response(prompt, context, history)
        """
        self.config = config
        self.llm_provider = llm_provider
        self._compile_patterns()
        self._logger = logging.getLogger(__name__)
    
    def set_llm_provider(self, provider: Any) -> None:
        """
        Set or update the LLM provider for Tier 4 detection.
        
        Args:
            provider: LLM provider implementing generate_response()
        """
        self.llm_provider = provider
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        
        # Incomplete markers - strong signals to defer completion
        # These indicate the speaker is not finished
        self._incomplete_patterns: List[Tuple[Pattern[str], str]] = [
            # Trailing ellipsis (various forms)
            (re.compile(r"\.\.\.+$"), "trailing_ellipsis"),
            (re.compile(r"\u2026$"), "trailing_ellipsis"),  # Unicode ellipsis
            
            # Mid-word cutoff (ends with hyphen)
            (re.compile(r"\w+-$"), "mid_word_cutoff"),
            
            # Ends with single letter after space (word got cut off)
            (re.compile(r"\s[a-zA-Z]$"), "word_cutoff"),
            
            # Trailing conjunctions/prepositions (open clause)
            (re.compile(r"\b(and|but|or|so|because|since|although|if|when|while|that|which|where|who|what|how|why|with|about|for|to|from|by|in|at|on)\s*$", re.IGNORECASE), "trailing_conjunction"),
            
            # Open clauses without predicate
            (re.compile(r"\b(when you were at|if you had|what about|tell me about|how about|regarding)\s*$", re.IGNORECASE), "open_clause"),
            
            # Self-correction signals at end
            (re.compile(r"\b(I mean|sorry|let me rephrase|actually|wait|no wait)\s*$", re.IGNORECASE), "self_correction"),
            
            # Dangling prepositions
            (re.compile(r"\b(about|with|for|from|by|to|at|in|on|of)\s*$", re.IGNORECASE), "dangling_preposition"),
        ]
        
        # Filler/non-terminal patterns at START - these suggest more is coming
        self._nonterminal_patterns: List[Tuple[Pattern[str], str]] = [
            (re.compile(r"^let me think", re.IGNORECASE), "filler_thinking"),
            (re.compile(r"^so basically", re.IGNORECASE), "filler_opening"),
            (re.compile(r"^what I mean is", re.IGNORECASE), "filler_clarification"),
            (re.compile(r"^hmm+", re.IGNORECASE), "filler_hmm"),
            (re.compile(r"^um+", re.IGNORECASE), "filler_um"),
            (re.compile(r"^uh+", re.IGNORECASE), "filler_uh"),
            (re.compile(r"^well,?\s*$", re.IGNORECASE), "filler_well"),
            (re.compile(r"^I mean,?\s*$", re.IGNORECASE), "filler_imean"),
            (re.compile(r"^you know,?\s*$", re.IGNORECASE), "filler_youknow"),
            (re.compile(r"^okay so\s*$", re.IGNORECASE), "filler_okayso"),
        ]
        
        # Complete question patterns (Tier 2)
        # These patterns indicate syntactically complete structures
        self._complete_question_patterns: List[Tuple[Pattern[str], float]] = [
            # WH-questions with verb and object ending with ?
            (re.compile(r"^(what|how|why|when|where|who)\s+\w+.*[?.!]$", re.IGNORECASE), 0.85),
            
            # Tell me / Describe / Explain with ending punctuation
            (re.compile(r"^(tell me|describe|explain|walk me through|give me)\b.*[.?!]$", re.IGNORECASE), 0.85),
            
            # Can/Could/Would you patterns with ending
            (re.compile(r"^(can|could|would|will)\s+you\s+\w+.*[.?!]$", re.IGNORECASE), 0.85),
            
            # Have you ever patterns
            (re.compile(r"^have\s+you\s+(ever\s+)?\w+.*[.?!]$", re.IGNORECASE), 0.80),
            
            # Do/Did you patterns
            (re.compile(r"^(do|did)\s+you\s+\w+.*[.?!]$", re.IGNORECASE), 0.80),
        ]
        
        # Complete statement patterns without punctuation
        # These need higher word count threshold
        self._complete_structure_patterns: List[Tuple[Pattern[str], float]] = [
            # WH-word + auxiliary + subject pattern
            (re.compile(r"^(what|how|why)\s+(is|are|was|were|do|did|would|have|has|can|could|should)\s+", re.IGNORECASE), 0.70),
            
            # Imperative patterns
            (re.compile(r"^(tell me about|describe|explain|walk me through)\s+.{10,}", re.IGNORECASE), 0.75),
            
            # Can you / Could you with substantial content
            (re.compile(r"^(can|could|would)\s+you\s+(tell|describe|explain|share|give)\s+.{10,}", re.IGNORECASE), 0.75),
        ]
        
        # Question starters (for Tier 2 structure analysis)
        self._question_starters = [
            "what", "how", "why", "when", "where", "who", "which",
            "tell me", "describe", "explain", "walk me through", "give me",
            "can you", "could you", "would you", "will you",
            "have you", "do you", "did you", "are you", "is there"
        ]
        
        # Common auxiliary verbs for structure detection
        self._auxiliary_verbs = [
            "is", "are", "was", "were", "do", "does", "did",
            "have", "has", "had", "would", "could", "should",
            "can", "will", "may", "might"
        ]
    
    async def is_complete(
        self,
        text: str,
        pause_duration_ms: int = 0,
        context: Optional[List[str]] = None
    ) -> CompletenessResult:
        """
        Determine if the accumulated text is a complete utterance.
        
        Uses a 4-tier cascaded detection system:
        1. Check for incomplete markers first (fast rejection)
        2. Tier 1: Punctuation-based detection (<1ms)
        3. Tier 2: Syntactic structure detection (<5ms)
        4. Tier 3: Timing-based detection (<1ms)
        5. Tier 4: LLM fallback for ambiguous cases (~150ms)
        
        Args:
            text: Accumulated transcription text
            pause_duration_ms: Time since last segment ended (ms)
            context: Previous conversation turns (optional, for LLM context)
        
        Returns:
            CompletenessResult with is_complete, confidence, tier_used, reason
        """
        text = text.strip() if text else ""
        
        # Empty text is incomplete
        if not text:
            return CompletenessResult.incomplete(
                confidence=0.0,
                tier=DetectionTier.EMPTY.value,
                reason="Empty text"
            )
        
        # Check for incomplete markers first (should defer completion)
        incomplete_result = self._check_incomplete_markers(text)
        if incomplete_result:
            return incomplete_result
        
        # Tier 1: Punctuation check (<1ms)
        tier1_result = self._tier1_punctuation(text)
        if tier1_result.is_complete and tier1_result.confidence >= self.config.tier1_confidence:
            return tier1_result
        
        # Tier 2: Syntactic completeness (<5ms)
        tier2_result = self._tier2_syntax(text)
        if tier2_result.is_complete and tier2_result.confidence >= self.config.tier2_confidence:
            return tier2_result
        
        # Tier 3: Timing-based (uses pause_duration_ms)
        if pause_duration_ms > 0:
            tier3_result = self._tier3_timing(text, pause_duration_ms)
            if tier3_result.is_complete:
                return tier3_result
        
        # Tier 4: LLM fallback for ambiguous cases
        # Only use if:
        # - LLM fallback is enabled
        # - We have an LLM provider
        # - Combined confidence is below threshold
        # - Text has enough content to analyze
        combined_confidence = max(tier1_result.confidence, tier2_result.confidence)
        
        if (self.config.use_llm_fallback and 
            self.llm_provider and 
            combined_confidence < self.config.llm_fallback_threshold and
            len(text.split()) >= 3):
            
            tier4_result = await self._tier4_llm(text, context)
            return tier4_result
        
        # Default: Not complete enough, continue accumulating
        return CompletenessResult.incomplete(
            confidence=combined_confidence,
            tier=DetectionTier.NONE.value,
            reason="No tier matched; continuing accumulation"
        )
    
    def _check_incomplete_markers(self, text: str) -> Optional[CompletenessResult]:
        """
        Check for markers that indicate utterance is definitely incomplete.
        
        These are strong signals that the speaker is not finished and
        we should wait for more input.
        
        Args:
            text: The utterance text to check
        
        Returns:
            CompletenessResult if incomplete markers found, None otherwise
        """
        # Check for trailing incomplete patterns
        for pattern, marker_type in self._incomplete_patterns:
            if pattern.search(text):
                return CompletenessResult.incomplete(
                    confidence=0.30,
                    tier=DetectionTier.INCOMPLETE_MARKER.value,
                    reason=f"Incomplete marker detected: {marker_type}",
                    should_wait=True,
                    wait_reason=marker_type
                )
        
        # Check for non-terminal opening patterns
        # Only flag as incomplete if the entire text is just the filler
        for pattern, marker_type in self._nonterminal_patterns:
            if pattern.match(text):
                # If text is ONLY the filler phrase, wait for content
                if len(text.split()) <= 5:
                    return CompletenessResult.incomplete(
                        confidence=0.20,
                        tier=DetectionTier.NONTERMINAL.value,
                        reason=f"Non-terminal phrase: {marker_type}",
                        should_wait=True,
                        wait_reason=marker_type
                    )
        
        return None
    
    def _tier1_punctuation(self, text: str) -> CompletenessResult:
        """
        Tier 1: Punctuation-based completion detection (<1ms).
        
        Checks for terminal punctuation that indicates completion:
        - Question mark "?" -> high confidence complete
        - Period "." with question-like structure -> moderate confidence
        - Exclamation mark "!" -> moderate confidence
        
        Args:
            text: The utterance text to check
        
        Returns:
            CompletenessResult with punctuation-based assessment
        """
        # Question mark = high confidence complete
        if text.rstrip().endswith("?"):
            return CompletenessResult.complete(
                confidence=0.90,
                tier=DetectionTier.TIER1_PUNCTUATION.value,
                reason="Ends with question mark"
            )
        
        # Period with question-like or imperative structure
        if text.rstrip().endswith("."):
            lower = text.lower()
            word_count = len(text.split())
            
            # Check if it looks like a command/request (starts with imperative)
            imperative_starters = [
                "tell me", "describe", "explain", "walk me through",
                "give me", "share", "outline", "discuss"
            ]
            if any(lower.startswith(starter) for starter in imperative_starters):
                return CompletenessResult.complete(
                    confidence=0.90,
                    tier=DetectionTier.TIER1_PUNCTUATION.value,
                    reason="Imperative statement with period"
                )
            
            # Check if it CONTAINS an imperative verb (e.g., "So I have a question. Describe your...")
            imperative_verbs = ["describe", "explain", "tell me", "walk me through", "give me", "share", "outline"]
            if any(verb in lower for verb in imperative_verbs) and word_count >= 5:
                return CompletenessResult.complete(
                    confidence=0.88,
                    tier=DetectionTier.TIER1_PUNCTUATION.value,
                    reason="Contains imperative verb with period"
                )
            
            # Long substantive statement with period - high confidence
            if word_count >= 10:
                return CompletenessResult.complete(
                    confidence=0.85,
                    tier=DetectionTier.TIER1_PUNCTUATION.value,
                    reason="Long statement with period (very substantive)"
                )
            
            # Medium length statement with period
            if word_count >= 5:
                return CompletenessResult.complete(
                    confidence=0.80,
                    tier=DetectionTier.TIER1_PUNCTUATION.value,
                    reason="Statement with period (substantive)"
                )
            else:
                return CompletenessResult.incomplete(
                    confidence=0.50,
                    tier=DetectionTier.TIER1_PUNCTUATION.value,
                    reason="Short statement with period (may be incomplete)"
                )
        
        # Exclamation mark
        if text.rstrip().endswith("!"):
            return CompletenessResult.complete(
                confidence=0.80,
                tier=DetectionTier.TIER1_PUNCTUATION.value,
                reason="Ends with exclamation mark"
            )
        
        # No terminal punctuation - incomplete at this tier
        return CompletenessResult.incomplete(
            confidence=0.40,
            tier=DetectionTier.TIER1_PUNCTUATION.value,
            reason="No terminal punctuation"
        )
    
    def _tier2_syntax(self, text: str) -> CompletenessResult:
        """
        Tier 2: Syntactic completeness detection (<5ms).
        
        Uses regex patterns and heuristics to detect complete
        grammatical structures:
        - Complete question patterns (WH + verb + object)
        - Imperative patterns (Tell me about + object)
        - Subject-verb-object structures
        
        Args:
            text: The utterance text to check
        
        Returns:
            CompletenessResult with syntax-based assessment
        """
        # Check against complete question patterns (with punctuation)
        for pattern, confidence in self._complete_question_patterns:
            if pattern.match(text):
                return CompletenessResult.complete(
                    confidence=confidence,
                    tier=DetectionTier.TIER2_SYNTAX.value,
                    reason="Matches complete question pattern"
                )
        
        # Check structure patterns (may lack punctuation)
        for pattern, base_confidence in self._complete_structure_patterns:
            if pattern.match(text):
                # Adjust confidence based on word count
                word_count = len(text.split())
                if word_count >= 8:
                    confidence = min(base_confidence + 0.10, 0.85)
                elif word_count >= 5:
                    confidence = base_confidence
                else:
                    confidence = base_confidence - 0.10
                
                return CompletenessResult.complete(
                    confidence=confidence,
                    tier=DetectionTier.TIER2_SYNTAX.value,
                    reason=f"Complete structure pattern ({word_count} words)"
                )
        
        # Heuristic analysis: subject-verb-object detection
        lower = text.lower()
        words = text.split()
        word_count = len(words)
        
        # Check for question starters
        has_question_starter = any(
            lower.startswith(starter) for starter in self._question_starters
        )
        
        # Check for auxiliary verb (suggests complete clause)
        has_auxiliary = any(
            f" {aux} " in f" {lower} " for aux in self._auxiliary_verbs
        )
        
        # Sufficient length with structure indicators = likely complete
        if has_question_starter and word_count >= 5:
            if has_auxiliary or word_count >= 8:
                return CompletenessResult.complete(
                    confidence=0.75,
                    tier=DetectionTier.TIER2_SYNTAX.value,
                    reason="Question starter with substantive content"
                )
            else:
                return CompletenessResult.incomplete(
                    confidence=0.55,
                    tier=DetectionTier.TIER2_SYNTAX.value,
                    reason="Question starter but structure may be incomplete"
                )
        
        # Default: Structure appears incomplete
        return CompletenessResult.incomplete(
            confidence=0.45,
            tier=DetectionTier.TIER2_SYNTAX.value,
            reason="Structure appears incomplete"
        )
    
    def _tier3_timing(self, text: str, pause_duration_ms: int) -> CompletenessResult:
        """
        Tier 3: Timing-based completion detection (<1ms).
        
        Uses pause duration to infer completion:
        - Longer pause = higher confidence speaker is done
        - Formula: confidence = min(0.85, 0.70 + (pause_ms - 1500) / 5000)
        
        Args:
            text: The utterance text
            pause_duration_ms: Time since last segment ended
        
        Returns:
            CompletenessResult with timing-based assessment
        """
        soft_timeout = self.config.soft_timeout_ms
        
        # Past soft timeout - likely complete
        if pause_duration_ms >= soft_timeout:
            # Calculate confidence based on how far past threshold
            # Base confidence of 0.70, increases with longer pauses
            base_confidence = self.config.tier3_confidence
            extra_pause = pause_duration_ms - 1500  # Start counting from 1500ms
            confidence_boost = min(0.15, extra_pause / 5000)  # Up to 0.15 boost
            
            confidence = min(0.85, base_confidence + confidence_boost)
            
            return CompletenessResult.complete(
                confidence=confidence,
                tier=DetectionTier.TIER3_TIMING.value,
                reason=f"Pause duration {pause_duration_ms}ms exceeds soft timeout"
            )
        
        # Moderate pause with substantive text
        word_count = len(text.split())
        if pause_duration_ms >= 1500 and word_count >= 5:
            # Moderate confidence - pause is notable but not conclusive
            confidence = self.config.tier3_confidence - 0.10
            
            return CompletenessResult.complete(
                confidence=confidence,
                tier=DetectionTier.TIER3_TIMING.value,
                reason=f"Moderate pause {pause_duration_ms}ms with {word_count} words"
            )
        
        # Pause below threshold
        return CompletenessResult.incomplete(
            confidence=0.40,
            tier=DetectionTier.TIER3_TIMING.value,
            reason=f"Pause {pause_duration_ms}ms below threshold"
        )
    
    async def _tier4_llm(
        self,
        text: str,
        context: Optional[List[str]] = None
    ) -> CompletenessResult:
        """
        Tier 4: LLM fallback for ambiguous cases (~150ms).
        
        Uses a fast LLM (gpt-4o-mini, gemini-flash, claude-haiku) to
        determine if the utterance is complete. Only called when:
        - use_llm_fallback is enabled
        - llm_provider is set
        - Combined confidence from Tier 1-3 is below threshold
        
        Args:
            text: The utterance text
            context: Optional list of recent conversation turns
        
        Returns:
            CompletenessResult with LLM-based assessment
        """
        if self.llm_provider is None:
            return CompletenessResult.incomplete(
                confidence=0.50,
                tier=DetectionTier.ERROR.value,
                reason="LLM provider not available"
            )
        
        try:
            start_time = time.time()
            
            # Format context for prompt
            context_str = ""
            if context and len(context) > 0:
                # Take last 3 context entries
                recent = context[-3:]
                context_str = "\n".join(recent)
            else:
                context_str = "No previous context."
            
            prompt = LLM_COMPLETENESS_PROMPT.format(
                text=text,
                context=context_str
            )
            
            # Generate response - stream but collect quickly
            response_text = ""
            async for chunk in self.llm_provider.generate_response(prompt, "", []):
                response_text += chunk
                # We only need a short response (COMPLETE or INCOMPLETE)
                if len(response_text) > 20:
                    break
            
            latency_ms = (time.time() - start_time) * 1000
            self._logger.debug(f"Tier 4 LLM took {latency_ms:.0f}ms")
            
            # Parse response
            response_upper = response_text.upper()
            is_complete = "COMPLETE" in response_upper and "INCOMPLETE" not in response_upper
            
            if is_complete:
                return CompletenessResult.complete(
                    confidence=0.85,
                    tier=DetectionTier.TIER4_LLM.value,
                    reason=f"LLM classified as complete ({latency_ms:.0f}ms)"
                )
            else:
                return CompletenessResult.incomplete(
                    confidence=0.75,
                    tier=DetectionTier.TIER4_LLM.value,
                    reason=f"LLM classified as incomplete ({latency_ms:.0f}ms)"
                )
            
        except Exception as e:
            self._logger.warning(f"Tier 4 LLM failed: {e}")
            return CompletenessResult.incomplete(
                confidence=0.50,
                tier=DetectionTier.ERROR.value,
                reason=f"LLM error: {str(e)}"
            )
    
    def get_pattern_stats(self) -> Dict[str, int]:
        """
        Get statistics about compiled patterns for debugging.
        
        Returns:
            Dict with counts of patterns per category
        """
        return {
            "incomplete_patterns": len(self._incomplete_patterns),
            "nonterminal_patterns": len(self._nonterminal_patterns),
            "complete_question_patterns": len(self._complete_question_patterns),
            "complete_structure_patterns": len(self._complete_structure_patterns),
            "question_starters": len(self._question_starters),
            "auxiliary_verbs": len(self._auxiliary_verbs),
        }
