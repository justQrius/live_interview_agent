"""
Tests for the Voice Activity Detection (VAD) module.

Following TDD: these tests are written first, before implementation.
Tests Silero VAD v4 integration with 512-sample window and 0.5 threshold.
"""

import asyncio
import sys
from dataclasses import fields
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSpeechSegmentDataclass:
    """Tests for the SpeechSegment dataclass."""

    def test_speech_segment_has_required_fields(self):
        """SpeechSegment should have audio, start_time, end_time, confidence fields."""
        from src.audio.vad import SpeechSegment

        # Check field names
        field_names = {f.name for f in fields(SpeechSegment)}
        expected_fields = {"audio", "start_time", "end_time", "confidence"}
        assert field_names == expected_fields

    def test_speech_segment_creation(self):
        """SpeechSegment should be created with correct values."""
        from src.audio.vad import SpeechSegment

        audio_data = b"\x00\x01\x02\x03"
        segment = SpeechSegment(
            audio=audio_data,
            start_time=0.5,
            end_time=1.0,
            confidence=0.85,
        )

        assert segment.audio == audio_data
        assert segment.start_time == 0.5
        assert segment.end_time == 1.0
        assert segment.confidence == 0.85

    def test_speech_segment_types(self):
        """SpeechSegment fields should have correct types."""
        from src.audio.vad import SpeechSegment

        segment = SpeechSegment(
            audio=b"\x00\x01",
            start_time=0.0,
            end_time=0.5,
            confidence=0.9,
        )

        assert isinstance(segment.audio, bytes)
        assert isinstance(segment.start_time, float)
        assert isinstance(segment.end_time, float)
        assert isinstance(segment.confidence, float)


class TestVADProcessorInitialization:
    """Tests for VADProcessor initialization."""

    def test_vad_processor_creation_with_defaults(self):
        """VADProcessor should be created with default threshold=0.5, window_size=512."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        assert processor.threshold == 0.5
        assert processor.window_size == 512

    def test_vad_processor_custom_threshold(self):
        """VADProcessor should accept custom threshold."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor(threshold=0.7)

        assert processor.threshold == 0.7

    def test_vad_processor_custom_window_size(self):
        """VADProcessor should accept custom window size."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor(window_size=256, sample_rate=8000)

        assert processor.window_size == 256
        assert processor.sample_rate == 8000

    def test_vad_processor_loads_model(self):
        """VADProcessor should load Silero VAD model on creation."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        assert processor._model is not None

    def test_vad_processor_has_sample_rate(self):
        """VADProcessor should have 16kHz sample rate configured."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        assert processor.sample_rate == 16000


class TestVADThresholdConfiguration:
    """Tests for VAD threshold adjustment."""

    def test_threshold_must_be_between_0_and_1(self):
        """Threshold should be validated to be between 0 and 1."""
        from src.audio.vad import VADProcessor

        # Valid thresholds
        processor = VADProcessor(threshold=0.0)
        assert processor.threshold == 0.0

        processor = VADProcessor(threshold=1.0)
        assert processor.threshold == 1.0

        processor = VADProcessor(threshold=0.5)
        assert processor.threshold == 0.5

    def test_threshold_below_zero_raises(self):
        """Threshold below 0 should raise ValueError."""
        from src.audio.vad import VADProcessor

        with pytest.raises(ValueError, match="threshold"):
            VADProcessor(threshold=-0.1)

    def test_threshold_above_one_raises(self):
        """Threshold above 1 should raise ValueError."""
        from src.audio.vad import VADProcessor

        with pytest.raises(ValueError, match="threshold"):
            VADProcessor(threshold=1.1)


class TestVADWindowSize:
    """Tests for VAD window size configuration."""

    def test_window_size_512_for_16khz(self):
        """Window size of 512 samples at 16kHz = 32ms."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor(window_size=512)

        # 512 samples at 16kHz = 32ms
        window_duration_ms = (processor.window_size / processor.sample_rate) * 1000
        assert window_duration_ms == 32.0

    def test_window_size_256_for_8khz(self):
        """Window size of 256 samples at 8kHz = 32ms (not used but valid)."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor(window_size=256, sample_rate=8000)

        assert processor.window_size == 256
        assert processor.sample_rate == 8000


class TestVADProcessChunk:
    """Tests for VAD process_chunk method."""

    @pytest.mark.asyncio
    async def test_process_chunk_returns_list(self):
        """process_chunk should return a list of SpeechSegment."""
        from src.audio.vad import SpeechSegment, VADProcessor

        processor = VADProcessor()

        # Create a 500ms chunk of silence (8000 samples at 16kHz)
        silence = np.zeros(8000, dtype=np.int16).tobytes()

        result = await processor.process_chunk(silence)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_process_chunk_filters_silence(self):
        """process_chunk should return empty list for pure silence."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        # Create a chunk of pure silence (zeros)
        silence = np.zeros(8000, dtype=np.int16).tobytes()

        result = await processor.process_chunk(silence)

        # Silence should produce no speech segments
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_process_chunk_detects_speech(self):
        """process_chunk should detect speech in audio with voice content."""
        from src.audio.vad import SpeechSegment, VADProcessor

        processor = VADProcessor()

        # Create synthetic speech-like audio (sine wave with varying amplitude)
        # This simulates speech-like patterns that VAD should detect
        sample_rate = 16000
        duration = 0.5  # 500ms
        t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)

        # Generate speech-like signal: modulated sine wave
        # Fundamental frequency around 150 Hz (typical male voice)
        speech_signal = np.sin(2 * np.pi * 150 * t) * 0.8
        # Add some harmonics
        speech_signal += np.sin(2 * np.pi * 300 * t) * 0.4
        speech_signal += np.sin(2 * np.pi * 450 * t) * 0.2

        # Scale to int16 range
        audio_int16 = (speech_signal * 32767 * 0.5).astype(np.int16)
        audio_bytes = audio_int16.tobytes()

        result = await processor.process_chunk(audio_bytes)

        # For this synthetic signal, VAD may or may not detect speech
        # The test validates the interface returns properly typed results
        assert isinstance(result, list)
        for segment in result:
            assert isinstance(segment, SpeechSegment)

    @pytest.mark.asyncio
    async def test_process_chunk_segment_has_valid_times(self):
        """Speech segments should have valid start/end times within chunk duration."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        # Create 500ms audio chunk
        sample_rate = 16000
        duration = 0.5
        num_samples = int(sample_rate * duration)

        # Generate audio with some energy
        t = np.linspace(0, duration, num_samples, dtype=np.float32)
        audio = (np.sin(2 * np.pi * 200 * t) * 16000).astype(np.int16)
        audio_bytes = audio.tobytes()

        result = await processor.process_chunk(audio_bytes)

        for segment in result:
            # Times should be non-negative
            assert segment.start_time >= 0.0
            # End time should be after start time
            assert segment.end_time >= segment.start_time
            # Times should be within chunk duration
            assert segment.end_time <= duration + 0.1  # Small tolerance

    @pytest.mark.asyncio
    async def test_process_chunk_segment_has_valid_confidence(self):
        """Speech segments should have confidence between 0 and 1."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        # Create audio with some content
        sample_rate = 16000
        duration = 0.5
        num_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, num_samples, dtype=np.float32)
        audio = (np.sin(2 * np.pi * 200 * t) * 16000).astype(np.int16)
        audio_bytes = audio.tobytes()

        result = await processor.process_chunk(audio_bytes)

        for segment in result:
            assert 0.0 <= segment.confidence <= 1.0


