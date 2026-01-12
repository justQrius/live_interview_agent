"""
Gemini STT Provider.

Implements STTProvider interface using Google's Gemini model
for speech-to-text transcription via the unified google-genai SDK.
"""

import io
import logging
import wave
import base64
from typing import Any, Optional

from google import genai
from google.genai import types

from ..base import STTProvider, TranscriptionResult

# Import SAMPLE_RATE from capture module (single source of truth)
try:
    from src.audio.capture import SAMPLE_RATE
except ImportError:
    # Fallback if audio module not available (e.g., in tests)
    SAMPLE_RATE = 16000

logger = logging.getLogger(__name__)


class GeminiSTTProviderError(Exception):
    """Exception raised when Gemini STT provider operations fail."""
    pass


class GeminiSTTProvider(STTProvider):
    """
    Speech-to-Text provider using Google Gemini.

    Implements the STTProvider interface for the provider factory system.
    Uses the unified google-genai SDK (consistent with GeminiClient).

    Usage:
        provider = GeminiSTTProvider(api_key="...")
        result = await provider.transcribe(audio_bytes)
        print(result.text)
    """

    DEFAULT_MODEL = "gemini-3-flash-preview"

    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        Initialize Gemini STT provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-3-flash-preview)

        Raises:
            ValueError: If API key is empty
            GeminiSTTProviderError: If client initialization fails
        """
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._model_name = model_name or self.DEFAULT_MODEL
        self._available = False
        self._client = None

        try:
            self._client = genai.Client(api_key=api_key)
            self._available = True
            logger.info(f"Initialized Gemini STT provider with model {self._model_name}")
        except Exception as e:
            raise GeminiSTTProviderError(f"Failed to initialize Gemini client: {e}")

    def is_available(self) -> bool:
        """
        Check if the provider is available.

        Returns:
            True if the provider is ready to accept requests
        """
        return self._available

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """
        Convert raw PCM audio to WAV format in memory.

        Args:
            pcm_data: Raw 16kHz mono 16-bit PCM audio

        Returns:
            bytes: WAV formatted audio data
        """
        buffer = io.BytesIO()
        try:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(pcm_data)
            return buffer.getvalue()
        except Exception as e:
            raise GeminiSTTProviderError(f"Failed to convert PCM to WAV: {e}")

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en"
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw 16kHz mono 16-bit PCM audio
            language: Language code (default "en")

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            GeminiSTTProviderError: If transcription fails
        """
        if not audio_data:
            return TranscriptionResult(text="", language=language)

        try:
            # Convert PCM to WAV
            wav_data = self._pcm_to_wav(audio_data)

            # Prompt for transcription
            prompt = (
                "Transcribe the following audio exactly as spoken. "
                "Do not add any commentary, timestamps, or speaker labels. "
                "Just the text."
            )

            if not self._client:
                raise GeminiSTTProviderError("Gemini client is not initialized")

            # Create inline audio data part using google-genai SDK
            audio_part = types.Part.from_bytes(
                data=wav_data,
                mime_type="audio/wav"
            )

            # Generate content using the unified SDK
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=[prompt, audio_part]
            )

            text = ""
            if response.text:
                text = response.text.strip()

            return TranscriptionResult(
                text=text,
                language=language,
                confidence=0.0,  # Gemini doesn't provide confidence scores
            )

        except GeminiSTTProviderError:
            raise
        except Exception as e:
            logger.error(f"Gemini STT error: {e}")
            raise GeminiSTTProviderError(f"Transcription failed: {e}")
