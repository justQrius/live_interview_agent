"""
Data models for the Utterance Accumulator.

These models define the configuration, buffer state, and output types for
the utterance accumulation system, which buffers transcription segments
from the same speaker until the utterance is semantically complete.

Classes:
    AccumulatorConfig: Configuration for accumulation behavior
    SpeakerBuffer: Buffer state for a speaker's ongoing utterance
    CompleteUtterance: Finalized utterance ready for question detection
    CompletenessResult: Result from completeness detection
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class CompletionReason(str, Enum):
    """Reasons why an utterance was marked complete."""
    PUNCTUATION = "punctuation"
    SYNTAX = "syntax"
    TIMEOUT = "timeout"
    FORCED = "forced"
    SPEAKER_CHANGE = "speaker_change"
    LIMIT = "limit"
    DISABLED = "disabled"


class DetectionTier(str, Enum):
    """Tiers of completeness detection."""
    TIER1_PUNCTUATION = "tier1_punctuation"
    TIER2_SYNTAX = "tier2_syntax"
    TIER3_TIMING = "tier3_timing"
    TIER4_LLM = "tier4_llm"
    FORCED = "forced"
    SPEAKER_CHANGE = "speaker_change"
    LIMIT = "limit"
    INCOMPLETE_MARKER = "incomplete_marker"
    NONTERMINAL = "nonterminal"
    EMPTY = "empty"
    NONE = "none"
    ERROR = "tier4_error"


@dataclass
class AccumulatorConfig:
    """
    Configuration for utterance accumulation behavior.

    Controls timing thresholds, buffer limits, detection thresholds,
    and feature flags for the accumulation system.

    Attributes:
        merge_gap_ms: Segments less than this apart merge automatically (default: 500ms)
        soft_timeout_ms: Pause duration suggesting completion (default: 2000ms)
        hard_timeout_ms: Maximum wait time from first segment (default: 5000ms)
        max_tokens: Maximum buffer size in tokens (approximate) (default: 500)
        max_characters: Maximum buffer size in characters (default: 2000)
        max_duration_s: Maximum time from first segment in seconds (default: 30.0)
        tier1_confidence: Confidence threshold for punctuation-based completion (default: 0.90)
        tier2_confidence: Confidence threshold for syntactic completion (default: 0.80)
        tier3_confidence: Confidence threshold for timing-based completion (default: 0.75)
        llm_fallback_threshold: Below this confidence, invoke Tier 4 LLM (default: 0.70)
        enabled: Global enable/disable for accumulation (default: True)
        use_llm_fallback: Enable Tier 4 LLM detection (default: True)
        emit_accumulating_status: Send ACCUMULATING status to UI (default: True)
    """

    # Timing thresholds (milliseconds)
    merge_gap_ms: int = 500
    soft_timeout_ms: int = 2000
    hard_timeout_ms: int = 5000

    # Buffer limits
    max_tokens: int = 500
    max_characters: int = 2000
    max_duration_s: float = 30.0

    # Completeness detection thresholds
    tier1_confidence: float = 0.90
    tier2_confidence: float = 0.80
    tier3_confidence: float = 0.75
    llm_fallback_threshold: float = 0.70

    # Feature flags
    enabled: bool = True
    use_llm_fallback: bool = True
    emit_accumulating_status: bool = True

    @classmethod
    def from_env(cls) -> "AccumulatorConfig":
        """
        Create AccumulatorConfig from environment variables.

        Environment variables (with defaults):
            ACCUMULATOR_ENABLED: "true" (default) / "false"
            ACCUMULATOR_MERGE_GAP_MS: 500
            ACCUMULATOR_SOFT_TIMEOUT_MS: 2000
            ACCUMULATOR_HARD_TIMEOUT_MS: 5000
            ACCUMULATOR_MAX_TOKENS: 500
            ACCUMULATOR_MAX_CHARACTERS: 2000
            ACCUMULATOR_MAX_DURATION_S: 30.0
            ACCUMULATOR_TIER1_CONFIDENCE: 0.90
            ACCUMULATOR_TIER2_CONFIDENCE: 0.80
            ACCUMULATOR_TIER3_CONFIDENCE: 0.75
            ACCUMULATOR_LLM_FALLBACK_THRESHOLD: 0.70
            ACCUMULATOR_USE_LLM_FALLBACK: "true" (default) / "false"
            ACCUMULATOR_EMIT_STATUS: "true" (default) / "false"

        Returns:
            AccumulatorConfig instance with values from environment
        """

        def get_bool(key: str, default: bool) -> bool:
            value = os.getenv(key, str(default).lower())
            return value.lower() in ("true", "1", "yes", "on")

        def get_int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except (ValueError, TypeError):
                return default

        def get_float(key: str, default: float) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except (ValueError, TypeError):
                return default

        return cls(
            merge_gap_ms=get_int("ACCUMULATOR_MERGE_GAP_MS", 500),
            soft_timeout_ms=get_int("ACCUMULATOR_SOFT_TIMEOUT_MS", 2000),
            hard_timeout_ms=get_int("ACCUMULATOR_HARD_TIMEOUT_MS", 5000),
            max_tokens=get_int("ACCUMULATOR_MAX_TOKENS", 500),
            max_characters=get_int("ACCUMULATOR_MAX_CHARACTERS", 2000),
            max_duration_s=get_float("ACCUMULATOR_MAX_DURATION_S", 30.0),
            tier1_confidence=get_float("ACCUMULATOR_TIER1_CONFIDENCE", 0.90),
            tier2_confidence=get_float("ACCUMULATOR_TIER2_CONFIDENCE", 0.80),
            tier3_confidence=get_float("ACCUMULATOR_TIER3_CONFIDENCE", 0.75),
            llm_fallback_threshold=get_float("ACCUMULATOR_LLM_FALLBACK_THRESHOLD", 0.70),
            enabled=get_bool("ACCUMULATOR_ENABLED", True),
            use_llm_fallback=get_bool("ACCUMULATOR_USE_LLM_FALLBACK", True),
            emit_accumulating_status=get_bool("ACCUMULATOR_EMIT_STATUS", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "merge_gap_ms": self.merge_gap_ms,
            "soft_timeout_ms": self.soft_timeout_ms,
            "hard_timeout_ms": self.hard_timeout_ms,
            "max_tokens": self.max_tokens,
            "max_characters": self.max_characters,
            "max_duration_s": self.max_duration_s,
            "tier1_confidence": self.tier1_confidence,
            "tier2_confidence": self.tier2_confidence,
            "tier3_confidence": self.tier3_confidence,
            "llm_fallback_threshold": self.llm_fallback_threshold,
            "enabled": self.enabled,
            "use_llm_fallback": self.use_llm_fallback,
            "emit_accumulating_status": self.emit_accumulating_status,
        }


@dataclass
class SpeakerBuffer:
    """
    Buffer state for a single speaker's ongoing utterance.

    Tracks accumulated text segments, timestamps, and provides
    utility properties and methods for buffer management.

    Attributes:
        speaker: Speaker identifier (e.g., "Interviewer", "User")
        segments: List of accumulated text segments
        first_segment_time: Timestamp of first segment (seconds since epoch)
        last_segment_time: Timestamp of most recent segment (seconds since epoch)
        total_characters: Running count of total characters in buffer
    """

    speaker: str
    segments: List[str] = field(default_factory=list)
    first_segment_time: float = 0.0
    last_segment_time: float = 0.0
    total_characters: int = 0

    @property
    def text(self) -> str:
        """
        Return accumulated text with proper spacing.

        Joins all segments with single space separators.

        Returns:
            Full accumulated text as a single string
        """
        return " ".join(self.segments)

    @property
    def duration_s(self) -> float:
        """
        Return duration since first segment in seconds.

        Returns:
            Duration from first to last segment in seconds,
            or 0.0 if no segments have been added
        """
        if self.first_segment_time == 0.0:
            return 0.0
        return self.last_segment_time - self.first_segment_time

    @property
    def is_empty(self) -> bool:
        """
        Return True if buffer has no segments.

        Returns:
            True if no segments have been added, False otherwise
        """
        return len(self.segments) == 0

    @property
    def segment_count(self) -> int:
        """
        Return the number of segments in the buffer.

        Returns:
            Count of text segments accumulated
        """
        return len(self.segments)

    def append(self, text: str, timestamp: float) -> None:
        """
        Append a new segment to the buffer.

        Updates first_segment_time on first append, and always updates
        last_segment_time and total_characters.

        Args:
            text: Transcribed text segment to append
            timestamp: Timestamp of the segment (seconds since epoch)
        """
        if self.first_segment_time == 0.0:
            self.first_segment_time = timestamp
        self.segments.append(text)
        self.last_segment_time = timestamp
        self.total_characters += len(text)

    def reset(self) -> None:
        """
        Clear the buffer for a new utterance.

        Resets all state: segments, timestamps, and character count.
        The speaker identifier is preserved.
        """
        self.segments = []
        self.first_segment_time = 0.0
        self.last_segment_time = 0.0
        self.total_characters = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert buffer state to dictionary for serialization."""
        return {
            "speaker": self.speaker,
            "segments": self.segments,
            "first_segment_time": self.first_segment_time,
            "last_segment_time": self.last_segment_time,
            "total_characters": self.total_characters,
            "text": self.text,
            "duration_s": self.duration_s,
            "is_empty": self.is_empty,
            "segment_count": self.segment_count,
        }


