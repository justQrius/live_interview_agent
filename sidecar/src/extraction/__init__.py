"""
Extraction Module - Document processing for persistent memory.

This module provides:
- Document summarization (hierarchical)
- Fact extraction (structured data)
- STAR story extraction
- Candidate profile generation
- Extraction pipeline orchestration

Part of Phase 4: Interview Coach Evolution
"""

from .summarizer import DocumentSummarizer
from .fact_extractor import FactExtractor
from .story_extractor import StoryExtractor
from .profile_generator import ProfileGenerator
from .pipeline import ExtractionPipeline, ExtractionResult

__all__ = [
    "DocumentSummarizer",
    "FactExtractor",
    "StoryExtractor",
    "ProfileGenerator",
    "ExtractionPipeline",
    "ExtractionResult",
]
