import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import STTProvider, TranscriptionResult
# This import will fail until I create the file, but that's part of the process
try:
    from providers.stt.groq import GroqSTTProvider
except ImportError:
    pass

class TestGroqSTTProviderInit:
    """Test GroqSTTProvider initialization."""

    @patch("providers.stt.groq.Groq")
    def test_init_success(self, mock_groq):
        """Test successful initialization."""
        from providers.stt.groq import GroqSTTProvider
        provider = GroqSTTProvider(api_key="test_key")

        mock_groq.assert_called_once_with(api_key="test_key")
        assert provider.client is not None
        assert provider.is_available() is True

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        from providers.stt.groq import GroqSTTProvider
        with pytest.raises(ValueError, match="API key is required"):
            GroqSTTProvider(api_key="")

class TestGroqSTTProviderTranscribe:
    """Test transcribe method."""

    @pytest.fixture
    def mock_groq_client(self):
        with patch("providers.stt.groq.Groq") as mock_class:
            mock_client = MagicMock()
            mock_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def provider(self, mock_groq_client):
        from providers.stt.groq import GroqSTTProvider
        return GroqSTTProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_transcribe_success(self, provider, mock_groq_client):
        """Test successful transcription."""
        # Mock the transcriptions.create method
        mock_transcription = MagicMock()
        mock_transcription.text = "Hello world"
        
        # We need to mock the chain: client.audio.transcriptions.create
        mock_groq_client.audio.transcriptions.create.return_value = mock_transcription

        audio_bytes = b"fake_wav_header" + b"\x00" * 100

        result = await provider.transcribe(audio_bytes)

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.language == "en"
        
        # Verify the call
        mock_groq_client.audio.transcriptions.create.assert_called_once()
        call_args = mock_groq_client.audio.transcriptions.create.call_args
        assert call_args.kwargs['model'] == 'whisper-large-v3'
        
        file_arg = call_args.kwargs['file']
        assert file_arg[0] == "audio.wav"
        file_arg[1].seek(0)
        assert file_arg[1].read() == audio_bytes

    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self, provider, mock_groq_client):
        """Test transcribing empty audio returns empty result."""
        result = await provider.transcribe(b"")

        assert isinstance(result, TranscriptionResult)
        assert result.text == ""
        mock_groq_client.audio.transcriptions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_error(self, provider, mock_groq_client):
        """Test transcription error handling."""
        mock_groq_client.audio.transcriptions.create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="Groq STT Error"):
             await provider.transcribe(b"fake_audio")
