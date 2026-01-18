import unittest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock deepgram module before importing the provider
mock_deepgram = MagicMock()
mock_deepgram.AsyncDeepgramClient = MagicMock()
mock_deepgram.core = MagicMock()
mock_deepgram.core.api_error = MagicMock()
mock_deepgram.core.api_error.ApiError = Exception
sys.modules['deepgram'] = mock_deepgram
sys.modules['deepgram.core'] = mock_deepgram.core
sys.modules['deepgram.core.api_error'] = mock_deepgram.core.api_error

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import TranscriptionResult
from providers.stt.deepgram import DeepgramSTTProvider


class TestDeepgramSTTProvider(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.api_key = "test_key"
        self.audio_data = b"fake_audio_data"
        
        # Setup mocks for v5.x SDK async client path
        self.mock_client = MagicMock()
        self.mock_listen = MagicMock()
        self.mock_v1 = MagicMock()
        self.mock_media = MagicMock()
        
        # Chain the mocks: client.listen.v1.media.transcribe_file
        self.mock_client.listen = self.mock_listen
        self.mock_listen.v1 = self.mock_v1
        self.mock_v1.media = self.mock_media
        
        # Setup transcribe_file response
        self.mock_response = MagicMock()
        self.mock_channel = MagicMock()
        self.mock_alternative = MagicMock()
        self.mock_alternative.transcript = "Hello world"
        self.mock_alternative.confidence = 0.98
        self.mock_channel.alternatives = [self.mock_alternative]
        self.mock_response.results.channels = [self.mock_channel]
        
        # Make transcribe_file an async mock
        self.mock_media.transcribe_file = AsyncMock(return_value=self.mock_response)

    @patch('providers.stt.deepgram.AsyncDeepgramClient')
    async def test_transcribe_success(self, MockClient):
        # Arrange
        MockClient.return_value = self.mock_client
        provider = DeepgramSTTProvider(self.api_key)
        
        # Act
        result = await provider.transcribe(self.audio_data)
        
        # Assert
        self.assertIsInstance(result, TranscriptionResult)
        self.assertEqual(result.text, "Hello world")
        self.assertEqual(result.confidence, 0.98)
        
        # Verify client initialization with keyword arg
        MockClient.assert_called_with(api_key=self.api_key)
        
        # Verify transcription call
        call_kwargs = self.mock_media.transcribe_file.call_args.kwargs
        self.assertEqual(call_kwargs["request"], self.audio_data)
        self.assertEqual(call_kwargs["model"], "nova-3")
        self.assertEqual(call_kwargs["smart_format"], True)
        self.assertEqual(call_kwargs["language"], "en")

    @patch('providers.stt.deepgram.AsyncDeepgramClient')
    async def test_transcribe_empty_audio(self, MockClient):
        MockClient.return_value = self.mock_client
        provider = DeepgramSTTProvider(self.api_key)
        result = await provider.transcribe(b"")
        self.assertEqual(result.text, "")

    @patch('providers.stt.deepgram.AsyncDeepgramClient')
    async def test_init_raises_error_without_api_key(self, MockClient):
        with self.assertRaises(ValueError):
            DeepgramSTTProvider("")

    @patch('providers.stt.deepgram.AsyncDeepgramClient')
    async def test_custom_model(self, MockClient):
        """Test that custom model is used."""
        MockClient.return_value = self.mock_client
        provider = DeepgramSTTProvider(self.api_key, model="nova-2")
        self.assertEqual(provider.model, "nova-2")

    @patch('providers.stt.deepgram.AsyncDeepgramClient')
    async def test_timeout_and_retry_config(self, MockClient):
        """Test that timeout and retry options are configured."""
        MockClient.return_value = self.mock_client
        provider = DeepgramSTTProvider(
            self.api_key,
            timeout_seconds=120,
            max_retries=5
        )
        self.assertEqual(provider.timeout_seconds, 120)
        self.assertEqual(provider.max_retries, 5)

    @patch('providers.stt.deepgram.AsyncDeepgramClient')
    async def test_keyterms_config(self, MockClient):
        """Test that keyterms are configured for vocabulary boosting."""
        MockClient.return_value = self.mock_client
        keyterms = ["STAR", "behavioral", "technical"]
        provider = DeepgramSTTProvider(self.api_key, keyterms=keyterms)
        self.assertEqual(provider.keyterms, keyterms)
        
        # Verify keyterms are passed to transcribe
        await provider.transcribe(self.audio_data)
        call_kwargs = self.mock_media.transcribe_file.call_args.kwargs
        self.assertEqual(call_kwargs["keyterm"], keyterms)


if __name__ == '__main__':
    unittest.main()
