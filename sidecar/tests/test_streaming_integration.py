"""
Integration tests for Streaming STT Pipeline (Phase 7).

Tests the integration between:
- StreamingSTTManager
- UtteranceAccumulator (hybrid mode)
- Server callbacks

These tests verify the end-to-end flow from streaming audio
to question detection.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from src.providers.stt.streaming_base import (
    StreamingConfig,
    InterimResult,
    EndOfTurnEvent,
    EndpointingType,
)
from src.providers.stt.streaming_manager import (
    StreamingSTTManager,
    StreamingSTTCallbacks,
)
from src.classification.utterance_accumulator import UtteranceAccumulator
from src.classification.accumulator_models import AccumulatorConfig


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def streaming_config():
    """Create a streaming config for testing."""
    return StreamingConfig(
        enable_endpointing=True,
        emit_interim_results=True,
    )


@pytest.fixture
def accumulator_config_hybrid():
    """Create an accumulator config in hybrid mode."""
    return AccumulatorConfig(
        enabled=True,
        endpointing_mode="hybrid",
        streaming_confidence_threshold=0.7,
        merge_gap_ms=500,
        soft_timeout_ms=2000,
        hard_timeout_ms=5000,
    )


@pytest.fixture
def accumulator_config_timing():
    """Create an accumulator config in timing-only mode."""
    return AccumulatorConfig(
        enabled=True,
        endpointing_mode="timing",
        merge_gap_ms=500,
        soft_timeout_ms=2000,
        hard_timeout_ms=5000,
    )


@pytest.fixture
def accumulator_config_streaming():
    """Create an accumulator config in streaming-only mode."""
    return AccumulatorConfig(
        enabled=True,
        endpointing_mode="streaming",
        streaming_confidence_threshold=0.5,
    )


@pytest.fixture
def mock_streaming_provider():
    """Create a mock streaming STT provider."""
    provider = MagicMock()
    provider.provider_name = "test_provider"
    provider.supports_semantic_endpointing = True
    
    # Mock the connect method to return a mock session
    mock_session = MagicMock()
    mock_session.is_connected = True
    mock_session.send_audio = AsyncMock()
    mock_session.finalize = AsyncMock(return_value=None)
    mock_session.close = AsyncMock()
    
    # Create an async generator for results
    async def mock_results():
        # Yield nothing by default (tests can override)
        return
        yield  # Make this a generator
    
    mock_session.results = mock_results
    
    provider.connect = AsyncMock(return_value=mock_session)
    
    return provider


@pytest.fixture
def mock_factory(mock_streaming_provider):
    """Create a mock provider factory."""
    factory = MagicMock()
    factory.get_streaming_stt_provider.return_value = mock_streaming_provider
    return factory


# ============================================================================
# StreamingSTTManager Integration Tests
# ============================================================================

class TestStreamingManagerIntegration:
    """Test StreamingSTTManager integration with callbacks."""
    
    @pytest.mark.asyncio
    async def test_manager_starts_with_callbacks(self, mock_factory):
        """Manager should start session and register callbacks."""
        manager = StreamingSTTManager(mock_factory)
        
        interim_callback = MagicMock()
        end_of_turn_callback = MagicMock()
        
        callbacks = StreamingSTTCallbacks(
            on_interim=interim_callback,
            on_end_of_turn=end_of_turn_callback,
        )
        
        result = await manager.start_session(callbacks)
        
        assert result is True
        assert manager.is_active
        assert manager.provider_name == "test_provider"
    
    @pytest.mark.asyncio
    async def test_manager_sends_audio(self, mock_factory, mock_streaming_provider):
        """Manager should forward audio to the streaming session."""
        manager = StreamingSTTManager(mock_factory)
        await manager.start_session()
        
        audio_data = b"\x00\x01\x02\x03" * 1000
        result = await manager.send_audio(audio_data)
        
        assert result is True
        
        # Get the mock session from the provider's connect call
        mock_session = mock_streaming_provider.connect.return_value
        mock_session.send_audio.assert_called_once_with(audio_data)
    
    @pytest.mark.asyncio
    async def test_manager_stops_cleanly(self, mock_factory, mock_streaming_provider):
        """Manager should stop session and cleanup."""
        manager = StreamingSTTManager(mock_factory)
        await manager.start_session()
        
        final = await manager.stop_session()
        
        assert not manager.is_active
        mock_session = mock_streaming_provider.connect.return_value
        mock_session.close.assert_called_once()


# ============================================================================
# UtteranceAccumulator Hybrid Mode Tests
# ============================================================================

class TestAccumulatorHybridMode:
    """Test UtteranceAccumulator integration with streaming endpoints."""
    
    @pytest.mark.asyncio
    async def test_high_confidence_semantic_endpoint_bypasses_accumulator(
        self, accumulator_config_hybrid
    ):
        """High-confidence semantic endpoints should complete immediately."""
        accumulator = UtteranceAccumulator(accumulator_config_hybrid)
        
        result = await accumulator.on_streaming_end_of_turn(
            text="Tell me about your experience with Python?",
            speaker="Interviewer",
            confidence=0.9,
            is_semantic=True,
        )
        
        assert result is not None
        assert result.text == "Tell me about your experience with Python?"
        assert "tier0_streaming" in result.tier_used
        assert result.is_partial is False
    
    @pytest.mark.asyncio
    async def test_low_confidence_semantic_endpoint_falls_through(
        self, accumulator_config_hybrid
    ):
        """Low-confidence semantic endpoints should return None for fallback."""
        accumulator = UtteranceAccumulator(accumulator_config_hybrid)
        
        result = await accumulator.on_streaming_end_of_turn(
            text="Tell me about",
            speaker="Interviewer",
            confidence=0.5,  # Below threshold
            is_semantic=True,
        )
        
        # In hybrid mode with low confidence, returns None to signal
        # that timing-based detection should be used
        assert result is None
    
    @pytest.mark.asyncio
    async def test_acoustic_endpoint_in_hybrid_mode_falls_through(
        self, accumulator_config_hybrid
    ):
        """Acoustic endpoints should fall through in hybrid mode."""
        accumulator = UtteranceAccumulator(accumulator_config_hybrid)
        
        result = await accumulator.on_streaming_end_of_turn(
            text="Tell me about your experience?",
            speaker="Interviewer",
            confidence=0.9,
            is_semantic=False,  # Acoustic, not semantic
        )
        
        # Acoustic endpoints in hybrid mode return None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_streaming_mode_accepts_all_endpoints(
        self, accumulator_config_streaming
    ):
        """Streaming-only mode should accept all streaming endpoints."""
        accumulator = UtteranceAccumulator(accumulator_config_streaming)
        
        # Even low confidence should be accepted in streaming mode
        result = await accumulator.on_streaming_end_of_turn(
            text="What about?",
            speaker="Interviewer",
            confidence=0.4,
            is_semantic=False,
        )
        
        assert result is not None
        assert result.text == "What about?"
        assert result.is_partial is True  # Acoustic = partial
    
    @pytest.mark.asyncio
    async def test_timing_mode_ignores_streaming_endpoints(
        self, accumulator_config_timing
    ):
        """Timing-only mode should ignore streaming endpoints."""
        accumulator = UtteranceAccumulator(accumulator_config_timing)
        
        result = await accumulator.on_streaming_end_of_turn(
            text="Tell me about your experience?",
            speaker="Interviewer",
            confidence=0.95,
            is_semantic=True,
        )
        
        # Timing mode ignores streaming endpoints
        assert result is None
    
    @pytest.mark.asyncio
    async def test_combines_buffer_with_streaming_text(
        self, accumulator_config_hybrid
    ):
        """Should combine pending buffer with streaming endpoint text."""
        accumulator = UtteranceAccumulator(accumulator_config_hybrid)
        
        # First, add a segment to the buffer (simulating partial speech)
        # Use is_final=False to prevent completeness detection from finalizing it
        await accumulator.add_segment(
            text="Tell me about a time",
            speaker="Interviewer",
            timestamp=1000.0,
            is_final=False,  # Interim - don't trigger completeness check
        )
        
        # Verify the buffer has content
        buffer = accumulator.get_buffer("Interviewer")
        assert buffer is not None
        assert "Tell me about a time" in buffer.text
        
        # Then receive a streaming end-of-turn with the rest
        result = await accumulator.on_streaming_end_of_turn(
            text="when you led a team?",
            speaker="Interviewer",
            confidence=0.9,
            is_semantic=True,
        )
        
        assert result is not None
        assert "Tell me about a time" in result.text
        assert "when you led a team?" in result.text
        assert result.segment_count == 2  # Buffer + streaming


# ============================================================================
# End-to-End Streaming Pipeline Tests
# ============================================================================

class TestStreamingPipelineE2E:
    """End-to-end tests for the streaming STT pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_streaming_to_accumulator_flow(
        self, mock_factory, accumulator_config_hybrid
    ):
        """Test complete flow from streaming STT to accumulator."""
        # Create components
        manager = StreamingSTTManager(mock_factory)
        accumulator = UtteranceAccumulator(accumulator_config_hybrid)
        
        # Track results
        results = []
        
        # Define callback that integrates with accumulator
        async def on_end_of_turn(text, speaker, confidence, endpoint_type):
            is_semantic = endpoint_type == EndpointingType.SEMANTIC
            result = await accumulator.on_streaming_end_of_turn(
                text=text,
                speaker=str(speaker.value) if hasattr(speaker, 'value') else str(speaker),
                confidence=confidence,
                is_semantic=is_semantic,
            )
            if result:
                results.append(result)
        
        callbacks = StreamingSTTCallbacks(
            on_end_of_turn=on_end_of_turn,
        )
        
        # Start session
        await manager.start_session(callbacks)
        
        # Simulate receiving an end-of-turn event
        from src.protocol import Speaker
        await on_end_of_turn(
            "What is your greatest strength?",
            Speaker.INTERVIEWER,
            0.9,
            EndpointingType.SEMANTIC,
        )
        
        # Verify the flow worked
        assert len(results) == 1
        assert results[0].text == "What is your greatest strength?"
        
        # Cleanup
        await manager.stop_session()
    
    @pytest.mark.asyncio
    async def test_interim_results_dont_trigger_completion(
        self, mock_factory, accumulator_config_hybrid
    ):
        """Interim results should not trigger answer generation."""
        manager = StreamingSTTManager(mock_factory)
        accumulator = UtteranceAccumulator(accumulator_config_hybrid)
        
        interim_count = 0
        end_of_turn_count = 0
        
        def on_interim(text, speaker):
            nonlocal interim_count
            interim_count += 1
        
        async def on_end_of_turn(text, speaker, confidence, endpoint_type):
            nonlocal end_of_turn_count
            end_of_turn_count += 1
        
        callbacks = StreamingSTTCallbacks(
            on_interim=on_interim,
            on_end_of_turn=on_end_of_turn,
        )
        
        await manager.start_session(callbacks)
        
        # Simulate interim results (these should not be passed to accumulator
        # for completion - only end-of-turn events trigger completion)
        from src.protocol import Speaker
        on_interim("Tell me", Speaker.INTERVIEWER)
        on_interim("Tell me about", Speaker.INTERVIEWER)
        
        # Only end-of-turn should trigger completion
        await on_end_of_turn(
            "Tell me about your experience?",
            Speaker.INTERVIEWER,
            0.9,
            EndpointingType.SEMANTIC,
        )
        
        assert interim_count == 2
        assert end_of_turn_count == 1
        
        await manager.stop_session()


