"""
Streaming STT Provider Base Classes.

Defines interfaces for real-time streaming speech-to-text providers
with interim results and semantic endpointing capabilities.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Callable, Optional, List
import asyncio
import logging

logger = logging.getLogger(__name__)


class EndpointingType(Enum):
    """Type of endpointing detection used."""
    SILENCE = "silence"           # Silence-based (VAD)
    ACOUSTIC = "acoustic"         # Acoustic model (utterance boundary)
    SEMANTIC = "semantic"         # LLM-based semantic detection


@dataclass
class InterimResult:
    """
    Interim (partial) transcription result during streaming.
    
    These are fast, low-latency results that may change as more
    audio context is received.
    """
    text: str
    is_final: bool = False
    confidence: float = 0.0
    speaker: Optional[str] = None
    timestamp_ms: int = 0
    
    def __post_init__(self):
        if self.timestamp_ms == 0:
            import time
            self.timestamp_ms = int(time.time() * 1000)


@dataclass
class EndOfTurnEvent:
    """
    End-of-turn detection event from streaming provider.
    
    Indicates that the speaker has finished their turn/utterance
    based on acoustic or semantic analysis.
    """
    final_transcript: str
    confidence: float
    endpointing_type: EndpointingType
    duration_ms: int = 0
    speaker: Optional[str] = None
    # Additional metadata from provider-specific features
    metadata: dict = field(default_factory=dict)


@dataclass
class StreamingConfig:
    """Configuration for streaming STT session."""
    language: str = "en"
    # Endpointing settings
    enable_endpointing: bool = True
    endpointing_timeout_ms: int = 1000  # Silence before triggering end
    # Interim results settings
    emit_interim_results: bool = True
    interim_results_interval_ms: int = 100
    # Audio settings
    sample_rate: int = 16000
    encoding: str = "linear16"  # pcm_s16le
    channels: int = 1
    # Priority control: if False, only emit interim results, no turn signals
    # Used when higher-priority semantic endpointing (e.g., LiveKit) is active
    emit_turn_signals: bool = True
    # Provider-specific options
    extra_options: dict = field(default_factory=dict)


class StreamingSTTProvider(ABC):
    """
    Abstract Base Class for Streaming Speech-to-Text providers.
    
    Streaming providers receive audio in real-time chunks and emit:
    1. InterimResult - Fast, partial transcriptions (may change)
    2. InterimResult(is_final=True) - Finalized segment transcript  
    3. EndOfTurnEvent - Speaker finished their utterance
    
    Usage:
        provider = DeepgramStreamingProvider(api_key)
        
        async with provider.stream(config) as stream:
            # Send audio chunks
            await stream.send_audio(audio_chunk)
            
            # Process results
            async for result in stream.results():
                if isinstance(result, EndOfTurnEvent):
                    handle_turn_complete(result)
                else:
                    handle_interim(result)
    """
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self._is_available = True
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._is_available
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the streaming provider."""
        pass
    
    @property
    @abstractmethod
    def supports_semantic_endpointing(self) -> bool:
        """Whether provider supports semantic (LLM-based) endpointing."""
        pass
    
    @property
    def endpointing_type(self) -> EndpointingType:
        """Type of endpointing this provider uses."""
        if self.supports_semantic_endpointing:
            return EndpointingType.SEMANTIC
        return EndpointingType.ACOUSTIC
    
    @abstractmethod
    async def connect(self, config: StreamingConfig) -> "StreamingSession":
        """
        Establish streaming connection to the provider.
        
        Args:
            config: Streaming configuration
            
        Returns:
            StreamingSession for sending audio and receiving results
        """
        pass
    
    async def stream(self, config: Optional[StreamingConfig] = None) -> "StreamingSession":
        """
        Context manager for streaming session.
        
        Args:
            config: Optional streaming configuration
            
        Returns:
            StreamingSession context manager
        """
        if config is None:
            config = StreamingConfig()
        return await self.connect(config)


class StreamingSession(ABC):
    """
    Active streaming session with an STT provider.
    
    Handles bidirectional communication: sending audio chunks
    and receiving transcription results.
    """
    
    def __init__(self, provider: StreamingSTTProvider, config: StreamingConfig):
        self.provider = provider
        self.config = config
        self._is_connected = False
        self._is_closed = False
        self._result_queue: asyncio.Queue = asyncio.Queue()
        self._callbacks: List[Callable] = []
    
    @property
    def is_connected(self) -> bool:
        """Check if session is connected."""
        return self._is_connected and not self._is_closed
    
    @property
    def needs_reconnection(self) -> bool:
        """
        Check if session needs reconnection due to unhealthy state.
        
        Subclasses should override this to check provider-specific health signals.
        Default implementation checks for internal _needs_reconnection flag.
        """
        return getattr(self, '_needs_reconnection', False)
    
    def mark_needs_reconnection(self) -> None:
        """Mark that this session needs reconnection."""
        self._needs_reconnection = True  # type: ignore
    
    def clear_reconnection_flag(self) -> None:
        """Clear reconnection flag after successful reconnect."""
        self._needs_reconnection = False  # type: ignore
    
    @abstractmethod
    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio chunk to the provider.
        
        Args:
            audio_data: Raw audio bytes (PCM 16-bit, mono, 16kHz)
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the streaming session and cleanup resources."""
        pass
    
    @abstractmethod
    async def finalize(self) -> Optional[EndOfTurnEvent]:
        """
        Signal end of audio stream and get final result.
        
        Call this when you know the speaker has stopped
        (e.g., from external VAD) to flush any pending audio.
        
        Returns:
            Final EndOfTurnEvent if transcript pending, None otherwise
        """
        pass
    
    def results(self) -> AsyncGenerator[InterimResult | EndOfTurnEvent, None]:
        """
        Async generator for streaming results.
        
        Yields:
            InterimResult for partial/final transcripts
            EndOfTurnEvent when speaker turn ends
        """
        return self._result_generator()
    
    async def _result_generator(self) -> AsyncGenerator[InterimResult | EndOfTurnEvent, None]:
        """Internal generator implementation."""
        while self.is_connected or not self._result_queue.empty():
            try:
                result = await asyncio.wait_for(
                    self._result_queue.get(),
                    timeout=0.1
                )
                yield result
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in result generator: {e}")
                break
    
    async def _emit_result(self, result: InterimResult | EndOfTurnEvent) -> None:
        """Emit a result to the queue and callbacks."""
        await self._result_queue.put(result)
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def on_result(self, callback: Callable) -> None:
        """
        Register callback for results.
        
        Callback receives InterimResult or EndOfTurnEvent.
        """
        self._callbacks.append(callback)
    
    async def __aenter__(self) -> "StreamingSession":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
