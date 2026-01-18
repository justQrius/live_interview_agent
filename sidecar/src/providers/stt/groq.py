import asyncio
import io
from typing import Optional
from ..base import STTProvider, TranscriptionResult

try:
    from groq import Groq
except ImportError:
    Groq = None

class GroqSTTProvider(STTProvider):
    """
    Groq STT Provider using Whisper-large-v3.
    """
    
    DEFAULT_MODEL = "whisper-large-v3"

    def __init__(self, api_key: str, model: str = "whisper-large-v3"):
        if not api_key:
            raise ValueError("API key is required")
        
        if Groq is None:
            raise ImportError("groq package is not installed. Please install it with `pip install groq`.")
            
        self.client = Groq(api_key=api_key)
        self._api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio data using Groq's Whisper-large-v3.
        """
        if not audio_data:
            return TranscriptionResult(text="")

        try:
            # Create a file-like object with a name, as required by Groq API
            # buffer must be recreated inside the thread if passing bytes, 
            # but BytesIO is not thread-safe? Actually it is just memory.
            # Passing the data to the thread.
            
            def _call_api():
                # Re-create BytesIO inside thread to be safe or just pass it?
                # BytesIO is fine to pass if read only.
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "audio.wav"
                
                return self.client.audio.transcriptions.create(
                    file=(audio_file.name, audio_file),
                    model=self.model,
                    # language=language, # whisper-large-v3 on groq might support language
                    # Groq API docs say: language is optional.
                    response_format="json"
                )

            # Run in thread pool to avoid blocking the event loop
            transcription = await asyncio.to_thread(_call_api)

            return TranscriptionResult(
                text=transcription.text,
                language=language
            )

        except Exception as e:
            raise Exception(f"Groq STT Error: {str(e)}")
