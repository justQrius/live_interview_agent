"""
STT Provider implementations.

Simplified in Phase 3 of STT Simplification:
- LocalWhisperProvider: Local GPU-accelerated Whisper (faster-whisper) - PRIMARY
- GeminiSTTProvider: Cloud fallback for native audio processing
- DeepgramStreamingProvider/DeepgramFluxProvider: Streaming STT (user opt-in)
"""
from .gemini import GeminiSTTProvider
from .local_whisper import LocalWhisperProvider
from .streaming_base import (
    StreamingSTTProvider,
    StreamingSession,
    StreamingConfig,
    InterimResult,
    EndOfTurnEvent,
    EndpointingType,
)
from .deepgram_streaming import DeepgramStreamingProvider
from .deepgram_flux import DeepgramFluxProvider
from .streaming_manager import StreamingSTTManager, StreamingSTTCallbacks

__all__ = [
    # Batch providers (simplified)
    "LocalWhisperProvider",  # Primary - local GPU
    "GeminiSTTProvider",     # Cloud fallback
    # Streaming base
    "StreamingSTTProvider",
    "StreamingSession",
    "StreamingConfig",
    "InterimResult",
    "EndOfTurnEvent",
    "EndpointingType",
    # Streaming providers (Deepgram only)
    "DeepgramStreamingProvider",
    "DeepgramFluxProvider",
    # Streaming manager
    "StreamingSTTManager",
    "StreamingSTTCallbacks",
]
