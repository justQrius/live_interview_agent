"""
Unit tests for LocalWhisperProvider (faster-whisper).

Tests the local GPU-accelerated STT provider implementation.
These tests mock the faster-whisper library so it doesn't need to be installed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import sys
import os

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from src.providers.base import STTProvider, TranscriptionResult


# Global mock for faster_whisper.WhisperModel that persists across tests
_mock_whisper_model = MagicMock()
_mock_fw_module = MagicMock()
_mock_fw_module.WhisperModel = _mock_whisper_model

# Inject the mock module into sys.modules before any test imports the provider
sys.modules["faster_whisper"] = _mock_fw_module


@pytest.fixture(autouse=True)
def reset_whisper_mock():
    """Reset the WhisperModel mock before each test."""
    global _mock_whisper_model
    _mock_whisper_model.reset_mock()
    _mock_whisper_model.side_effect = None
    _mock_whisper_model.return_value = MagicMock()
    
    # Update the module's reference
    _mock_fw_module.WhisperModel = _mock_whisper_model
    sys.modules["faster_whisper"] = _mock_fw_module
    
    yield _mock_whisper_model


class TestLocalWhisperProviderGPUDetection:
    """Test GPU detection functionality."""

    def test_gpu_available_with_cuda(self, reset_whisper_mock):
        """Test that GPU is detected when CUDA is available."""
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import _check_gpu_available
            assert _check_gpu_available() is True

    def test_gpu_not_available(self, reset_whisper_mock):
        """Test that GPU detection returns False when no CUDA."""
        with patch("torch.cuda.is_available", return_value=False):
            from src.providers.stt.local_whisper import _check_gpu_available
            assert _check_gpu_available() is False


class TestLocalWhisperProviderInit:
    """Test LocalWhisperProvider initialization."""

    def test_init_success_with_gpu(self, reset_whisper_mock):
        """Test successful initialization with GPU."""
        mock_model = MagicMock()
        reset_whisper_mock.return_value = mock_model
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider()

        reset_whisper_mock.assert_called_once_with(
            "large-v3-turbo",
            device="cuda",
            compute_type="int8_float16",
        )
        assert provider.is_available() is True
        assert provider._device == "cuda"

    def test_init_success_without_gpu(self, reset_whisper_mock):
        """Test initialization falls back to CPU when no GPU."""
        mock_model = MagicMock()
        reset_whisper_mock.return_value = mock_model
        
        with patch("torch.cuda.is_available", return_value=False):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider()

        reset_whisper_mock.assert_called_once_with(
            "large-v3-turbo",
            device="cpu",
            compute_type="int8",
        )
        assert provider.is_available() is True
        assert provider._device == "cpu"

    def test_init_with_custom_model(self, reset_whisper_mock):
        """Test initialization with custom model size."""
        mock_model = MagicMock()
        reset_whisper_mock.return_value = mock_model
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider(model_size="small")

        reset_whisper_mock.assert_called_once_with(
            "small",
            device="cuda",
            compute_type="int8_float16",
        )

    def test_init_model_fallback_on_oom(self, reset_whisper_mock):
        """Test that provider falls back to smaller model on OOM."""
        reset_whisper_mock.side_effect = [
            Exception("CUDA out of memory"),
            MagicMock(),
        ]
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider()

        assert reset_whisper_mock.call_count == 2
        assert reset_whisper_mock.call_args_list[1][0][0] == "distil-large-v3"
        assert provider.is_available() is True


class TestLocalWhisperProviderTranscribe:
    """Test transcribe method."""

    @pytest.fixture
    def provider_with_model(self, reset_whisper_mock):
        """Create provider with mocked model."""
        mock_model = MagicMock()
        reset_whisper_mock.return_value = mock_model
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider()
        
        return provider, mock_model

    @pytest.mark.asyncio
    async def test_transcribe_success(self, provider_with_model):
        """Test successful transcription."""
        provider, mock_model = provider_with_model
        
        mock_segment = MagicMock()
        mock_segment.text = "Hello world"
        mock_segment.avg_logprob = -0.3
        
        mock_info = MagicMock()
        mock_info.language = "en"
        
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        audio_bytes = np.zeros(16000, dtype=np.int16).tobytes()

        result = await provider.transcribe(audio_bytes)

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.language == "en"
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self, provider_with_model):
        """Test empty audio returns empty result."""
        provider, mock_model = provider_with_model
        
        result = await provider.transcribe(b"")

        assert result.text == ""
        mock_model.transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_very_short_audio(self, provider_with_model):
        """Test very short audio returns empty result."""
        provider, mock_model = provider_with_model
        audio_bytes = np.zeros(800, dtype=np.int16).tobytes()

        result = await provider.transcribe(audio_bytes)

        assert result.text == ""
        mock_model.transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_multiple_segments(self, provider_with_model):
        """Test multiple segment transcription."""
        provider, mock_model = provider_with_model
        
        segment1 = MagicMock(text="Hello", avg_logprob=-0.2)
        segment2 = MagicMock(text="world", avg_logprob=-0.3)
        mock_info = MagicMock(language="en")
        
        mock_model.transcribe.return_value = ([segment1, segment2], mock_info)
        audio_bytes = np.zeros(32000, dtype=np.int16).tobytes()

        result = await provider.transcribe(audio_bytes)
        assert result.text == "Hello world"

    @pytest.mark.asyncio
    async def test_transcribe_error(self, provider_with_model):
        """Test transcription error handling."""
        provider, mock_model = provider_with_model
        mock_model.transcribe.side_effect = Exception("Model error")
        audio_bytes = np.zeros(16000, dtype=np.int16).tobytes()
        
        from src.providers.stt.local_whisper import LocalWhisperProviderError
        with pytest.raises(LocalWhisperProviderError, match="Transcription failed"):
            await provider.transcribe(audio_bytes)


class TestLocalWhisperProviderHelpers:
    """Test helper methods."""

    def test_get_model_info(self, reset_whisper_mock):
        """Test get_model_info returns configuration."""
        reset_whisper_mock.return_value = MagicMock()
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider(model_size="medium")
        
        info = provider.get_model_info()
        
        assert info["model_size"] == "medium"
        assert info["device"] == "cuda"
        assert info["available"] is True

    def test_pcm_to_float32(self, reset_whisper_mock):
        """Test PCM to float32 conversion."""
        reset_whisper_mock.return_value = MagicMock()
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider()
        
        test_data = np.array([0, 32767, -32768, 16384], dtype=np.int16).tobytes()
        result = provider._pcm_to_float32(test_data)
        
        assert result.dtype == np.float32
        np.testing.assert_almost_equal(result[0], 0.0, decimal=5)
        np.testing.assert_almost_equal(result[1], 0.99997, decimal=4)
        np.testing.assert_almost_equal(result[2], -1.0, decimal=5)


class TestLocalWhisperProviderIsAvailable:
    """Test is_available method."""

    def test_is_available_true(self, reset_whisper_mock):
        """Test available when model loads."""
        reset_whisper_mock.return_value = MagicMock()
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider
            provider = LocalWhisperProvider()
        
        assert provider.is_available() is True

    def test_is_available_false_on_failure(self, reset_whisper_mock):
        """Test exception when all models fail."""
        reset_whisper_mock.side_effect = [
            Exception("fail 1"), Exception("fail 2"),
            Exception("fail 3"), Exception("fail 4"), Exception("fail 5")
        ]
        
        with patch("torch.cuda.is_available", return_value=True):
            from src.providers.stt.local_whisper import LocalWhisperProvider, LocalWhisperProviderError
            
            with pytest.raises(LocalWhisperProviderError):
                LocalWhisperProvider()


class TestLocalWhisperProviderIntegration:
    """Integration tests (require actual installation)."""

    @pytest.mark.skipif(
        not os.environ.get("RUN_INTEGRATION_TESTS"),
        reason="Integration tests disabled"
    )
    @pytest.mark.asyncio
    async def test_real_transcription(self):
        """Test with real model."""
        # Remove mock for real test
        if "faster_whisper" in sys.modules:
            del sys.modules["faster_whisper"]
            
        from src.providers.stt.local_whisper import LocalWhisperProvider, _check_gpu_available
        
        if not _check_gpu_available():
            pytest.skip("No GPU available")
        
        provider = LocalWhisperProvider(model_size="tiny")
        audio_bytes = np.zeros(32000, dtype=np.int16).tobytes()
        result = await provider.transcribe(audio_bytes)
        
        assert isinstance(result, TranscriptionResult)
