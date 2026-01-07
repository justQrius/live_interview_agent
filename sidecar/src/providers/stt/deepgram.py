from typing import Optional
from ..base import STTProvider, TranscriptionResult

try:
    from deepgram import DeepgramClient, PrerecordedOptions
except ImportError:
    DeepgramClient = None
    PrerecordedOptions = None

class DeepgramSTTProvider(STTProvider):
    """
    Deepgram STT Provider using Nova-2 model.
    """
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
            
        if DeepgramClient is None:
            raise ImportError("deepgram-sdk is not installed. Please install it with `pip install deepgram-sdk`.")
            
        self.client = DeepgramClient(api_key)

    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio data using Deepgram's Nova-2 model.
        """
        if not audio_data:
            return TranscriptionResult(text="")

        try:
            # Prepare source
            payload = {'buffer': audio_data}
            
            # Prepare options
            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
                language=language
            )
            
            # Call Deepgram API
            response = await self.client.listen.asyncprerecorded.v("1").transcribe_file(payload, options)
            
            # Extract transcript
            # response structure: response.results.channels[0].alternatives[0].transcript
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
                return TranscriptionResult(text="", language=language)

        except Exception as e:
            raise Exception(f"Deepgram STT Error: {str(e)}")
