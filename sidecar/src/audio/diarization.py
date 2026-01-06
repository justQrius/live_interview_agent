import os
import numpy as np
import torch
import logging
import torchaudio

# Patch for torchaudio > 2.1 where list_audio_backends is removed
# SpeechBrain 1.0.3 relies on this function.
if not hasattr(torchaudio, "list_audio_backends"):
    def _list_audio_backends():
        # Minimal return to satisfy SpeechBrain check
        return ["soundfile"]
    torchaudio.list_audio_backends = _list_audio_backends

from speechbrain.inference.speaker import EncoderClassifier

logger = logging.getLogger(__name__)

class SpeakerRecognizer:
    def __init__(self, model_source="speechbrain/spkrec-ecapa-voxceleb"):
        # Use a local cache directory for models to keep them inside the project structure
        # or rely on default ~/.cache/speechbrain. 
        # Using default is safer for libraries, but here we might want to control it.
        # Let's use the default for now to avoid permission issues or path complexity.
        
        try:
            self.classifier = EncoderClassifier.from_hparams(
                source=model_source,
                run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"}
            )
            logger.info(f"SpeakerRecognizer initialized with {model_source}")
        except Exception as e:
            logger.error(f"Failed to initialize SpeakerRecognizer: {e}")
            raise

    def create_embedding(self, audio_chunk: np.ndarray) -> np.ndarray:
        """
        Create speaker embedding from audio chunk.
        
        Args:
            audio_chunk: 1D numpy array. Can be int16 or float32.
                        If int16, it will be normalized to float [-1, 1].
                        Assumes 16kHz sample rate.
        
        Returns:
            1D numpy array (embedding vector), usually size 192.
        """
        # Normalize if int16
        if audio_chunk.dtype == np.int16:
            wavs = audio_chunk.astype(np.float32) / 32768.0
        else:
            wavs = audio_chunk.astype(np.float32)

        # Convert to torch tensor
        wavs_tensor = torch.from_numpy(wavs)

        # Add batch dimension [batch, time]
        if len(wavs_tensor.shape) == 1:
            wavs_tensor = wavs_tensor.unsqueeze(0)

        # Compute embedding
        # encode_batch returns [batch, 1, embedding_dim]
        embeddings = self.classifier.encode_batch(wavs_tensor)
        
        # Squeeze to get [embedding_dim]
        return embeddings.squeeze().detach().cpu().numpy()

    def verify_speaker(self, audio_chunk: np.ndarray, reference_embedding: np.ndarray, threshold: float = 0.75) -> bool:
        """
        Verify if audio_chunk belongs to the speaker with reference_embedding.
        
        Args:
            audio_chunk: Audio data (numpy array)
            reference_embedding: Pre-computed embedding of the target speaker
            threshold: Cosine similarity threshold (default 0.75)
            
        Returns:
            True if similarity >= threshold, False otherwise.
        """
        try:
            new_embedding = self.create_embedding(audio_chunk)
            
            # Cosine similarity
            # Flatten to ensure 1D arrays
            emb1 = new_embedding.flatten()
            emb2 = reference_embedding.flatten()
            
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero norm embedding encountered in verify_speaker")
                return False
                
            score = np.dot(emb1, emb2) / (norm1 * norm2)
            
            return score >= threshold
            
        except Exception as e:
            logger.error(f"Error in verify_speaker: {e}")
            return False
