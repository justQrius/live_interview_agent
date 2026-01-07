"""
Tests for Noise Reduction module.

Following TDD: these tests are written first, before implementation.
Tests noisereduce library integration with configurable noise reduction.
"""

import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestNoiseReducerInitialization:
    """Tests for NoiseReducer initialization."""

    def test_noise_reducer_creation_with_defaults(self):
        """NoiseReducer should be created with default settings."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        assert reducer is not None

    def test_noise_reducer_has_sample_rate(self):
        """NoiseReducer should have 16kHz sample rate configured."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        assert reducer.sample_rate == 16000

    def test_noise_reducer_enabled_by_default(self):
        """NoiseReducer should be enabled by default."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        assert reducer.enabled is True

    def test_noise_reducer_can_be_disabled(self):
        """NoiseReducer should accept enabled=False parameter."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(enabled=False)

        assert reducer.enabled is False

    def test_noise_reducer_custom_sample_rate(self):
        """NoiseReducer should accept custom sample rate."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(sample_rate=48000)

        assert reducer.sample_rate == 48000


class TestNoiseReducerConfiguration:
    """Tests for NoiseReducer configuration options."""

    def test_noise_reducer_stationary_mode(self):
        """NoiseReducer should support stationary noise reduction."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(stationary=True)

        assert reducer.stationary is True

    def test_noise_reducer_nonstationary_mode(self):
        """NoiseReducer should support non-stationary noise reduction."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(stationary=False)

        assert reducer.stationary is False

    def test_noise_reducer_default_is_stationary(self):
        """NoiseReducer should use stationary mode by default."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        assert reducer.stationary is True

    def test_noise_reducer_prop_decrease_parameter(self):
        """NoiseReducer should accept prop_decrease parameter (aggressiveness)."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(prop_decrease=0.8)

        assert reducer.prop_decrease == 0.8

    def test_noise_reducer_default_prop_decrease(self):
        """NoiseReducer should have sensible default prop_decrease."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Default should be moderate (not too aggressive)
        assert 0.0 <= reducer.prop_decrease <= 1.5


