"""
Deepgram Streaming STT Provider.

Uses Deepgram's SDK v5.x WebSocket client for real-time streaming transcription
with Nova-3 model.

Features:
- Real-time interim results (~150ms latency)
- utterance_end_ms for acoustic-based endpointing
- Smart formatting for numbers, dates, etc.
- Built-in keep-alive and reconnection
- Typed event handling
"""
import asyncio
import logging
import time
from typing import Optional, List, Any, TYPE_CHECKING

from .streaming_base import (
    StreamingSTTProvider,
    StreamingSession,
    StreamingConfig,
    InterimResult,
    EndOfTurnEvent,
    EndpointingType,
)

logger = logging.getLogger(__name__)

# SDK imports with fallback for type checking
SDK_AVAILABLE = False
try:
    from deepgram import AsyncDeepgramClient
    from deepgram.core.events import EventType
    SDK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Failed to import deepgram SDK: {e}")
    AsyncDeepgramClient = Any  # type: ignore
    EventType = Any  # type: ignore


class DeepgramStreamingProvider(StreamingSTTProvider):
    """
    Deepgram streaming STT provider using SDK v5.x WebSocket client.
    
    Uses Nova-3 model (Gen 1 Flagship) with utterance_end_ms for detecting
    when speaker has finished an utterance based on acoustic analysis.
    
    Pricing: ~$0.0077/min (Nova-3 streaming)
    Latency: P50 ~150ms for interim results
    """
    
    DEFAULT_MODEL = "nova-3"
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "nova-3",
        keyterms: Optional[List[str]] = None,
    ):
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL
        self.keyterms = keyterms or []
        
        if not SDK_AVAILABLE:
            raise ImportError(
                "deepgram-sdk is required for Deepgram streaming. "
                "Install with: pip install deepgram-sdk"
            )
        
        # Create async client for WebSocket connections
        self._client = AsyncDeepgramClient(api_key=api_key)
    
    @property
    def provider_name(self) -> str:
        return "deepgram"
    
    @property
    def supports_semantic_endpointing(self) -> bool:
        """Deepgram Nova-3 uses acoustic endpointing, not semantic."""
        return False
    
    async def connect(self, config: StreamingConfig) -> "DeepgramStreamingSession":
        """Establish WebSocket connection to Deepgram using SDK."""
        session = DeepgramStreamingSession(self, config)
        await session._connect()
        return session