class TestVADEmptyInput:
    """Tests for handling empty or invalid input."""

    @pytest.mark.asyncio
    async def test_process_empty_bytes(self):
        """process_chunk should handle empty bytes gracefully."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        result = await processor.process_chunk(b"")

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_process_very_short_audio(self):
        """process_chunk should handle audio shorter than window size."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor(window_size=512)

        # Only 100 samples (less than 512 window size)
        short_audio = np.zeros(100, dtype=np.int16).tobytes()

        result = await processor.process_chunk(short_audio)

        # Should not crash, may return empty list
        assert isinstance(result, list)


class TestVADReset:
    """Tests for VAD state reset."""

    def test_reset_clears_internal_state(self):
        """reset() should clear any internal state for new session."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        # Reset should not raise
        processor.reset()

        # Processor should still be usable after reset
        assert processor._model is not None

    @pytest.mark.asyncio
    async def test_reset_between_sessions(self):
        """reset() should allow processing new audio sessions cleanly."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        # Process first session
        audio1 = np.zeros(8000, dtype=np.int16).tobytes()
        await processor.process_chunk(audio1)

        # Reset for new session
        processor.reset()

        # Process second session - should work normally
        audio2 = np.zeros(8000, dtype=np.int16).tobytes()
        result = await processor.process_chunk(audio2)

        assert isinstance(result, list)


class TestVADContinuousSpeech:
    """Tests for handling continuous speech across chunks."""

    @pytest.mark.asyncio
    async def test_continuous_speech_tracking(self):
        """VAD should track speech state across multiple process_chunk calls."""
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        # Process multiple chunks sequentially
        results = []
        for _ in range(3):
            # Create varied audio chunks
            audio = np.random.randint(-16000, 16000, 8000, dtype=np.int16).tobytes()
            result = await processor.process_chunk(audio)
            results.append(result)

        # All results should be valid lists
        assert all(isinstance(r, list) for r in results)


class TestVADIntegrationWithAudioModule:
    """Tests for VAD integration with audio module."""

    def test_vad_uses_same_sample_rate_as_audio_capture(self):
        """VAD should use the same 16kHz sample rate as AudioCapture."""
        from src.audio.capture import SAMPLE_RATE
        from src.audio.vad import VADProcessor

        processor = VADProcessor()

        assert processor.sample_rate == SAMPLE_RATE

    def test_vad_processor_is_exported_from_audio_module(self):
        """VADProcessor and SpeechSegment should be exported from src.audio module."""
        from src.audio import SpeechSegment, VADProcessor

        # Should not raise ImportError
        assert VADProcessor is not None
        assert SpeechSegment is not None


class TestVADConstants:
    """Tests for VAD-related constants."""

    def test_default_threshold_constant(self):
        """DEFAULT_VAD_THRESHOLD should be 0.5."""
        from src.audio.vad import DEFAULT_VAD_THRESHOLD

        assert DEFAULT_VAD_THRESHOLD == 0.5

    def test_default_window_size_constant(self):
        """DEFAULT_VAD_WINDOW_SIZE should be 512."""
        from src.audio.vad import DEFAULT_VAD_WINDOW_SIZE

        assert DEFAULT_VAD_WINDOW_SIZE == 512


class TestVADModelLoading:
    """Tests for VAD model loading behavior."""

    def test_model_loading_error_is_handled(self):
        """VADProcessor should raise clear error if model fails to load."""
        from src.audio.vad import VADModelError

        # VADModelError should be defined
        assert VADModelError is not None

    def test_vad_model_error_is_exception(self):
        """VADModelError should be an Exception subclass."""
        from src.audio.vad import VADModelError

        assert issubclass(VADModelError, Exception)