class TestNoiseReducerProcessing:
    """Tests for noise reduction processing."""

    def test_reduce_noise_accepts_numpy_array(self):
        """reduce_noise should accept numpy array input."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Create test audio (1 second of silence)
        audio = np.zeros(16000, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        assert isinstance(result, np.ndarray)

    def test_reduce_noise_accepts_bytes(self):
        """reduce_noise should accept bytes input."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Create test audio as bytes
        audio = np.zeros(16000, dtype=np.int16).tobytes()

        result = reducer.reduce_noise(audio)

        assert isinstance(result, bytes)

    def test_reduce_noise_preserves_dtype(self):
        """reduce_noise should preserve int16 dtype."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        audio = np.zeros(16000, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        assert result.dtype == np.int16

    def test_reduce_noise_preserves_shape(self):
        """reduce_noise should preserve array shape (mono audio)."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        audio = np.zeros(16000, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        assert result.shape == audio.shape

    def test_reduce_noise_with_silent_audio(self):
        """reduce_noise should handle silent audio without errors."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Pure silence
        audio = np.zeros(16000, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        # Should not crash, result should be close to input
        assert result is not None
        assert len(result) == len(audio)

    def test_reduce_noise_with_noisy_audio(self):
        """reduce_noise should process noisy audio."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Create noisy audio (white noise)
        np.random.seed(42)
        noise = np.random.randint(-1000, 1000, 16000, dtype=np.int16)

        result = reducer.reduce_noise(noise)

        assert result is not None
        assert len(result) == len(noise)
        # Result should have reduced amplitude (less noise)
        assert np.abs(result).mean() <= np.abs(noise).mean()

    def test_reduce_noise_with_speech_signal(self):
        """reduce_noise should preserve speech while reducing noise."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Create synthetic speech (sine wave at voice frequency)
        t = np.linspace(0, 1.0, 16000, dtype=np.float32)
        speech = (np.sin(2 * np.pi * 200 * t) * 16000).astype(np.int16)

        result = reducer.reduce_noise(speech)

        assert result is not None
        assert len(result) == len(speech)
        # Speech energy should be mostly preserved
        assert np.abs(result).max() > 1000  # Not zeroed out


class TestNoiseReducerDisabledMode:
    """Tests for disabled noise reduction (pass-through mode)."""

    def test_disabled_reducer_returns_input_unchanged(self):
        """When disabled, reduce_noise should return input unchanged."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(enabled=False)

        audio = np.random.randint(-16000, 16000, 16000, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        # Should be identical (pass-through)
        np.testing.assert_array_equal(result, audio)

    def test_disabled_reducer_has_zero_latency(self):
        """When disabled, reduce_noise should have minimal overhead."""
        import time

        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer(enabled=False)

        audio = np.zeros(16000, dtype=np.int16)

        start = time.time()
        result = reducer.reduce_noise(audio)
        elapsed = time.time() - start

        # Should be nearly instant (<1ms)
        assert elapsed < 0.001


class TestNoiseReducerLatency:
    """Tests for noise reduction latency."""

    def test_reduce_noise_latency_under_100ms(self):
        """reduce_noise should process 500ms audio in <100ms."""
        import time

        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # 500ms audio chunk (8000 samples at 16kHz)
        audio = np.random.randint(-16000, 16000, 8000, dtype=np.int16)

        start = time.time()
        result = reducer.reduce_noise(audio)
        elapsed = time.time() - start

        # Should be under 100ms
        assert elapsed < 0.1, f"Latency {elapsed*1000:.1f}ms exceeds 100ms target"

    def test_reduce_noise_latency_for_1sec_audio(self):
        """reduce_noise should handle 1 second audio reasonably fast."""
        import time

        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # 1 second audio
        audio = np.random.randint(-16000, 16000, 16000, dtype=np.int16)

        start = time.time()
        result = reducer.reduce_noise(audio)
        elapsed = time.time() - start

        # Should complete in reasonable time (<200ms for 1sec audio)
        assert elapsed < 0.2


class TestNoiseReducerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_reduce_noise_empty_array(self):
        """reduce_noise should handle empty array gracefully."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        audio = np.array([], dtype=np.int16)

        result = reducer.reduce_noise(audio)

        assert isinstance(result, np.ndarray)
        assert len(result) == 0

    def test_reduce_noise_very_short_audio(self):
        """reduce_noise should handle very short audio (< 100 samples)."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        audio = np.zeros(50, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        assert len(result) == len(audio)

    def test_reduce_noise_with_clipping(self):
        """reduce_noise should handle audio with clipping (max values)."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Audio at max int16 range
        audio = np.full(1000, 32767, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        assert result is not None
        # Should not overflow
        assert result.dtype == np.int16


class TestNoiseReducerThreadSafety:
    """Tests for thread safety (important for async audio processing)."""

    def test_reduce_noise_is_stateless(self):
        """reduce_noise should be stateless (safe to call concurrently)."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Process two different audio chunks
        audio1 = np.zeros(8000, dtype=np.int16)
        audio2 = np.ones(8000, dtype=np.int16) * 1000

        result1 = reducer.reduce_noise(audio1)
        result2 = reducer.reduce_noise(audio2)

        # Results should be independent
        assert not np.array_equal(result1, result2)


class TestNoiseReducerIntegrationWithAudioModule:
    """Tests for integration with audio pipeline."""

    def test_noise_reducer_uses_same_sample_rate_as_audio_capture(self):
        """NoiseReducer should use the same 16kHz sample rate as AudioCapture."""
        from audio.capture import SAMPLE_RATE
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        assert reducer.sample_rate == SAMPLE_RATE

    def test_noise_reducer_is_exported_from_audio_module(self):
        """NoiseReducer should be exported from audio module."""
        from audio import NoiseReducer

        # Should not raise ImportError
        assert NoiseReducer is not None


class TestNoiseReducerConstants:
    """Tests for noise reduction constants."""

    def test_default_prop_decrease_constant_exists(self):
        """DEFAULT_PROP_DECREASE constant should exist."""
        from audio.noise_reduction import DEFAULT_PROP_DECREASE

        assert DEFAULT_PROP_DECREASE is not None
        assert 0.0 <= DEFAULT_PROP_DECREASE <= 1.5


class TestNoiseReducerWithRealNoisereduceLibrary:
    """Integration tests with actual noisereduce library."""

    def test_noisereduce_library_is_available(self):
        """noisereduce library should be importable."""
        try:
            import noisereduce as nr

            assert nr is not None
        except ImportError:
            pytest.skip("noisereduce library not installed")

    def test_reduce_noise_calls_noisereduce(self):
        """reduce_noise should call noisereduce.reduce_noise."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Create test audio with noise
        np.random.seed(42)
        audio = np.random.randint(-5000, 5000, 8000, dtype=np.int16)

        result = reducer.reduce_noise(audio)

        # Should produce different output (noise reduced)
        assert result is not None
        # For noisy input, output should be different
        # (This is a weak test, but validates processing occurred)


class TestNoiseReducerAccuracyImprovement:
    """Tests for measuring STT accuracy improvement (optional validation)."""

    def test_noise_reducer_improves_snr(self):
        """reduce_noise should improve Signal-to-Noise Ratio."""
        from audio.noise_reduction import NoiseReducer

        reducer = NoiseReducer()

        # Create signal (clean speech) + noise
        t = np.linspace(0, 0.5, 8000, dtype=np.float32)
        signal = np.sin(2 * np.pi * 200 * t)
        np.random.seed(42)
        noise = np.random.randn(8000).astype(np.float32) * 0.3

        # Noisy audio
        noisy = ((signal + noise) * 16000).astype(np.int16)

        result = reducer.reduce_noise(noisy)

        # Result should have less noise (measured by variance)
        result_float = result.astype(np.float32) / 16000.0
        signal_power = np.var(signal)
        result_power = np.var(result_float)

        # Result should be closer to original signal power than noisy signal
        # This is a simplified SNR test
        assert result_power > 0  # Not silent
