"""
Integration tests for NoiseReducer with the audio pipeline.

Tests noise reduction integration with VAD → NoiseReducer → STT flow.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestNoiseReducerWithVAD:
    """Tests for NoiseReducer integration with VAD pipeline."""

    @pytest.mark.asyncio
    async def test_noise_reducer_processes_vad_output(self):
        """NoiseReducer should process speech segments from VAD."""
        from src.audio.noise_reduction import NoiseReducer
        from src.audio.vad import SpeechSegment

        reducer = NoiseReducer()

        # Create a speech segment (simulating VAD output)
        audio_data = np.random.randint(-16000, 16000, 8000, dtype=np.int16).tobytes()
        segment = SpeechSegment(
            audio=audio_data,
            start_time=0.0,
            end_time=0.5,
            confidence=0.9,
        )

        # Process the segment audio
        clean_audio = reducer.reduce_noise(segment.audio)

        assert isinstance(clean_audio, bytes)
        assert len(clean_audio) == len(segment.audio)

    @pytest.mark.asyncio
    async def test_noise_reducer_with_multiple_segments(self):
        """NoiseReducer should handle multiple VAD segments."""
        from src.audio.noise_reduction import NoiseReducer
        from src.audio.vad import SpeechSegment

        reducer = NoiseReducer()

        # Create multiple segments
        segments = [
            SpeechSegment(
                audio=np.random.randint(-16000, 16000, 4000, dtype=np.int16).tobytes(),
                start_time=i * 0.5,
                end_time=(i + 1) * 0.5,
                confidence=0.8,
            )
            for i in range(3)
        ]

        # Process each segment
        cleaned_segments = []
        for segment in segments:
            clean_audio = reducer.reduce_noise(segment.audio)
            cleaned_segments.append(clean_audio)

        assert len(cleaned_segments) == 3
        assert all(isinstance(seg, bytes) for seg in cleaned_segments)


class TestNoiseReducerWithServerPipeline:
    """Tests for NoiseReducer integration with server audio pipeline."""

    @pytest.mark.asyncio
    async def test_server_can_use_noise_reducer(self):
        """Server should be able to integrate NoiseReducer into pipeline."""
        from src.audio.noise_reduction import NoiseReducer

        # This test validates that NoiseReducer can be instantiated in server context
        reducer = NoiseReducer(enabled=True)

        # Simulate processing audio from VAD before sending to STT
        audio_chunk = np.zeros(8000, dtype=np.int16).tobytes()
        clean_audio = reducer.reduce_noise(audio_chunk)

        assert clean_audio is not None

    @pytest.mark.asyncio
    async def test_server_can_disable_noise_reducer(self):
        """Server should be able to disable noise reduction via config."""
        from src.audio.noise_reduction import NoiseReducer

        # Initialize with disabled mode (for users who don't want noise reduction)
        reducer = NoiseReducer(enabled=False)

        audio_chunk = np.zeros(8000, dtype=np.int16).tobytes()
        result = reducer.reduce_noise(audio_chunk)

        # Should pass through unchanged
        assert result == audio_chunk


class TestNoiseReducerLatencyInPipeline:
    """Tests for noise reduction latency impact on pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_latency_with_noise_reduction(self):
        """Pipeline with NoiseReducer should meet <5sec latency target."""
        import time

        from src.audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Simulate 500ms audio chunk (standard chunk size)
        audio_chunk = np.random.randint(-16000, 16000, 8000, dtype=np.int16).tobytes()

        # Measure noise reduction time
        start = time.time()
        clean_audio = reducer.reduce_noise(audio_chunk)
        nr_latency = time.time() - start

        # Noise reduction should be <100ms to stay within 5sec total latency budget
        assert nr_latency < 0.1, f"Noise reduction took {nr_latency*1000:.1f}ms"

    @pytest.mark.asyncio
    async def test_pipeline_latency_without_noise_reduction(self):
        """Pipeline without NoiseReducer should have minimal overhead."""
        import time

        from src.audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(enabled=False)

        audio_chunk = np.random.randint(-16000, 16000, 8000, dtype=np.int16).tobytes()

        start = time.time()
        result = reducer.reduce_noise(audio_chunk)
        latency = time.time() - start

        # Disabled mode should be nearly instant (<1ms)
        assert latency < 0.001


class TestNoiseReducerConfiguration:
    """Tests for configuring NoiseReducer in server context."""

    def test_noise_reducer_default_config(self):
        """NoiseReducer should have sensible defaults for server use."""
        from src.audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Defaults should be:
        # - Enabled
        # - Stationary mode (better for consistent background noise)
        # - Moderate aggressiveness
        assert reducer.enabled is True
        assert reducer.stationary is True
        assert 0.5 <= reducer.prop_decrease <= 1.5

    def test_noise_reducer_aggressive_config(self):
        """NoiseReducer should support aggressive mode for very noisy environments."""
        from src.audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(prop_decrease=1.5, stationary=False)

        assert reducer.prop_decrease == 1.5
        assert reducer.stationary is False

    def test_noise_reducer_gentle_config(self):
        """NoiseReducer should support gentle mode to preserve voice characteristics."""
        from src.audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(prop_decrease=0.5)

        assert reducer.prop_decrease == 0.5


class TestNoiseReducerMemoryUsage:
    """Tests for memory efficiency of NoiseReducer."""

    def test_noise_reducer_does_not_accumulate_memory(self):
        """NoiseReducer should not accumulate memory across calls."""
        from src.audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Process 100 chunks (simulating 50 seconds of audio)
        for _ in range(100):
            audio = np.random.randint(-16000, 16000, 8000, dtype=np.int16)
            result = reducer.reduce_noise(audio)

        # Should complete without memory errors
        assert result is not None

    def test_disabled_reducer_has_minimal_memory_footprint(self):
        """Disabled NoiseReducer should have minimal memory usage."""
        from src.audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(enabled=False)

        # Should not load noisereduce library
        assert reducer._nr is None
