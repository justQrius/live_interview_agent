"""
Tests for GeminiSTTProvider.

Tests the Gemini STT provider that uses the unified google-genai SDK.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from src.providers.base import STTProvider, TranscriptionResult
from src.providers.stt.gemini import GeminiSTTProvider, GeminiSTTProviderError


class TestGeminiSTTProviderInit:
    """Test GeminiSTTProvider initialization."""

    @patch("src.providers.stt.gemini.genai")
    def test_init_success(self, mock_genai):
        """Test successful initialization."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        
        provider = GeminiSTTProvider(api_key="test_key")

        mock_genai.Client.assert_called_once_with(api_key="test_key")
        assert provider._api_key == "test_key"
        assert provider._available is True
        assert provider._client == mock_client

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiSTTProvider(api_key="")

    def test_init_none_api_key(self):
        """Test that None API key raises error."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiSTTProvider(api_key=None)

    @patch("src.providers.stt.gemini.genai")
    def test_implements_stt_provider(self, mock_genai):
        """Test that GeminiSTTProvider implements STTProvider interface."""
        mock_genai.Client.return_value = MagicMock()
        provider = GeminiSTTProvider(api_key="test_key")
        assert isinstance(provider, STTProvider)

    @patch("src.providers.stt.gemini.genai")
    def test_custom_model_name(self, mock_genai):
        """Test initialization with custom model name."""
        mock_genai.Client.return_value = MagicMock()
        provider = GeminiSTTProvider(api_key="test_key", model_name="custom-model")

        assert provider._model_name == "custom-model"


class TestGeminiSTTProviderAvailability:
    """Test is_available method."""

    @patch("src.providers.stt.gemini.genai")
    def test_is_available_true(self, mock_genai):
        """Test is_available returns True when initialized properly."""
        mock_genai.Client.return_value = MagicMock()
        provider = GeminiSTTProvider(api_key="test_key")
        assert provider.is_available() is True

    @patch("src.providers.stt.gemini.genai")
    def test_is_available_false_after_error(self, mock_genai):
        """Test is_available returns False after initialization error."""
        mock_genai.Client.side_effect = Exception("API Error")

        with pytest.raises(GeminiSTTProviderError):
            GeminiSTTProvider(api_key="test_key")


class TestGeminiSTTProviderTranscribe:
    """Test transcribe method."""

    @pytest.fixture
    def mock_genai(self):
        with patch("src.providers.stt.gemini.genai") as mock:
            mock.Client.return_value = MagicMock()
            yield mock

    @pytest.fixture
    def mock_types(self):
        with patch("src.providers.stt.gemini.types") as mock:
            mock.Part.from_bytes.return_value = MagicMock()
            yield mock

    @pytest.fixture
    def provider(self, mock_genai, mock_types):
        return GeminiSTTProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_transcribe_success(self, provider):
        """Test successful transcription."""
        mock_response = MagicMock()
        mock_response.text = "Hello world"
        provider._client.models.generate_content = MagicMock(return_value=mock_response)

        audio_bytes = b"\x00" * 32000  # 1 sec of silence (approx)

        result = await provider.transcribe(audio_bytes)

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.language == "en"
        provider._client.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_with_language(self, provider):
        """Test transcription with specified language."""
        mock_response = MagicMock()
        mock_response.text = "Bonjour"
        provider._client.models.generate_content = MagicMock(return_value=mock_response)

        audio_bytes = b"\x00" * 32000

        result = await provider.transcribe(audio_bytes, language="fr")

        assert result.text == "Bonjour"
        assert result.language == "fr"

    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self, provider):
        """Test transcribing empty audio returns empty result."""
        result = await provider.transcribe(b"")

        assert isinstance(result, TranscriptionResult)
        assert result.text == ""
        provider._client.models.generate_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_error(self, provider):
        """Test transcription error handling."""
        provider._client.models.generate_content = MagicMock(side_effect=Exception("API Error"))

        with pytest.raises(GeminiSTTProviderError, match="Transcription failed"):
            await provider.transcribe(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_transcribe_empty_response(self, provider):
        """Test handling empty response from API."""
        mock_response = MagicMock()
        mock_response.text = None
        provider._client.models.generate_content = MagicMock(return_value=mock_response)

        result = await provider.transcribe(b"\x00" * 32000)

        assert result.text == ""

    @pytest.mark.asyncio
    async def test_transcribe_whitespace_response(self, provider):
        """Test response with whitespace is trimmed."""
        mock_response = MagicMock()
        mock_response.text = "  Hello world  \n"
        provider._client.models.generate_content = MagicMock(return_value=mock_response)

        result = await provider.transcribe(b"\x00" * 32000)

        assert result.text == "Hello world"


class TestGeminiSTTProviderPCMToWAV:
    """Test PCM to WAV conversion."""

    @patch("src.providers.stt.gemini.genai")
    def test_pcm_to_wav_creates_valid_wav(self, mock_genai):
        """Test that PCM to WAV conversion creates valid WAV header."""
        mock_genai.Client.return_value = MagicMock()
        provider = GeminiSTTProvider(api_key="test_key")

        # Create some test PCM data
        pcm_data = b"\x00\x01" * 1000  # 2000 bytes of PCM

        wav_data = provider._pcm_to_wav(pcm_data)

        # Check WAV header (RIFF)
        assert wav_data[:4] == b"RIFF"
        # Check WAVE format
        assert wav_data[8:12] == b"WAVE"
        # Check fmt chunk
        assert wav_data[12:16] == b"fmt "

    @patch("src.providers.stt.gemini.genai")
    def test_pcm_to_wav_preserves_data(self, mock_genai):
        """Test that PCM data is preserved in WAV."""
        mock_genai.Client.return_value = MagicMock()
        provider = GeminiSTTProvider(api_key="test_key")

        pcm_data = b"\x00\x01\x02\x03" * 100

        wav_data = provider._pcm_to_wav(pcm_data)

        # WAV header is 44 bytes, data should follow
        # The PCM data should be at the end
        assert wav_data[-len(pcm_data):] == pcm_data


class TestGeminiSTTProviderBackwardsCompatibility:
    """Test backwards compatibility with old GeminiSTT interface."""

    @pytest.fixture
    def mock_genai(self):
        with patch("src.providers.stt.gemini.genai") as mock:
            mock.Client.return_value = MagicMock()
            yield mock

    @pytest.fixture
    def mock_types(self):
        with patch("src.providers.stt.gemini.types") as mock:
            mock.Part.from_bytes.return_value = MagicMock()
            yield mock

    @pytest.fixture
    def provider(self, mock_genai, mock_types):
        return GeminiSTTProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_transcribe_returns_result_with_text_attribute(self, provider):
        """Ensure TranscriptionResult has text attribute for compatibility."""
        mock_response = MagicMock()
        mock_response.text = "Test text"
        provider._client.models.generate_content = MagicMock(return_value=mock_response)

        result = await provider.transcribe(b"\x00" * 100)

        # Can access .text directly like old interface
        assert result.text == "Test text"
