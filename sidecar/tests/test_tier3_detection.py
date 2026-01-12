"""
Tests for Tier 3 Question Detection (STORY-063).

Tests:
1. Trigger conditions (confidence thresholds)
2. LLM integration (mocked)
3. Fallback logic
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from src.classification.question_detector import QuestionDetector

@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    mock = MagicMock()
    # Setup async generator for generate_response
    async def async_gen(*args, **kwargs):
        yield "QUESTION"
    mock.generate_response = MagicMock(side_effect=async_gen)
    return mock

@pytest.mark.asyncio
async def test_tier1_high_confidence(mock_llm_provider):
    """Test that high confidence regex matches skip Tier 3."""
    detector = QuestionDetector(llm_provider=mock_llm_provider)
    
    # "What is..." is a strong pattern (>0.80)
    is_q, conf, q_type = await detector.is_actionable_question_async("What is the difference between TCP and UDP?")
    
    assert is_q is True
    assert conf >= 0.80
    assert q_type == "interview_question"
    
    # Verify LLM was NOT called
    mock_llm_provider.generate_response.assert_not_called()

@pytest.mark.asyncio
async def test_tier3_trigger_condition(mock_llm_provider):
    """Test that ambiguous input triggers Tier 3 LLM verification."""
    detector = QuestionDetector(llm_provider=mock_llm_provider)
    
    # "So basically..." is a statement pattern (0.85) -> Wait, let's find something ambiguous.
    # "I see" is acknowledgment (0.95).
    # Default fallback is (False, 0.55, "statement").
    # If we have text that doesn't match patterns but looks substantive:
    # "The deployment failed yesterday" -> No pattern -> 0.55 confidence statement.
    # This falls into 0.4 <= result[1] < 0.75 range.
    
    text = "The system crashed when we scaled up."
    
    # Mock LLM to say it's NOT a question
    async def async_gen_not_question(*args, **kwargs):
        yield "NOT_QUESTION"
    mock_llm_provider.generate_response = MagicMock(side_effect=async_gen_not_question)
    
    is_q, conf, q_type = await detector.is_actionable_question_async(text)
    
    assert is_q is False
    assert conf == 0.85
    assert q_type == "statement"
    
    # Verify LLM WAS called
    mock_llm_provider.generate_response.assert_called_once()

@pytest.mark.asyncio
async def test_tier3_identifies_question(mock_llm_provider):
    """Test that Tier 3 correctly identifies a tricky question."""
    detector = QuestionDetector(llm_provider=mock_llm_provider)
    
    # "I'm wondering if you could explain that again" - might be missed or low confidence
    text = "I'm wondering if you could handle this differently."
    
    # Mock LLM to say it IS a question
    async def async_gen_question(*args, **kwargs):
        yield "QUESTION"
    mock_llm_provider.generate_response = MagicMock(side_effect=async_gen_question)
    
    is_q, conf, q_type = await detector.is_actionable_question_async(text)
    
    assert is_q is True
    assert conf == 0.85
    assert q_type == "interview_question"
    
    mock_llm_provider.generate_response.assert_called_once()

@pytest.mark.asyncio
async def test_tier3_skips_short_text(mock_llm_provider):
    """Test that Tier 3 is skipped for very short text."""
    detector = QuestionDetector(llm_provider=mock_llm_provider)
    
    text = "No way."  # Too short (< 3 words)
    
    is_q, conf, q_type = await detector.is_actionable_question_async(text)
    
    # Should use rule-based result
    assert is_q is False
    mock_llm_provider.generate_response.assert_not_called()

@pytest.mark.asyncio
async def test_tier3_skips_without_llm():
    """Test that Tier 3 is skipped if no LLM provider is set."""
    detector = QuestionDetector(llm_provider=None)
    
    text = "The system crashed when we scaled up."
    
    is_q, conf, q_type = await detector.is_actionable_question_async(text)
    
    # Should return low confidence statement
    assert is_q is False
    assert conf == 0.55  # Default fallback confidence