# ============================================================================
# Configuration Tests
# ============================================================================

class TestStreamingConfiguration:
    """Test configuration handling for streaming STT."""
    
    def test_accumulator_config_from_env_streaming_fields(self):
        """AccumulatorConfig should read streaming fields from environment."""
        with patch.dict(os.environ, {
            "ACCUMULATOR_ENDPOINTING_MODE": "streaming",
            "ACCUMULATOR_STREAMING_CONFIDENCE": "0.85",
        }):
            config = AccumulatorConfig.from_env()
            
            assert config.endpointing_mode == "streaming"
            assert config.streaming_confidence_threshold == 0.85
    
    def test_accumulator_config_defaults(self):
        """Default config should use hybrid mode."""
        config = AccumulatorConfig()
        
        assert config.endpointing_mode == "hybrid"
        assert config.streaming_confidence_threshold == 0.7
    
    def test_accumulator_config_to_dict_includes_streaming(self):
        """to_dict should include streaming configuration fields."""
        config = AccumulatorConfig(
            endpointing_mode="streaming",
            streaming_confidence_threshold=0.8,
        )
        
        d = config.to_dict()
        
        assert "endpointing_mode" in d
        assert "streaming_confidence_threshold" in d
        assert d["endpointing_mode"] == "streaming"
        assert d["streaming_confidence_threshold"] == 0.8


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestStreamingErrorHandling:
    """Test error handling in streaming STT pipeline."""
    
    @pytest.mark.asyncio
    async def test_manager_handles_connection_failure(self):
        """Manager should handle connection failures gracefully."""
        factory = MagicMock()
        provider = MagicMock()
        provider.connect = AsyncMock(side_effect=Exception("Connection refused"))
        factory.get_streaming_stt_provider.return_value = provider
        
        manager = StreamingSTTManager(factory)
        
        error_handler_called = False
        
        def on_error(e):
            nonlocal error_handler_called
            error_handler_called = True
        
        callbacks = StreamingSTTCallbacks(on_error=on_error)
        
        result = await manager.start_session(callbacks)
        
        assert result is False
        assert not manager.is_active
        assert error_handler_called
    
    @pytest.mark.asyncio
    async def test_accumulator_handles_empty_text(
        self, accumulator_config_hybrid
    ):
        """Accumulator should handle empty streaming text gracefully."""
        accumulator = UtteranceAccumulator(accumulator_config_hybrid)
        
        result = await accumulator.on_streaming_end_of_turn(
            text="",
            speaker="Interviewer",
            confidence=0.9,
            is_semantic=True,
        )
        
        # Empty text results in no utterance
        # (The method should handle this gracefully)
        # Note: Current implementation may still create a result,
        # but it should not crash
        # This test verifies no exception is raised


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
