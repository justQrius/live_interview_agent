"""
Deepgram STT Provider using Nova-3 model.

Uses AsyncDeepgramClient for native async support with:
- Automatic retry logic for transient failures (408, 429, 5xx)
- Configurable timeouts for long audio files
- Keyterm boosting for interview-specific vocabulary
- Proper error handling with ApiError
"""
import logging
from typing import Optional, List

from ..base import STTProvider, TranscriptionResult

logger = logging.getLogger(__name__)

try:
    from deepgram import AsyncDeepgramClient
    from deepgram.core.api_error import ApiError
except ImportError as e:
    logger.warning(f"Failed to import deepgram: {e}")
    AsyncDeepgramClient = None
    ApiError = Exception  # Fallback for type hints


class DeepgramSTTProvider(STTProvider):
    """
    Deepgram STT Provider using Nova-3 model.
    
    Uses AsyncDeepgramClient for truly async operations with:
    - Automatic retry with exponential backoff
    - Configurable request timeouts
    - Keyterm boosting for specialized vocabulary
    - Smart formatting for numbers, dates, etc.
    """
    
    DEFAULT_MODEL = "nova-3"
    DEFAULT_TIMEOUT_SECONDS = 60
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self, 
        api_key: str, 
        model: str = "nova-3",
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        keyterms: Optional[List[str]] = None,
    ):
        """
        Initialize Deepgram STT provider.
        
        Args:
            api_key: Deepgram API key
            model: Model to use (default: nova-3)
            timeout_seconds: Request timeout (default: 60)
            max_retries: Max retries for transient failures (default: 3)
            keyterms: List of terms to boost (e.g., company names, technical terms)
        """
        if not api_key:
            raise ValueError("API key is required")
            
        if AsyncDeepgramClient is None:
            raise ImportError(
                "deepgram-sdk is not installed. "
                "Please install it with `pip install deepgram-sdk`."
            )
        
        # v5.x SDK: Use AsyncDeepgramClient for native async support
        self.client = AsyncDeepgramClient(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.keyterms = keyterms or []

    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio data using Deepgram's async API.
        
        Args:
            audio_data: Raw audio bytes to transcribe
            language: BCP-47 language code (default: "en")
            
        Returns:
            TranscriptionResult with text, confidence, and language
            
        Raises:
            ApiError: If Deepgram API returns an error
            Exception: For other failures
        """
        if not audio_data:
            return TranscriptionResult(text="")

        try:
            # Build request options with retry and timeout config
            request_options = {
                "timeout_in_seconds": self.timeout_seconds,
                "max_retries": self.max_retries,
            }
            
            # Build transcription kwargs
            transcribe_kwargs = {
                "request": audio_data,
                "model": self.model,
                "smart_format": True,
                "language": language,
                "punctuate": True,
                "request_options": request_options,
            }
            
            # Add keyterms if configured (Nova-3 only)
            if self.keyterms and "nova-3" in self.model:
                transcribe_kwargs["keyterm"] = self.keyterms
            
            # v5.x async API: await client.listen.v1.media.transcribe_file()
            response = await self.client.listen.v1.media.transcribe_file(
                **transcribe_kwargs
            )
            
            # Response can be ListenV1Response (sync) or ListenV1AcceptedResponse (callback)
            # We use sync mode (no callback param), so we get ListenV1Response with results
            results = getattr(response, 'results', None)
            if results is None:
                logger.warning("Deepgram response missing 'results' - may be callback mode")
                return TranscriptionResult(text="")
            
            channels = getattr(results, 'channels', None)
            if not channels or len(channels) == 0:
                return TranscriptionResult(text="")
                
            alternatives = getattr(channels[0], 'alternatives', None)
            if not alternatives or len(alternatives) == 0:
                return TranscriptionResult(text="")
            
            alternative = alternatives[0]
            text = getattr(alternative, 'transcript', None) or ""
            confidence = getattr(alternative, 'confidence', 0.0) or 0.0
            
            # Log detected language if available
            detected_language = getattr(channels[0], 'detected_language', None)
            if detected_language:
                logger.debug(f"Deepgram detected language: {detected_language}")
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=detected_language or language
            )
            
        except ApiError as e:
            # Structured error from Deepgram API
            logger.error(
                f"Deepgram API error: status={e.status_code}, "
                f"message={getattr(e, 'message', str(e))}"
            )
            raise
            
        except Exception as e:
            logger.error(f"Deepgram transcription failed: {e}")
            raise
