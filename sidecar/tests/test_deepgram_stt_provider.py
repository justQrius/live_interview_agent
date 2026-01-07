import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock deepgram module before importing the provider
sys.modules['deepgram'] = MagicMock()

from sidecar.src.providers.stt.deepgram import DeepgramSTTProvider
from sidecar.src.providers.base import TranscriptionResult

class TestDeepgramSTTProvider(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.api_key = "test_key"
        self.audio_data = b"fake_audio_data"
        
        # Setup mocks
        self.mock_client = MagicMock()
        self.mock_listen = MagicMock()
        self.mock_asyncprerecorded = MagicMock()
        self.mock_v1 = MagicMock()
        
        # Chain the mocks: client.listen.asyncprerecorded.v("1")
        self.mock_client.listen = self.mock_listen
        self.mock_listen.asyncprerecorded = self.mock_asyncprerecorded
        self.mock_asyncprerecorded.v.return_value = self.mock_v1
        
        # Setup transcribe_file response
        self.mock_response = MagicMock()
        self.mock_channel = MagicMock()
        self.mock_alternative = MagicMock()
        self.mock_alternative.transcript = "Hello world"
        self.mock_alternative.confidence = 0.98
        self.mock_channel.alternatives = [self.mock_alternative]
        self.mock_response.results.channels = [self.mock_channel]
        
        # Make transcribe_file async
        self.mock_v1.transcribe_file = AsyncMock(return_value=self.mock_response)

    @patch('sidecar.src.providers.stt.deepgram.DeepgramClient')
    @patch('sidecar.src.providers.stt.deepgram.PrerecordedOptions')
    async def test_transcribe_success(self, MockOptions, MockClient):
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
        
        # Check options
        MockOptions.assert_called_with(
            model="nova-2",
            smart_format=True,
            language="en"
        )

    @patch('sidecar.src.providers.stt.deepgram.DeepgramClient')
    async def test_transcribe_empty_audio(self, MockClient):
        provider = DeepgramSTTProvider(self.api_key)
        result = await provider.transcribe(b"")
        self.assertEqual(result.text, "")

    @patch('sidecar.src.providers.stt.deepgram.DeepgramClient')
    async def test_init_raises_error_without_api_key(self, MockClient):
        with self.assertRaises(ValueError):
            DeepgramSTTProvider("")

if __name__ == '__main__':
    unittest.main()
