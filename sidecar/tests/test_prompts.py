"""
Tests for the enhanced prompts module.

Tests question classification, prompt building, and context formatting.
"""

import pytest
from src.providers.llm.prompts import (
    classify_question,
    build_system_prompt,
    format_context_for_prompt,
    MASTER_SYSTEM_PROMPT,
    BEHAVIORAL_ADDON,
    INTRO_ADDON,
    WEAKNESS_ADDON,
    MOTIVATION_ADDON,
    TECHNICAL_ADDON,
)


class TestClassifyQuestion:
    """Tests for the question classification function."""

    @pytest.mark.parametrize("question,expected", [
        # Behavioral questions
        ("Tell me about a time you solved a difficult problem", "behavioral"),
        ("Describe a situation where you had to lead a team", "behavioral"),
        ("Give me an example of when you resolved a conflict", "behavioral"),
        ("Walk me through a time when you failed", "behavioral"),
        ("How did you handle a challenging deadline?", "behavioral"),
        ("Have you ever had to deal with a difficult coworker?", "behavioral"),
        
        # Intro questions
        ("Tell me about yourself", "intro"),
        ("Walk me through your background", "intro"),
        ("Introduce yourself", "intro"),
        ("Who are you?", "intro"),
        ("What's your background?", "intro"),
        
        # Weakness questions
        ("What is your greatest weakness?", "weakness"),
        ("What areas do you need to improve?", "weakness"),
        ("What are your shortcomings?", "weakness"),
        ("What would you improve about yourself?", "weakness"),
        
        # Motivation questions
        ("Why do you want to work here?", "motivation"),
        ("Why are you interested in this role?", "motivation"),
        ("What attracts you to this company?", "motivation"),
        ("Why should we hire you?", "motivation"),
        
        # Technical questions
        ("How would you design a caching system?", "technical"),
        ("Explain how REST APIs work", "technical"),
        ("What is the difference between SQL and NoSQL?", "technical"),
        ("How do you debug a production issue?", "technical"),
        
        # General/fallback
        ("What is your salary expectation?", "general"),
        ("When can you start?", "general"),
        ("Do you have any questions for us?", "general"),
    ])
    def test_classify_question(self, question: str, expected: str):
        """Test that questions are classified correctly."""
        assert classify_question(question) == expected

    def test_empty_question_returns_general(self):
        """Test that empty questions return 'general'."""
        assert classify_question("") == "general"
        assert classify_question("   ") == "general"

    def test_case_insensitive(self):
        """Test that classification is case-insensitive."""
        assert classify_question("TELL ME ABOUT YOURSELF") == "intro"
        assert classify_question("Tell Me About Yourself") == "intro"


class TestBuildSystemPrompt:
    """Tests for the system prompt builder."""

    def test_returns_tuple(self):
        """Test that build_system_prompt returns a tuple."""
        result = build_system_prompt("Tell me about yourself")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_behavioral_question_includes_star(self):
        """Test that behavioral questions include STAR method."""
        prompt, qtype = build_system_prompt("Tell me about a time you led a project")
        assert qtype == "behavioral"
        assert "STAR" in prompt
        assert "SITUATION" in prompt
        assert "TASK" in prompt
        assert "ACTION" in prompt
        assert "RESULT" in prompt

    def test_intro_question_includes_pitch_structure(self):
        """Test that intro questions include elevator pitch structure."""
        prompt, qtype = build_system_prompt("Tell me about yourself")
        assert qtype == "intro"
        assert "HEADLINE" in prompt
        assert "BACKGROUND" in prompt
        assert "CAREER HIGHLIGHTS" in prompt or "HIGHLIGHTS" in prompt

    def test_weakness_question_includes_growth_narrative(self):
        """Test that weakness questions include growth narrative."""
        prompt, qtype = build_system_prompt("What is your greatest weakness?")
        assert qtype == "weakness"
        # SHARE framework includes honest acknowledgment via HINDRANCE section
        assert "HINDRANCE" in prompt or "ACKNOWLEDGE" in prompt
        assert "EVALUATION" in prompt or "PROGRESS" in prompt

    def test_master_prompt_always_included(self):
        """Test that master prompt is always included."""
        for question in ["Tell me about yourself", "How do you design systems?", "What's your salary?"]:
            prompt, _ = build_system_prompt(question)
            assert "FIRST PERSON" in prompt or "first person" in prompt.lower()
            assert "Context" in prompt or "context" in prompt.lower()

    def test_examples_included_for_behavioral(self):
        """Test that behavioral questions include examples."""
        prompt, _ = build_system_prompt("Describe a situation where you led", include_examples=True)
        assert "Example" in prompt or "EXAMPLE" in prompt

    def test_examples_excluded_when_disabled(self):
        """Test that examples can be excluded."""
        prompt_with, _ = build_system_prompt("Tell me about yourself", include_examples=True)
        prompt_without, _ = build_system_prompt("Tell me about yourself", include_examples=False)
        assert len(prompt_with) > len(prompt_without)


