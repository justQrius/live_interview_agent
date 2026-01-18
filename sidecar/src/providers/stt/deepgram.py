from typing import Optional
from ..base import STTProvider, TranscriptionResult

try:
    from deepgram import DeepgramClient
except ImportError as e:
    # Log the specific error to help debug dependency issues
    import logging
    logging.getLogger(__name__).warning(f"Failed to import deepgram: {e}")
    DeepgramClient = None

class DeepgramSTTProvider(STTProvider):
    """
    Deepgram STT Provider using Nova-2/3 model.
    """
    
    DEFAULT_MODEL = "nova-3"

    def __init__(self, api_key: str, model: str = "nova-3"):
        if not api_key:
            raise ValueError("API key is required")
            
        if DeepgramClient is None:
            raise ImportError("deepgram-sdk is not installed. Please install it with `pip install deepgram-sdk`.")
            
        self.client = DeepgramClient(api_key)
        self.model = model or self.DEFAULT_MODEL

    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio data using Deepgram.
        """
        if not audio_data:
            return TranscriptionResult(text="")

        try:
            # Prepare source
            payload = {'buffer': audio_data}
            
            # Prepare options (as dict for SDK v3+ compatibility)
            options = {
                "model": self.model,
                "smart_format": True,
                "language": language
            }
            
            # Call Deepgram API
            # v3 SDK usage: deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
            # Or asyncprerecorded if available?
            # v3 usually exposes .listen.prerecorded.v("1") or .listen.asyncprerecorded.v("1")
            
            # Use async client if possible, but DeepgramClient might be sync wrapper?
            # Deepgram SDK v3 handles async via async client or sync client.
            # Here we initialized DeepgramClient(api_key).
            # If we want async, we might need to use AsyncDeepgramClient or call via thread.
            
            # Assuming client.listen.prerecorded... is sync, we run in thread.
            
            def _call_api():
                return self.client.listen.prerecorded.v("1").transcribe_file(payload, options)

            import asyncio
            response = await asyncio.to_thread(_call_api)
            
            # Extract transcript
            # response.results.channels[0].alternatives[0].transcript
            # In v3, response is an object, not dict.
            
            if (response.results and 
                response.results.channels and 
                response.results.channels[0].alternatives):
                
                alternative = response.results.channels[0].alternatives[0]
                text = alternative.transcript
                confidence = alternative.confidence if hasattr(alternative, 'confidence') else 0.0
                
                return TranscriptionResult(
                    text=text,
                    confidence=confidence,
                    language=language
                )
            else:
                return TranscriptionResult(text="")
                
        except Exception as e:
            # ... existing error handling ...
            import logging
            logging.getLogger(__name__).error(f"Deepgram transcription failed: {e}")
            raise
