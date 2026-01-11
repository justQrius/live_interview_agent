"""
Playbook Module - Interview preparation playbook generation.

This module provides:
- Interview question generation
- Answer drafting with STAR stories
- Competency mapping
- Playbook assembly and export

Part of Phase 4: Interview Coach Evolution
"""

from .question_generator import QuestionGenerator, PlaybookQuestion, QuestionCategory

__all__ = [
    "QuestionGenerator",
    "PlaybookQuestion",
    "QuestionCategory",
]
