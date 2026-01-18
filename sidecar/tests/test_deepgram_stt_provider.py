import unittest
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock deepgram module before importing the provider
sys.modules['deepgram'] = MagicMock()

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import TranscriptionResult
from providers.stt.deepgram import DeepgramSTTProvider

class TestDeepgramSTTProvider(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.api_key = "test_key"
        self.audio_data = b"fake_audio_data"
        
        # Setup mocks for v3 SDK sync client path
        self.mock_client = MagicMock()
        self.mock_listen = MagicMock()
        self.mock_prerecorded = MagicMock()
        self.mock_v1 = MagicMock()
        
        # Chain the mocks: client.listen.prerecorded.v("1")
        self.mock_client.listen = self.mock_listen
        self.mock_listen.prerecorded = self.mock_prerecorded
        self.mock_prerecorded.v.return_value = self.mock_v1
        
        # Setup transcribe_file response (sync, wrapped with asyncio.to_thread in prod)
        self.mock_response = MagicMock()
        self.mock_channel = MagicMock()
        self.mock_alternative = MagicMock()
        self.mock_alternative.transcript = "Hello world"
        self.mock_alternative.confidence = 0.98
        self.mock_channel.alternatives = [self.mock_alternative]
        self.mock_response.results.channels = [self.mock_channel]
        
        # Make transcribe_file return sync value (production wraps with to_thread)
        self.mock_v1.transcribe_file = MagicMock(return_value=self.mock_response)

    @patch('providers.stt.deepgram.DeepgramClient')
    async def test_transcribe_success(self, MockClient):
        # Arrange
        MockClient.return_value = self.mock_client
        provider = DeepgramSTTProvider(self.api_key)
        
        # Act
        result = await provider.transcribe(self.audio_data)
        
        # Assert
        self.assertIsInstance(result, TranscriptionResult)
        self.assertEqual(result.text, "Hello world")
        self.assertEqual(result.confidence, 0.98) # Assuming we map confidence
        
        # Verify client calls
        MockClient.assert_called_with(self.api_key)
        
        # Verify transcription call
        # Check payload
        call_args = self.mock_v1.transcribe_file.call_args
        payload = call_args[0][0]
        self.assertEqual(payload, {'buffer': self.audio_data})
        
        # Check options - now passed as dict, not PrerecordedOptions
        options = call_args[0][1]
        self.assertEqual(options["model"], "nova-3")
        self.assertEqual(options["smart_format"], True)
        self.assertEqual(options["language"], "en")

    @patch('providers.stt.deepgram.DeepgramClient')
    async def test_transcribe_empty_audio(self, MockClient):
        provider = DeepgramSTTProvider(self.api_key)
        result = await provider.transcribe(b"")
        self.assertEqual(result.text, "")

    @patch('providers.stt.deepgram.DeepgramClient')
    async def test_init_raises_error_without_api_key(self, MockClient):
        with self.assertRaises(ValueError):
            DeepgramSTTProvider("")

if __name__ == '__main__':
    unittest.main()
