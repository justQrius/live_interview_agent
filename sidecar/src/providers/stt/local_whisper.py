"""
Local Whisper STT Provider using faster-whisper.

Implements STTProvider interface using faster-whisper for local GPU-accelerated
speech-to-text transcription. Provides ~17-34x faster transcription than cloud STT
with 100% privacy and offline capability.

Optimal for 8GB GPU with CUDA 12.x.
"""

import logging
from typing import Optional

import numpy as np

from ..base import STTProvider, TranscriptionResult

# Import SAMPLE_RATE from capture module (single source of truth)
try:
    from src.audio.capture import SAMPLE_RATE
except ImportError:
    # Fallback if audio module not available (e.g., in tests)
    SAMPLE_RATE = 16000

logger = logging.getLogger(__name__)


class LocalWhisperProviderError(Exception):
    """Exception raised when LocalWhisper provider operations fail."""
    pass


def _check_gpu_available() -> bool:
    """
    Check if CUDA GPU is available for faster-whisper.
    
    Returns:
        True if CUDA is available, False otherwise.
    """
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        logger.warning("PyTorch not available, cannot check GPU availability")
        return False


class LocalWhisperProvider(STTProvider):
    """
    Speech-to-Text provider using faster-whisper (local GPU-accelerated).

    Implements the STTProvider interface for the provider factory system.
    Uses CTranslate2-based Whisper for efficient GPU inference.

    Optimal Configuration for 8GB GPU:
        - Model: large-v3-turbo (best speed/accuracy balance)
        - Compute Type: int8_float16 (40-50% VRAM savings)
        - Expected VRAM: ~1.5-2.5GB (leaves 5.5GB free)
        - Expected Latency: ~100-200ms per segment

    Usage:
        provider = LocalWhisperProvider()  # Auto-detects GPU
        result = await provider.transcribe(audio_bytes)
        print(result.text)
    """

    # Model configurations
    DEFAULT_MODEL = "large-v3-turbo"
    FALLBACK_MODELS = ["distil-large-v3", "medium", "small", "tiny"]
    
    # Compute type configurations (for different GPU memory)
    COMPUTE_TYPES = {
        "high_vram": "float16",       # Best quality, highest VRAM
        "balanced": "int8_float16",   # Recommended for 8GB GPU
        "low_vram": "int8",           # Lowest VRAM usage
    }
    DEFAULT_COMPUTE_TYPE = "int8_float16"  # Optimized for 8GB GPU

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        """
        Initialize LocalWhisper STT provider.

        Args:
            model_size: Whisper model to use (default: large-v3-turbo).
                       Options: tiny, small, medium, large-v3, large-v3-turbo,
                               distil-large-v3
            device: Device to use ("cuda" or "cpu"). Auto-detects if None.
            compute_type: Quantization type (default: int8_float16).
                         Options: float16, int8_float16, int8

        Raises:
            LocalWhisperProviderError: If model loading fails.
        """
        self._model_size = model_size or self.DEFAULT_MODEL
        self._compute_type = compute_type or self.DEFAULT_COMPUTE_TYPE
        self._available = False
        self._model = None
        self._device = device
        
        # Auto-detect device if not specified
        if self._device is None:
            if _check_gpu_available():
                self._device = "cuda"
                logger.info("GPU detected, using CUDA for faster-whisper")
            else:
                self._device = "cpu"
                logger.info("No GPU detected, using CPU for faster-whisper")
                # Adjust compute type for CPU
                if self._compute_type == "int8_float16":
                    self._compute_type = "int8"
                    logger.info("Adjusted compute_type to 'int8' for CPU")

        # Load model
        self._load_model()

    def _load_model(self) -> None:
        """
        Load the faster-whisper model.
        
        Attempts to load the specified model, falling back to smaller models
        if VRAM is insufficient.
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            logger.error(f"faster-whisper not installed: {e}")
            raise LocalWhisperProviderError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )

        models_to_try = [self._model_size] + [
            m for m in self.FALLBACK_MODELS if m != self._model_size
        ]

        for model_name in models_to_try:
            try:
                logger.info(
                    f"Loading faster-whisper model: {model_name} "
                    f"(device={self._device}, compute_type={self._compute_type})"
                )
                
                self._model = WhisperModel(
                    model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                
                self._model_size = model_name
                self._available = True
                logger.info(f"Successfully loaded faster-whisper model: {model_name}")
                return
                
            except Exception as e:
                error_msg = str(e).lower()
                # Check for VRAM-related errors
                if "out of memory" in error_msg or "cuda" in error_msg:
                    logger.warning(
                        f"Failed to load {model_name} (likely VRAM issue): {e}. "
                        f"Trying smaller model..."
                    )
                    continue
                else:
                    logger.error(f"Failed to load model {model_name}: {e}")
                    raise LocalWhisperProviderError(f"Model loading failed: {e}")

        # All models failed
        logger.error("All faster-whisper models failed to load")
        raise LocalWhisperProviderError(
            "Failed to load any faster-whisper model. Check GPU/CUDA installation."
        )

    def is_available(self) -> bool:
        """
        Check if the provider is available.

        Returns:
            True if the model is loaded and ready to use.
        """
        return self._available and self._model is not None

    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model configuration details.
        """
        return {
            "model_size": self._model_size,
            "device": self._device,
            "compute_type": self._compute_type,
            "available": self._available,
        }

    def _pcm_to_float32(self, pcm_data: bytes) -> np.ndarray:
        """
        Convert raw PCM audio (int16) to float32 numpy array for Whisper.

        Args:
            pcm_data: Raw 16kHz mono 16-bit PCM audio bytes.

        Returns:
            numpy.ndarray: Float32 audio array normalized to [-1, 1].
        """
        # Convert bytes to int16 numpy array
        audio_int16 = np.frombuffer(pcm_data, dtype=np.int16)
        
        # Convert to float32 and normalize to [-1, 1]
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        return audio_float32

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en"
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw 16kHz mono 16-bit PCM audio bytes.
            language: Language code (default "en").

        Returns:
            TranscriptionResult with transcribed text and metadata.

        Raises:
            LocalWhisperProviderError: If transcription fails.
        """
        if not audio_data:
            return TranscriptionResult(text="", language=language)

        if not self._available or self._model is None:
            raise LocalWhisperProviderError("Model not loaded or unavailable")

        try:
            # Convert PCM bytes to float32 numpy array
            audio_float32 = self._pcm_to_float32(audio_data)
            
            # Check for very short audio (less than 0.1 seconds)
            if len(audio_float32) < SAMPLE_RATE * 0.1:
                logger.debug("Audio too short for transcription")
                return TranscriptionResult(text="", language=language)

            # Transcribe with faster-whisper
            # beam_size=5 is a good balance of accuracy and speed
            segments, info = self._model.transcribe(
                audio_float32,
                language=language,
                beam_size=5,
                vad_filter=True,  # Filter out non-speech segments
                vad_parameters={
                    "min_speech_duration_ms": 100,
                    "min_silence_duration_ms": 500,
                },
            )

            # Collect all segment texts
            text_parts = []
            avg_confidence = 0.0
            segment_count = 0
            
            for segment in segments:
                text_parts.append(segment.text.strip())
                # avg_logprob is in log space, convert to probability
                # Higher (less negative) logprob = higher confidence
                avg_confidence += 1.0 - abs(segment.avg_logprob)
                segment_count += 1

            full_text = " ".join(text_parts).strip()
            
            # Calculate average confidence
            if segment_count > 0:
                avg_confidence /= segment_count
            else:
                avg_confidence = 0.0

            logger.debug(
                f"Transcribed {len(audio_data)} bytes -> '{full_text[:50]}...' "
                f"(language={info.language}, confidence={avg_confidence:.2f})"
            )

            return TranscriptionResult(
                text=full_text,
                language=info.language or language,
                confidence=avg_confidence,
            )

        except LocalWhisperProviderError:
            raise
        except Exception as e:
            logger.error(f"Local Whisper STT error: {e}")
            raise LocalWhisperProviderError(f"Transcription failed: {e}")