class TestFormatContextForPrompt:
    """Tests for context formatting."""

    def test_empty_context_returns_empty(self):
        """Test that empty context returns empty string."""
        assert format_context_for_prompt("", "behavioral") == ""
        assert format_context_for_prompt("   ", "behavioral") == ""

    def test_behavioral_context_header(self):
        """Test that behavioral questions get experience header."""
        result = format_context_for_prompt("Some experience info", "behavioral")
        assert "EXPERIENCE" in result
        assert "STAR" in result

    def test_intro_context_header(self):
        """Test that intro questions get background header."""
        result = format_context_for_prompt("Some background info", "intro")
        assert "BACKGROUND" in result

    def test_technical_context_header(self):
        """Test that technical questions get technical header."""
        result = format_context_for_prompt("Some technical info", "technical")
        assert "TECHNICAL" in result

    def test_context_content_preserved(self):
        """Test that context content is preserved."""
        content = "I worked at Google for 5 years on distributed systems."
        result = format_context_for_prompt(content, "behavioral")
        assert content in result


class TestPromptQuality:
    """Tests for overall prompt quality requirements."""

    def test_master_prompt_has_conversational_instructions(self):
        """Test that master prompt includes conversational style."""
        assert "contraction" in MASTER_SYSTEM_PROMPT.lower()
        assert "natural" in MASTER_SYSTEM_PROMPT.lower()

    def test_master_prompt_has_grounding_rules(self):
        """Test that master prompt includes grounding rules."""
        assert "NEVER invent" in MASTER_SYSTEM_PROMPT or "never invent" in MASTER_SYSTEM_PROMPT.lower()
        assert "Context" in MASTER_SYSTEM_PROMPT

    def test_master_prompt_forbids_common_ai_phrases(self):
        """Test that master prompt forbids robotic phrases."""
        prompt_lower = MASTER_SYSTEM_PROMPT.lower()
        assert "great question" in prompt_lower  # Should be mentioned as forbidden
        
    def test_behavioral_addon_has_timing_guidance(self):
        """Test that STAR addon includes timing percentages."""
        assert "15%" in BEHAVIORAL_ADDON or "60%" in BEHAVIORAL_ADDON

    def test_prompts_are_reasonable_length(self):
        """Test that prompts aren't excessively long.
        
        Note: Master prompt was expanded in Phase 9 to include comprehensive
        grounding rules, source priority hierarchy, and anti-hallucination
        instructions. The increased length (~5000 chars / ~1200 tokens) is
        justified for improved context utilization accuracy.
        """
        # Master prompt should be under 5500 chars (includes enhanced grounding rules)
        assert len(MASTER_SYSTEM_PROMPT) < 5500
        
        # Full prompt with addon should be under 8500 chars
        full_prompt, _ = build_system_prompt("Tell me about a time you solved a problem")
        assert len(full_prompt) < 8500