class DeepgramStreamingSession(StreamingSession):
    """
    Active streaming session with Deepgram using SDK v5.x WebSocket client.
    
    Manages connection lifecycle, audio streaming, and event handling using
    the SDK's typed event system.
    """
    
    # Keepalive interval in seconds (Deepgram timeout is ~10s, send keepalive every 5s)
    KEEPALIVE_INTERVAL_S = 5.0
    
    def __init__(self, provider: DeepgramStreamingProvider, config: StreamingConfig):
        super().__init__(provider, config)
        self._connection: Any = None  # SDK AsyncV1SocketClient
        self._context_manager: Any = None  # Store context manager for cleanup
        self._transcript_buffer: str = ""
        self._start_time_ms: int = 0
        self._last_audio_time_ms: int = 0
        self._keepalive_task: Optional[asyncio.Task] = None
    
    async def _connect(self) -> None:
        """Establish WebSocket connection using SDK v5.x."""
        provider: DeepgramStreamingProvider = self.provider  # type: ignore
        
        # Build connection kwargs - all values must be strings per SDK signature
        connect_kwargs: dict[str, Any] = {
            "model": provider.model,
        }
        
        # Optional parameters
        if self.config.language:
            connect_kwargs["language"] = self.config.language
        
        connect_kwargs["punctuate"] = "true"
        connect_kwargs["smart_format"] = "true"
        
        if self.config.encoding:
            connect_kwargs["encoding"] = self.config.encoding
        if self.config.sample_rate:
            connect_kwargs["sample_rate"] = str(self.config.sample_rate)
        if self.config.channels:
            connect_kwargs["channels"] = str(self.config.channels)
        
        # Enable interim results
        if self.config.emit_interim_results:
            connect_kwargs["interim_results"] = "true"
        
        # Enable endpointing with configurable timeout
        if self.config.enable_endpointing:
            timeout_ms = self.config.extra_options.get(
                "utterance_end_ms", 
                self.config.endpointing_timeout_ms
            )
            connect_kwargs["utterance_end_ms"] = str(timeout_ms)
        
        # Add keyterms for vocabulary boosting (Nova-3 only)
        if provider.keyterms and "nova-3" in provider.model:
            # Keyterms are passed as comma-separated or repeated params
            connect_kwargs["keyterm"] = ",".join(provider.keyterms)
        
        # Diarization if requested
        if self.config.extra_options.get("diarize"):
            connect_kwargs["diarize"] = "true"
        
        try:
            # SDK returns an async context manager from connect()
            self._context_manager = provider._client.listen.v1.connect(**connect_kwargs)
            self._connection = await self._context_manager.__aenter__()
            
            # Register event handlers using SDK's event system
            self._connection.on(EventType.OPEN, self._on_open)
            self._connection.on(EventType.MESSAGE, self._on_message)
            self._connection.on(EventType.CLOSE, self._on_close)
            self._connection.on(EventType.ERROR, self._on_error)
            
            # Start listening for events in background
            await self._connection.start_listening()
            
            self._is_connected = True
            self._start_time_ms = int(time.time() * 1000)
            
            # Start keepalive task to prevent timeout during silence
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            
            logger.info(f"Deepgram streaming connected via SDK: model={provider.model}")
            
        except Exception as e:
            self._is_connected = False
            self.provider._is_available = False
            logger.error(f"Failed to connect to Deepgram: {e}")
            raise ConnectionError(f"Failed to connect to Deepgram: {e}")
    
    def _on_open(self, _: Any) -> None:
        """Handle connection opened."""
        logger.debug("Deepgram WebSocket connection opened")
    
    def _on_message(self, message: Any) -> None:
        """Handle incoming message from Deepgram."""
        # Run async handler in event loop
        asyncio.create_task(self._handle_message_async(message))
    
    def _on_close(self, _: Any) -> None:
        """Handle connection closed."""
        logger.info("Deepgram WebSocket connection closed")
        self._is_connected = False
    
    def _on_error(self, error: Any) -> None:
        """Handle connection error."""
        logger.error(f"Deepgram WebSocket error: {error}")
    
    async def _handle_message_async(self, message: Any) -> None:
        """Process incoming message asynchronously."""
        if self._is_closed:
            return
        
        try:
            msg_type = getattr(message, 'type', None)
            
            if msg_type == 'Results' or hasattr(message, 'channel'):
                await self._handle_results(message)
            elif msg_type == 'UtteranceEnd':
                await self._handle_utterance_end(message)
            elif msg_type == 'SpeechStarted':
                logger.debug("Deepgram: Speech started")
            elif msg_type == 'Metadata':
                logger.debug("Deepgram metadata received")
            elif msg_type == 'Error':
                error_msg = getattr(message, 'error', {})
                logger.error(f"Deepgram error: {error_msg}")
            else:
                logger.debug(f"Deepgram message: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling Deepgram message: {e}")
    
    async def _handle_results(self, data: Any) -> None:
        """Handle transcription results."""
        channel = getattr(data, 'channel', None)
        if not channel:
            return
            
        alternatives = getattr(channel, 'alternatives', [])
        if not alternatives:
            return
        
        alt = alternatives[0]
        transcript = getattr(alt, 'transcript', "") or ""
        confidence = getattr(alt, 'confidence', 0.0) or 0.0
        is_final = getattr(data, 'is_final', False)
        speech_final = getattr(data, 'speech_final', False)
        
        if not transcript:
            return
        
        # Create interim result
        result = InterimResult(
            text=transcript,
            is_final=is_final or speech_final,
            confidence=confidence,
            timestamp_ms=int(time.time() * 1000),
        )
        
        # Update buffer for final results
        if is_final or speech_final:
            self._transcript_buffer = transcript
        
        await self._emit_result(result)
        
        logger.debug(
            f"Deepgram result: {'[FINAL]' if result.is_final else '[interim]'} "
            f"({confidence:.2f}) {transcript[:50]}..."
        )
    
    async def _handle_utterance_end(self, data: Any) -> None:
        """Handle UtteranceEnd event from Deepgram."""
        duration_ms = int(time.time() * 1000) - self._start_time_ms
        last_word_end = getattr(data, 'last_word_end', 0)
        
        if self._transcript_buffer.strip():
            event = EndOfTurnEvent(
                final_transcript=self._transcript_buffer.strip(),
                confidence=0.90,  # Utterance end is high confidence
                endpointing_type=EndpointingType.ACOUSTIC,
                duration_ms=duration_ms,
                metadata={
                    "source": "utterance_end",
                    "last_word_end": last_word_end,
                }
            )
            
            await self._emit_result(event)
            
            # Reset buffer for next utterance
            self._transcript_buffer = ""
            self._start_time_ms = int(time.time() * 1000)
            
            logger.info(
                f"Deepgram utterance end: {event.final_transcript[:50]}... "
                f"(duration={duration_ms}ms)"
            )
    
    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk to Deepgram."""
        if not self.is_connected or self._connection is None:
            raise RuntimeError("Not connected to Deepgram")
        
        try:
            # SDK's send_media accepts raw bytes
            await self._connection.send_media(audio_data)
            self._last_audio_time_ms = int(time.time() * 1000)
        except Exception as e:
            logger.error(f"Error sending audio to Deepgram: {e}")
            await self.close()
            raise
    
    async def _keepalive_loop(self) -> None:
        """
        Background task to send periodic keepalive messages.
        
        Deepgram closes connections that receive no data for ~10-15 seconds.
        Since Browser VAD filters silence before sending to server, we need
        to send explicit KeepAlive messages during quiet periods.
        """
        try:
            from deepgram.extensions.types.sockets import ListenV1ControlMessage  # type: ignore
            
            while self.is_connected and not self._is_closed:
                await asyncio.sleep(self.KEEPALIVE_INTERVAL_S)
                
                if not self.is_connected or self._is_closed or self._connection is None:
                    break
                
                try:
                    control = ListenV1ControlMessage(type="KeepAlive")
                    await self._connection.send_control(control)
                    logger.debug("Deepgram keepalive sent")
                except Exception as e:
                    logger.warning(f"Deepgram keepalive failed: {e}")
                    break
                    
        except asyncio.CancelledError:
            logger.debug("Deepgram keepalive task cancelled")
        except Exception as e:
            logger.warning(f"Deepgram keepalive loop error: {e}")
    
    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._is_closed = True
        self._is_connected = False
        
        # Cancel keepalive task first
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
        
        if self._connection and self._context_manager:
            try:
                # Send close control message
                from deepgram.extensions.types.sockets import ListenV1ControlMessage  # type: ignore
                control = ListenV1ControlMessage(type="CloseStream")
                await self._connection.send_control(control)
            except Exception as e:
                logger.debug(f"Error sending close control: {e}")
            
            try:
                # Exit the async context manager properly
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing Deepgram connection: {e}")
            
            self._connection = None
            self._context_manager = None
        
        logger.info("Deepgram streaming session closed")
    
    async def finalize(self) -> Optional[EndOfTurnEvent]:
        """Signal end of audio and get final result."""
        if not self.is_connected or self._connection is None:
            return None
        
        try:
            # Send finalize control message
            from deepgram.extensions.types.sockets import ListenV1ControlMessage  # type: ignore
            control = ListenV1ControlMessage(type="FinishStream")
            await self._connection.send_control(control)
            
            # Wait briefly for final results
            await asyncio.sleep(0.5)
            
            # Return pending transcript if any
            if self._transcript_buffer.strip():
                duration_ms = int(time.time() * 1000) - self._start_time_ms
                return EndOfTurnEvent(
                    final_transcript=self._transcript_buffer.strip(),
                    confidence=0.85,
                    endpointing_type=EndpointingType.ACOUSTIC,
                    duration_ms=duration_ms,
                    metadata={"source": "finalize"}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finalizing Deepgram stream: {e}")
            return None
