"""
Gemini STT (Speech-to-Text) module.

Uses Google's Gemini 1.5 Flash model to transcribe audio.
Converts raw PCM audio to WAV format before sending to the API.
"""

import io
import logging
import wave
from typing import Optional

import google.generativeai as genai

# Import SAMPLE_RATE from capture module (single source of truth)
from audio.capture import SAMPLE_RATE

# Configure logging
logger = logging.getLogger(__name__)


class GeminiSTTError(Exception):
    """Exception raised when STT fails."""
    pass


class GeminiSTT:
    """
    Speech-to-Text client using Google Gemini.
    
    Usage:
        stt = GeminiSTT(api_key="...")
        text = await stt.transcribe(audio_bytes)
    """

    def __init__(self, api_key: str, model_name: str = "gemini-3-flash-preview"):
        """
        Initialize Gemini STT client.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-3-flash-preview)
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.model_name = model_name
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            raise GeminiSTTError(f"Failed to initialize Gemini client: {e}")

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
            raise GeminiSTTError(f"Failed to convert PCM to WAV: {e}")

    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio using Gemini.

        Args:
            audio_bytes: Raw 16kHz mono 16-bit PCM audio

        Returns:
            str: Transcribed text
            
        Raises:
            GeminiSTTError: If transcription fails
        """
        if not audio_bytes:
            return ""

        try:
            # Convert PCM to WAV
            wav_data = self._pcm_to_wav(audio_bytes)

            # Prompt for transcription
            prompt = "Transcribe the following audio exactly as spoken. Do not add any commentary, timestamps, or speaker labels. Just the text."

            # Generate content asynchronously
            response = await self.model.generate_content_async(
                [
                    prompt,
                    {
                        "mime_type": "audio/wav",
                        "data": wav_data
                    }
                ]
            )
            
            if response.text:
                return response.text.strip()
            return ""
            
        except Exception as e:
            logger.error(f"Gemini STT error: {e}")
            raise GeminiSTTError(f"Transcription failed: {e}")
