"""
Playbook Module - Interview preparation playbook generation.

This module provides:
- Interview question generation
- Answer drafting with STAR stories
- Competency mapping
- Playbook assembly and export

Part of Phase 4: Interview Coach Evolution
"""

from .question_generator import QuestionGenerator, PlaybookQuestion, QuestionCategory, AnswerFramework
from .answer_drafter import AnswerDrafter
from .competency_mapper import CompetencyMapper, CompetencyMapping, CompetencyReport, MatchStrength
from .assembler import PlaybookAssembler, Playbook, PositioningStatements, CheatSheet

__all__ = [
    # Question Generation
    "QuestionGenerator",
    "PlaybookQuestion",
    "QuestionCategory",
    "AnswerFramework",
    # Answer Drafting
    "AnswerDrafter",
    # Competency Mapping
    "CompetencyMapper",
    "CompetencyMapping",
    "CompetencyReport",
    "MatchStrength",
    # Assembly & Export
    "PlaybookAssembler",
    "Playbook",
    "PositioningStatements",
    "CheatSheet",
]
