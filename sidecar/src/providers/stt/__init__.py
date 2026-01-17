"""
STT Provider implementations.
"""
from .gemini import GeminiSTTProvider
from .groq import GroqSTTProvider
from .deepgram import DeepgramSTTProvider
from .streaming_base import (
    StreamingSTTProvider,
    StreamingSession,
    StreamingConfig,
    InterimResult,
    EndOfTurnEvent,
    EndpointingType,
)
from .deepgram_streaming import DeepgramStreamingProvider
from .assemblyai_streaming import AssemblyAIStreamingProvider
from .openai_realtime import OpenAIRealtimeProvider
from .streaming_manager import StreamingSTTManager, StreamingSTTCallbacks

__all__ = [
    # Batch providers
    "GeminiSTTProvider",
    "GroqSTTProvider", 
    "DeepgramSTTProvider",
    # Streaming base
    "StreamingSTTProvider",
    "StreamingSession",
    "StreamingConfig",
    "InterimResult",
    "EndOfTurnEvent",
    "EndpointingType",
    # Streaming providers
    "DeepgramStreamingProvider",
    "AssemblyAIStreamingProvider",
    "OpenAIRealtimeProvider",
    # Streaming manager
    "StreamingSTTManager",
    "StreamingSTTCallbacks",
]
