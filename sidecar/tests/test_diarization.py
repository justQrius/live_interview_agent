import unittest
from unittest.mock import MagicMock, patch
import torch
import numpy as np
import sys
import os

# Add src to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# We need to create the module first or the import will fail completely before tests run
# But TDD says write test first. 
# However, python requires the file to exist to import it.
# So I will assume I will create the file immediately after.
# To make the test "runnable" but failing, I will try to import, and if it fails, the test will fail.

class TestSpeakerRecognizer(unittest.TestCase):
    
    @patch('src.audio.diarization.EncoderClassifier')
    def test_initialization(self, mock_encoder):
        from src.audio.diarization import SpeakerRecognizer
        recognizer = SpeakerRecognizer()
        self.assertIsNotNone(recognizer)
        mock_encoder.from_hparams.assert_called_once()

    @patch('src.audio.diarization.EncoderClassifier')
    def test_create_embedding(self, mock_encoder):
        from src.audio.diarization import SpeakerRecognizer
        
        # Setup mock
        mock_model = MagicMock()
        mock_encoder.from_hparams.return_value = mock_model
        
        # Mock embedding output (batch, time, channels) -> we usually get (batch, embeddings)
        # ECAPA-TDNN returns embeddings. 
        # We'll simulate a tensor output
        mock_output = torch.rand(1, 1, 192)
        mock_model.encode_batch.return_value = mock_output
        
        recognizer = SpeakerRecognizer()
        
        # Create dummy audio chunk (numpy array)
        audio_chunk = np.random.rand(16000) # 1 sec of audio
        
        embedding = recognizer.create_embedding(audio_chunk)
        
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.shape, (192,))
        mock_model.encode_batch.assert_called()

    @patch('src.audio.diarization.EncoderClassifier')
    def test_verify_speaker(self, mock_encoder):
        from src.audio.diarization import SpeakerRecognizer
        
        # Setup mock for initialization
        mock_model = MagicMock()
        mock_encoder.from_hparams.return_value = mock_model
        
        # Mock embedding output for verify_speaker call
        # We need to control what create_embedding returns
        # Since verify_speaker calls create_embedding, and create_embedding calls mock_model.encode_batch
        
        # Let's say we return a specific vector
        mock_vector = torch.tensor([1.0, 0.0]) # Simplified 2D embedding
        # Shape: [1, 1, 2]
        mock_model.encode_batch.return_value = mock_vector.view(1, 1, 2)
        
        recognizer = SpeakerRecognizer()
        
        audio_chunk = np.random.rand(16000)
        reference_embedding = np.array([1.0, 0.0]) # Identical direction
        
        # Case 1: Same speaker (dot product 1.0)
        is_match = recognizer.verify_speaker(audio_chunk, reference_embedding, threshold=0.5)
        self.assertTrue(is_match)
        
        # Case 2: Different speaker
        # For this we need create_embedding to return something else.
        # But since we mocked the class method, we can't easily change it mid-test without side effects unless we use side_effect
        
    @patch('src.audio.diarization.EncoderClassifier')
    def test_verify_speaker_mismatch(self, mock_encoder):
        from src.audio.diarization import SpeakerRecognizer
        
        mock_model = MagicMock()
        mock_encoder.from_hparams.return_value = mock_model
        
        # Return orthogonal vector
        mock_vector = torch.tensor([0.0, 1.0]) 
        mock_model.encode_batch.return_value = mock_vector.view(1, 1, 2)
        
        recognizer = SpeakerRecognizer()
        
        audio_chunk = np.random.rand(16000)
        reference_embedding = np.array([1.0, 0.0]) # Orthogonal to [0, 1]
        
        # Case: Different speaker (dot product 0.0)
        is_match = recognizer.verify_speaker(audio_chunk, reference_embedding, threshold=0.5)
        self.assertFalse(is_match)

if __name__ == '__main__':
    unittest.main()