@dataclass
class CompleteUtterance:
    """
    A finalized, complete utterance ready for question detection.

    Represents the output of the accumulation process when an utterance
    is deemed complete (by any detection tier or timeout).

    Attributes:
        text: Full accumulated text
        speaker: Speaker identifier
        start_time: When utterance started (seconds since epoch)
        end_time: When utterance completed (seconds since epoch)
        segment_count: Number of VAD segments accumulated
        completion_reason: Why deemed complete (punctuation, syntax, timeout, forced, speaker_change)
        confidence: Completeness confidence score (0.0-1.0)
        tier_used: Which detection tier determined completeness
        is_partial: True if forced by timeout before natural completion
    """

    text: str
    speaker: str
    start_time: float
    end_time: float
    segment_count: int
    completion_reason: str
    confidence: float
    tier_used: str
    is_partial: bool = False

    @property
    def duration_s(self) -> float:
        """
        Return total utterance duration in seconds.

        Returns:
            Duration from start to end of utterance in seconds
        """
        return self.end_time - self.start_time

    @property
    def word_count(self) -> int:
        """
        Return approximate word count of the utterance.

        Returns:
            Number of whitespace-separated tokens in text
        """
        return len(self.text.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert utterance to dictionary for serialization."""
        return {
            "text": self.text,
            "speaker": self.speaker,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "segment_count": self.segment_count,
            "completion_reason": self.completion_reason,
            "confidence": self.confidence,
            "tier_used": self.tier_used,
            "is_partial": self.is_partial,
            "duration_s": self.duration_s,
            "word_count": self.word_count,
        }

    @classmethod
    def from_buffer(
        cls,
        buffer: SpeakerBuffer,
        completion_reason: str,
        confidence: float,
        tier_used: str,
        is_partial: bool = False,
    ) -> "CompleteUtterance":
        """
        Create a CompleteUtterance from a SpeakerBuffer.

        Factory method to convert a buffer to a finalized utterance.

        Args:
            buffer: The SpeakerBuffer containing accumulated segments
            completion_reason: Human-readable reason for completion
            confidence: Completeness confidence score (0.0-1.0)
            tier_used: Detection tier that made the decision
            is_partial: Whether forced before natural completion

        Returns:
            CompleteUtterance instance with buffer data
        """
        return cls(
            text=buffer.text,
            speaker=buffer.speaker,
            start_time=buffer.first_segment_time,
            end_time=buffer.last_segment_time,
            segment_count=buffer.segment_count,
            completion_reason=completion_reason,
            confidence=confidence,
            tier_used=tier_used,
            is_partial=is_partial,
        )


@dataclass
class CompletenessResult:
    """
    Result from completeness detection.

    Returned by the CompletenessDetector to indicate whether an utterance
    is complete and which tier made the determination.

    Attributes:
        is_complete: Whether the utterance is complete
        confidence: Confidence score (0.0-1.0)
        tier_used: Which detection tier made the decision
            (tier1_punctuation, tier2_syntax, tier3_timing, tier4_llm,
             incomplete_marker, nonterminal, forced, speaker_change, limit)
        reason: Human-readable reason for the decision
        should_wait: True if incomplete markers detected (defer completion)
        wait_reason: Explanation for why we're waiting (e.g., "trailing ellipsis")
    """

    is_complete: bool
    confidence: float
    tier_used: str
    reason: str
    should_wait: bool = False
    wait_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "is_complete": self.is_complete,
            "confidence": self.confidence,
            "tier_used": self.tier_used,
            "reason": self.reason,
            "should_wait": self.should_wait,
            "wait_reason": self.wait_reason,
        }

    @classmethod
    def complete(
        cls,
        confidence: float,
        tier: str,
        reason: str,
    ) -> "CompletenessResult":
        """
        Factory method for creating a complete result.

        Args:
            confidence: Confidence score (0.0-1.0)
            tier: Detection tier identifier
            reason: Human-readable reason

        Returns:
            CompletenessResult with is_complete=True
        """
        return cls(
            is_complete=True,
            confidence=confidence,
            tier_used=tier,
            reason=reason,
        )

    @classmethod
    def incomplete(
        cls,
        confidence: float,
        tier: str,
        reason: str,
        should_wait: bool = False,
        wait_reason: Optional[str] = None,
    ) -> "CompletenessResult":
        """
        Factory method for creating an incomplete result.

        Args:
            confidence: Confidence score (0.0-1.0)
            tier: Detection tier identifier
            reason: Human-readable reason
            should_wait: True if incomplete markers detected
            wait_reason: Explanation for waiting

        Returns:
            CompletenessResult with is_complete=False
        """
        return cls(
            is_complete=False,
            confidence=confidence,
            tier_used=tier,
            reason=reason,
            should_wait=should_wait,
            wait_reason=wait_reason,
        )
