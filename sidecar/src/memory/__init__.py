"""
Memory Store Module - Persistent memory for candidate context.

This module provides:
- SQLite-based storage for extracted facts, stories, and profiles
- Data models for structured candidate information
- CRUD operations for memory management
- Session claim tracking for consistency

Part of Phase 4: Interview Coach Evolution
"""

from .models import (
    ExtractedFacts,
    SkillEntry,
    CareerEntry,
    Achievement,
    Education,
    STARStory,
    CandidateProfile,
    SessionClaim,
    DocumentSummary,
)
from .store import MemoryStore

__all__ = [
    # Data Models
    "ExtractedFacts",
    "SkillEntry",
    "CareerEntry",
    "Achievement",
    "Education",
    "STARStory",
    "CandidateProfile",
    "SessionClaim",
    "DocumentSummary",
    # Store
    "MemoryStore",
]
