"""
Tests for Structure Suggester (STORY-067).

Tests mapping of question types to answer frameworks.
"""

import pytest
from src.coaching.structure_suggester import StructureSuggester, StructureHint

def test_behavioral_detection():
    """Test detection of behavioral questions."""
    suggester = StructureSuggester()
    
    assert suggester._detect_subtype("Tell me about a time you failed", "interview_question") == "behavioral"
    assert suggester._detect_subtype("Give me an example of conflict", "interview_question") == "behavioral"
    assert suggester._detect_subtype("Walk me through your resume", "interview_question") == "behavioral"

def test_technical_detection():
    """Test detection of technical questions."""
    suggester = StructureSuggester()
    
    assert suggester._detect_subtype("How would you design a rate limiter?", "interview_question") == "technical"
    assert suggester._detect_subtype("Explain the CAP theorem", "interview_question") == "technical"
    assert suggester._detect_subtype("What is the difference between TCP and UDP?", "interview_question") == "technical"

def test_motivation_detection():
    """Test detection of motivation questions."""
    suggester = StructureSuggester()
    
    assert suggester._detect_subtype("Why do you want to work here?", "interview_question") == "motivation"
    assert suggester._detect_subtype("Where do you see yourself in five years?", "interview_question") == "motivation"

def test_structure_mapping():
    """Test that correct structure is returned for type."""
    suggester = StructureSuggester()
    
    hint = suggester.suggest_structure("Tell me about a time...", "interview_question")
    assert hint.name == "STAR Method"
    assert len(hint.sections) == 4
    assert hint.sections[0].name == "Situation"
    
    hint = suggester.suggest_structure("Design Twitter", "interview_question")
    assert hint.name == "Concept-Example-Tradeoff"
    
    hint = suggester.suggest_structure("What's your favorite ice cream?", "interview_question")
    assert hint.name == "Direct-Support-Close"  # Fallback to general

def test_structure_hint_serialization():
    """Test to_dict method."""
    suggester = StructureSuggester()
    hint = suggester.suggest_structure("Tell me about a time...", "interview_question")
    
    data = hint.to_dict()
    assert data["name"] == "STAR Method"
    assert isinstance(data["sections"], list)
    assert isinstance(data["tips"], list)
    assert data["sections"][0]["name"] == "Situation"
    assert data["sections"][0]["percentage"] == "15%"
