"""
Evaluation module for RAG quality assessment.

Provides RAGAS-style metrics for measuring context utilization,
answer groundedness, and faithfulness.
"""

from .groundedness import (
    GroundednessEvaluator,
    GroundednessResult,
    ContextUtilizationResult,
)
from .context_tracker import ContextUsageTracker, ChunkUsageRecord

__all__ = [
    "GroundednessEvaluator",
    "GroundednessResult",
    "ContextUtilizationResult",
    "ContextUsageTracker",
    "ChunkUsageRecord",
]
