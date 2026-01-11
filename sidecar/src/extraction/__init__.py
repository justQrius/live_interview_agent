"""
Extraction Module - Document processing for persistent memory.

This module provides:
- Document summarization (hierarchical)
- Fact extraction (structured data)
- STAR story extraction
- Candidate profile generation

Part of Phase 4: Interview Coach Evolution
"""

from .summarizer import DocumentSummarizer
from .fact_extractor import FactExtractor
from .story_extractor import StoryExtractor

__all__ = [
    "DocumentSummarizer",
    "FactExtractor",
    "StoryExtractor",
]
