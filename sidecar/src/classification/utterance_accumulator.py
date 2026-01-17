"""
Utterance Accumulator - Orchestrates segment accumulation by speaker.

Accumulates transcription segments from the same speaker until the utterance
is semantically and syntactically complete, dramatically improving question
detection accuracy for multi-sentence interview questions.

Core behavior:
- Maintains per-speaker buffers
- Appends segments from same speaker
- Finalizes buffer on speaker change
- Uses CompletenessDetector for completion decisions
- Enforces hard timeout and buffer limits

This module is part of the Utterance Accumulation feature.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional

from src.classification.accumulator_models import (
    AccumulatorConfig,
    CompletionReason,
    CompleteUtterance,
    CompletenessResult,
    DetectionTier,
    SpeakerBuffer,
)
from src.classification.completeness_detector import CompletenessDetector

logger = logging.getLogger(__name__)


class UtteranceAccumulator:
    """
    Accumulates transcription segments by speaker until semantically complete.
    
    Sits between STT output and question detection, buffering segments from
    the same speaker until the utterance is deemed complete by the
    CompletenessDetector or forced by timeout/limits.
    
    Example:
        accumulator = UtteranceAccumulator(config)
        accumulator.set_llm_provider(llm)
        
        # In transcription handler:
        result = await accumulator.add_segment(text, speaker, timestamp)
        if result:
            # Process complete utterance
            await process_question(result.text)
    
    Attributes:
        config: AccumulatorConfig with timing and detection thresholds
        buffers: Dict mapping speaker IDs to their SpeakerBuffer
        completeness_detector: CompletenessDetector for completion decisions
    """
    
    def __init__(self, config: Optional[AccumulatorConfig] = None):
        """
        Initialize the utterance accumulator.
        
        Args:
            config: AccumulatorConfig with timing thresholds and feature flags.
                   Defaults to AccumulatorConfig() with standard values.
        """
        self.config = config or AccumulatorConfig()
        self.buffers: Dict[str, SpeakerBuffer] = {}
        self.completeness_detector = CompletenessDetector(self.config)
        self._logger = logging.getLogger(__name__)
    
    def set_llm_provider(self, provider: Any) -> None:
        """
        Set LLM provider for Tier 4 completeness detection.
        
        The LLM provider is used as a fallback when Tiers 1-3 cannot
        confidently determine completion. Must implement:
            async generate_response(prompt, context, history)
        
        Args:
            provider: LLM provider implementing generate_response()
        """
        self.completeness_detector.set_llm_provider(provider)
    
    async def add_segment(
        self,
        text: str,
        speaker: str,
        timestamp: float,
        is_final: bool = True
    ) -> Optional[CompleteUtterance]:
        """
        Add a transcription segment to the accumulator.
        
        This is the main entry point for processing STT output. The segment
        is added to the speaker's buffer, and completeness is checked.
        
        Args:
            text: Transcribed text for this segment
            speaker: Speaker identifier (e.g., "Interviewer", "User")
            timestamp: Time when segment was received (seconds since epoch)
            is_final: Whether this is a final (not interim) transcription.
                     Interim transcriptions update buffer but don't trigger
                     completeness checks.
        
        Returns:
            CompleteUtterance if accumulation is complete, None if still buffering.
            May also return a complete utterance from a previous speaker if
            speaker changed.
        """
        # Edge case: Empty text - skip processing
        if not text or not text.strip():
            self._logger.debug("Skipping empty segment")
            return None
        
        text = text.strip()
        
        # Feature flag: If disabled, bypass accumulation entirely
        if not self.config.enabled:
            self._logger.debug("Accumulation disabled, returning segment immediately")
            return CompleteUtterance(
                text=text,
                speaker=speaker,
                start_time=timestamp,
                end_time=timestamp,
                segment_count=1,
                completion_reason="Accumulation disabled",
                confidence=1.0,
                tier_used=DetectionTier.FORCED.value,
                is_partial=False,
            )
        
        # Handle speaker change - finalize previous speaker's buffer
        completed_from_speaker_change = await self._handle_speaker_change(
            speaker, timestamp
        )
        
        # Get or create buffer for this speaker
        buffer = self._get_or_create_buffer(speaker)
        
        # Check hard timeout before appending
        if self._check_hard_timeout(buffer, timestamp):
            self._logger.info(
                f"Hard timeout reached for {speaker} before append, "
                f"forcing completion"
            )
            completed = self._finalize_buffer(
                buffer,
                CompletionReason.TIMEOUT,
                0.70,
                DetectionTier.FORCED,
            )
            buffer.reset()
            return completed
        
        # Check if we should merge with previous segment (gap < merge_gap_ms)
        # If merging, we skip re-checking completeness for efficiency
        should_check_completeness = True
        if not buffer.is_empty:
            gap_ms = (timestamp - buffer.last_segment_time) * 1000
            if gap_ms < self.config.merge_gap_ms:
                # Merge without completeness check - clearly mid-sentence
                self._logger.debug(
                    f"Merging segment (gap {gap_ms:.0f}ms < {self.config.merge_gap_ms}ms)"
                )
                should_check_completeness = False
        
        # Append the new segment
        buffer.append(text, timestamp)
        self._logger.debug(
            f"Buffer for {speaker}: {buffer.segment_count} segments, "
            f"{buffer.total_characters} chars, '{buffer.text[:50]}...'"
        )
        
        # Check buffer limits - force completion if exceeded
        if self._check_buffer_limit(buffer):
            self._logger.warning(
                f"Buffer limit reached for {speaker}: "
                f"{buffer.total_characters} chars"
            )
            completed = self._finalize_buffer(
                buffer,
                CompletionReason.LIMIT,
                0.70,
                DetectionTier.LIMIT,
                is_partial=True,
            )
            buffer.reset()
            return completed
        
        # Check hard timeout after append
        if self._check_hard_timeout(buffer, timestamp):
            self._logger.info(
                f"Hard timeout reached for {speaker} after append, "
                f"forcing completion"
            )
            completed = self._finalize_buffer(
                buffer,
                CompletionReason.TIMEOUT,
                0.70,
                DetectionTier.FORCED,
                is_partial=True,
            )
            buffer.reset()
            return completed
        
        # For interim transcriptions, don't check completeness
        if not is_final:
            self._logger.debug("Interim transcription, skipping completeness check")
            return completed_from_speaker_change
        
        # Check completeness if not merging
        if should_check_completeness:
            # Calculate pause duration since last segment (for timing-based detection)
            # For a new segment, pause is 0 since we just received it
            pause_ms = 0
            
            result = await self.completeness_detector.is_complete(
                buffer.text,
                pause_duration_ms=pause_ms,
                context=None  # TODO: Add conversation context if available
            )
            
            self._logger.debug(
                f"Completeness check: complete={result.is_complete}, "
                f"confidence={result.confidence:.2f}, tier={result.tier_used}"
            )
            
            if result.is_complete and result.confidence >= self.config.tier1_confidence:
                # High confidence completion - finalize immediately
                self._logger.info(
                    f"Utterance complete via {result.tier_used}: "
                    f"'{buffer.text[:80]}...'"
                )
                completed = self._finalize_buffer(
                    buffer,
                    self._reason_from_tier(result.tier_used),
                    result.confidence,
                    self._tier_from_string(result.tier_used),
                )
                buffer.reset()
                return completed
            
            if result.should_wait:
                # Incomplete markers detected - continue buffering
                self._logger.debug(
                    f"Incomplete marker detected: {result.wait_reason}, "
                    f"continuing accumulation"
                )
                return completed_from_speaker_change
            
            # Moderate confidence - check if we should complete
            # based on a lower threshold for tier 2/3
            if result.is_complete:
                if result.confidence >= self.config.tier2_confidence:
                    self._logger.info(
                        f"Utterance complete (moderate confidence) via "
                        f"{result.tier_used}: '{buffer.text[:80]}...'"
                    )
                    completed = self._finalize_buffer(
                        buffer,
                        self._reason_from_tier(result.tier_used),
                        result.confidence,
                        self._tier_from_string(result.tier_used),
                    )
                    buffer.reset()
                    return completed
        
        # Still buffering - return any completed utterance from speaker change
        return completed_from_speaker_change
    
    def get_buffer(self, speaker: str) -> Optional[SpeakerBuffer]:
        """
        Get the current buffer for a speaker.
        
        Args:
            speaker: Speaker identifier
        
        Returns:
            SpeakerBuffer if exists, None otherwise
        """
        return self.buffers.get(speaker)
    
    def get_buffer_preview(self, speaker: str, max_chars: int = 100) -> str:
        """
        Get a preview of the buffer contents for UI status display.
        
        Args:
            speaker: Speaker identifier
            max_chars: Maximum characters to return (default 100)
        
        Returns:
            Truncated buffer text with "..." prefix if truncated,
            empty string if buffer doesn't exist or is empty
        """
        buffer = self.buffers.get(speaker)
        if buffer is None or buffer.is_empty:
            return ""
        
        text = buffer.text
        if len(text) <= max_chars:
            return text
        
        # Truncate and add ellipsis at start
        return "..." + text[-(max_chars - 3):]
    
    def force_complete(self, speaker: str) -> Optional[CompleteUtterance]:
        """
        Force immediate completion of a speaker's buffer.
        
        Used for manual override (e.g., user pressing "Generate Now" button)
        or when session is ending and buffers need to be flushed.
        
        Args:
            speaker: Speaker identifier
        
        Returns:
            CompleteUtterance if buffer had content, None if empty or not found
        """
        buffer = self.buffers.get(speaker)
        if buffer is None or buffer.is_empty:
            self._logger.debug(f"No buffer to force complete for {speaker}")
            return None
        
        self._logger.info(
            f"Force completing buffer for {speaker}: '{buffer.text[:80]}...'"
        )
        
        completed = self._finalize_buffer(
            buffer,
            CompletionReason.FORCED,
            0.60,
            DetectionTier.FORCED,
            is_partial=True,
        )
        buffer.reset()
        return completed
    
    def reset(self, speaker: Optional[str] = None) -> None:
        """
        Reset buffer(s) for a new session or after processing.
        
        Args:
            speaker: Specific speaker to reset, or None to reset all buffers
        """
        if speaker is not None:
            buffer = self.buffers.get(speaker)
            if buffer:
                buffer.reset()
                self._logger.debug(f"Reset buffer for {speaker}")
        else:
            for buffer in self.buffers.values():
                buffer.reset()
            self.buffers.clear()
            self._logger.debug("Reset all buffers")
    
    def _get_or_create_buffer(self, speaker: str) -> SpeakerBuffer:
        """
        Get existing buffer for speaker or create a new one.
        
        Args:
            speaker: Speaker identifier
        
        Returns:
            SpeakerBuffer for the speaker
        """
        if speaker not in self.buffers:
            self.buffers[speaker] = SpeakerBuffer(speaker=speaker)
            self._logger.debug(f"Created new buffer for {speaker}")
        return self.buffers[speaker]
    
    async def _handle_speaker_change(
        self,
        new_speaker: str,
        timestamp: float
    ) -> Optional[CompleteUtterance]:
        """
        Handle speaker change by finalizing other speakers' buffers.
        
        When a new speaker starts talking, any accumulated buffer from
        other speakers is finalized as complete (speaker_change reason).
        
        Args:
            new_speaker: The speaker who is now talking
            timestamp: Current timestamp
        
        Returns:
            CompleteUtterance from the previous speaker if any, None otherwise
        """
        completed = None
        
        for speaker, buffer in list(self.buffers.items()):
            if speaker != new_speaker and not buffer.is_empty:
                self._logger.info(
                    f"Speaker changed from {speaker} to {new_speaker}, "
                    f"finalizing: '{buffer.text[:80]}...'"
                )
                completed = self._finalize_buffer(
                    buffer,
                    CompletionReason.SPEAKER_CHANGE,
                    0.85,
                    DetectionTier.SPEAKER_CHANGE,
                )
                buffer.reset()
        
        return completed
    
    def _finalize_buffer(
        self,
        buffer: SpeakerBuffer,
        reason: CompletionReason,
        confidence: float,
        tier: DetectionTier,
        is_partial: bool = False,
    ) -> CompleteUtterance:
        """
        Create CompleteUtterance from buffer contents.
        
        Args:
            buffer: SpeakerBuffer to finalize
            reason: CompletionReason enum value
            confidence: Confidence score (0.0-1.0)
            tier: DetectionTier that determined completion
            is_partial: Whether forced before natural completion
        
        Returns:
            CompleteUtterance with buffer data
        """
        return CompleteUtterance.from_buffer(
            buffer=buffer,
            completion_reason=f"{reason.value}: {tier.value}",
            confidence=confidence,
            tier_used=tier.value,
            is_partial=is_partial,
        )
    
    def _check_hard_timeout(self, buffer: SpeakerBuffer, now: float) -> bool:
        """
        Check if buffer has exceeded hard timeout.
        
        Hard timeout is the maximum time from first segment. If exceeded,
        the buffer should be force-completed to guarantee response.
        
        Args:
            buffer: SpeakerBuffer to check
            now: Current timestamp
        
        Returns:
            True if hard timeout exceeded, False otherwise
        """
        if buffer.is_empty or buffer.first_segment_time == 0.0:
            return False
        
        duration_ms = (now - buffer.first_segment_time) * 1000
        return duration_ms >= self.config.hard_timeout_ms
    
    def _check_buffer_limit(self, buffer: SpeakerBuffer) -> bool:
        """
        Check if buffer has exceeded character limit.
        
        If the buffer contains more characters than max_characters,
        it should be force-completed to prevent runaway accumulation.
        
        Args:
            buffer: SpeakerBuffer to check
        
        Returns:
            True if character limit exceeded, False otherwise
        """
        return buffer.total_characters >= self.config.max_characters
    
    def _reason_from_tier(self, tier_string: str) -> CompletionReason:
        """
        Map tier string to CompletionReason enum.
        
        Args:
            tier_string: Tier identifier string
        
        Returns:
            Appropriate CompletionReason
        """
        if "punctuation" in tier_string.lower():
            return CompletionReason.PUNCTUATION
        elif "syntax" in tier_string.lower():
            return CompletionReason.SYNTAX
        elif "timing" in tier_string.lower():
            return CompletionReason.TIMEOUT
        elif "llm" in tier_string.lower():
            return CompletionReason.SYNTAX  # LLM determines syntax/semantic
        elif "speaker" in tier_string.lower():
            return CompletionReason.SPEAKER_CHANGE
        elif "limit" in tier_string.lower():
            return CompletionReason.LIMIT
        elif "forced" in tier_string.lower():
            return CompletionReason.FORCED
        else:
            return CompletionReason.FORCED
    
    def _tier_from_string(self, tier_string: str) -> DetectionTier:
        """
        Convert tier string to DetectionTier enum.
        
        Args:
            tier_string: Tier identifier string from CompletenessResult
        
        Returns:
            Corresponding DetectionTier enum value
        """
        try:
            # Try direct enum value match first
            return DetectionTier(tier_string)
        except ValueError:
            # Fallback to fuzzy matching
            tier_lower = tier_string.lower()
            if "tier1" in tier_lower or "punctuation" in tier_lower:
                return DetectionTier.TIER1_PUNCTUATION
            elif "tier2" in tier_lower or "syntax" in tier_lower:
                return DetectionTier.TIER2_SYNTAX
            elif "tier3" in tier_lower or "timing" in tier_lower:
                return DetectionTier.TIER3_TIMING
            elif "tier4" in tier_lower or "llm" in tier_lower:
                return DetectionTier.TIER4_LLM
            elif "speaker" in tier_lower:
                return DetectionTier.SPEAKER_CHANGE
            elif "limit" in tier_lower:
                return DetectionTier.LIMIT
            elif "error" in tier_lower:
                return DetectionTier.ERROR
            else:
                return DetectionTier.FORCED
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current accumulator state.
        
        Useful for debugging and monitoring.
        
        Returns:
            Dict with buffer counts, sizes, and configuration status
        """
        buffer_stats = {}
        for speaker, buffer in self.buffers.items():
            buffer_stats[speaker] = {
                "segment_count": buffer.segment_count,
                "total_characters": buffer.total_characters,
                "duration_s": buffer.duration_s,
                "is_empty": buffer.is_empty,
                "text_preview": self.get_buffer_preview(speaker, 50),
            }
        
        return {
            "enabled": self.config.enabled,
            "buffer_count": len(self.buffers),
            "buffers": buffer_stats,
            "config": self.config.to_dict(),
        }
