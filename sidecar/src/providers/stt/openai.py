"""
OpenAI STT Provider.

Implements STTProvider interface using OpenAI's Whisper model
via the AsyncOpenAI client.
"""

import logging
from typing import Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..base import STTProvider, TranscriptionResult

logger = logging.getLogger(__name__)


class OpenAISTTProvider(STTProvider):
    """
    OpenAI STT Provider using Whisper model.
    """
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
            
        if AsyncOpenAI is None:
            raise ImportError("openai package is not installed. Please install it with `pip install openai`.")
            
        self.client = AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio data using OpenAI's Whisper model.
        """
        if not audio_data:
            return TranscriptionResult(text="")

        try:
            # OpenAI requires a filename/file-like object with a name for the API
            # We can't just pass bytes directly without a 'name' attribute in some clients,
            # but AsyncOpenAI handles (filename, bytes) tuples or file-like objects.
            # Let's wrap it in a BytesIO with a name.
            import io
            file_obj = io.BytesIO(audio_data)
            file_obj.name = "audio.wav"  # Whisper expects a filename to determine format

            # Call OpenAI API
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=file_obj,
                language=language,
                response_format="json"
            )
            
            # Extract text
            text = transcript.text if transcript else ""
            
            # OpenAI Whisper API doesn't return confidence scores in standard JSON response
            # So we default to 0.0 or 1.0 (indicating success)
            return TranscriptionResult(
                text=text,
                confidence=1.0 if text else 0.0,
                language=language
            )

        except Exception as e:
            logger.error(f"OpenAI STT Error: {e}")
            raise Exception(f"OpenAI STT Error: {str(e)}")
