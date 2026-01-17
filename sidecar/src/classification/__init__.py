"""
Classification module for interview utterances.

This module provides intelligent detection and classification of interview
utterances to determine what requires a response vs. what should be ignored.

Components:
- QuestionDetector: Multi-tier question classification
- QueryReformulator: Follow-up question expansion
- QuestionSplitter: Compound question decomposition
- UtteranceAccumulator: Segment accumulation until complete
- CompletenessDetector: Multi-tier utterance completeness detection
"""

from .question_detector import QuestionDetector
from .query_reformulator import QueryReformulator
from .question_splitter import QuestionSplitter
from .utterance_accumulator import UtteranceAccumulator
from .completeness_detector import CompletenessDetector
from .accumulator_models import (
    AccumulatorConfig,
    SpeakerBuffer,
    CompleteUtterance,
    CompletenessResult,
    CompletionReason,
    DetectionTier,
)

__all__ = [
    "QuestionDetector",
    "QueryReformulator",
    "QuestionSplitter",
    "UtteranceAccumulator",
    "CompletenessDetector",
    "AccumulatorConfig",
    "SpeakerBuffer",
    "CompleteUtterance",
    "CompletenessResult",
    "CompletionReason",
    "DetectionTier",
]
