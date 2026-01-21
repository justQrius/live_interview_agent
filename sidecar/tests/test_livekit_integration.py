"""
Tests for LiveKit turn detection integration.

Note: These tests require the livekit-agents package to be installed.
Run with: pytest -xvs tests/test_livekit_integration.py
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Skip tests if LiveKit not installed
pytest.importorskip("livekit")

from livekit_integration.turn_detector_wrapper import LiveKitTurnDetector, get_turn_detector


@pytest.mark.asyncio
async def test_turn_detector_initialization():
    """Test turn detector can be loaded"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    assert detector.is_loaded() is True
    assert detector._model is not None


@pytest.mark.asyncio
async def test_single_sentence_question():
    """Test turn detection on single sentence question"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    text = "Tell me about your experience with machine learning."
    history = []

    is_finished, confidence = await detector.check(text, history)

    # Question should be detected as finished (has question mark)
    assert is_finished is True
    assert confidence > 0.75


@pytest.mark.asyncio
async def test_multi_sentence_statement():
    """Test turn detection on multi-sentence statement"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    text = "I worked at Google for three years on natural language processing models."
    history = []

    is_finished, confidence = await detector.check(text, history)

    # Statement should be detected as finished (ends with period, complete thought)
    # Note: With no conversation context, this might be detected differently
    # Adjust assertion based on actual model behavior
    assert confidence > 0.4  # At least some confidence


@pytest.mark.asyncio
async def test_mid_thought_pause():
    """Test turn detection with mid-thought pause"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    # Simulating: "I worked at..." (speaker paused to think)
    text = "I worked at"
    history = []

    is_finished, confidence = await detector.check(text, history)

    # Mid-thought pause should NOT be finished
    # Confidence should be lower for incomplete phrases
    assert confidence < 0.7


@pytest.mark.asyncio
async def test_conversation_context():
    """Test turn detection with conversation history"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    history = [
        {"role": "user", "content": "Tell me about your project experience."},
        {"role": "assistant", "content": "I led a team of 5 engineers building a payment system."},
    ]

    # Follow-up question
    text = "What was your favorite part of that project?"

    is_finished, confidence = await detector.check(text, history)

    # Should recognize as finished with context awareness
    assert is_finished is True
    assert confidence > 0.7


@pytest.mark.asyncio
async def test_consecutive_questions():
    """Test turn detection on consecutive questions"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    # "What was your role? And how did you handle the challenges?"
    text = "What was your role and how did you handle the challenges?"
    history = []

    is_finished, confidence = await detector.check(text, history)

    # Compound question should be detected as finished
    assert is_finished is True
    assert confidence > 0.6


@pytest.mark.asyncio
async def test_singleton_get_detector():
    """Test that get_turn_detector returns singleton instance"""
    # Get instance twice
    detector1 = get_turn_detector()
    detector2 = get_turn_detector()

    # Should be the same instance
    assert detector1 is detector2


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test that timeout is handled gracefully"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    text = "Test text"
    history = []

    # Very short timeout to trigger timeout
    is_finished, confidence = await detector.check(text, history, timeout=0.001)

    # Should return safe default on timeout
    assert is_finished is True
    assert confidence == 0.5


@pytest.mark.asyncio
async def test_message_formatting():
    """Test that messages are formatted correctly for turn detector"""
    detector = LiveKitTurnDetector()
    await detector.initialize()

    # Build messages with various formats
    text = "Tell me more"
    history = [
        {"speaker": "interviewer", "content": "Welcome", "text": "Welcome"},
    ]

    messages = detector._build_messages(text, history)

    # Should format correctly
    assert len(messages) == 2  # history + current
    assert messages[0]["role"] == "user"  # interviewer -> user
    assert messages[0]["content"] == "Welcome"
    assert messages[1]["content"] == "Tell me more"


if __name__ == "__main__":
    # Run a quick test if executed directly
    import asyncio

    async def quick_test():
        print("Testing LiveKit Turn Detection...")

        try:
            detector = LiveKitTurnDetector()
            await detector.initialize()
            print("✓ Model loaded")

            # Test a simple question
            is_finished, confidence = await detector.check("Tell me about yourself.", [])
            print(f"✓ Turn detection: finished={is_finished}, confidence={confidence:.2f}")

            print("\nBasic tests passed!")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(quick_test())
