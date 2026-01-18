"""
Deepgram Flux Streaming STT Provider.

Uses Deepgram's Flux model via SDK v5.x - a Conversational Speech Recognition (CSR) model
with semantic turn detection and model-integrated endpointing.

Key Features (vs Nova-3):
- Semantic end-of-turn detection (understands meaning, not just pauses)
- Built-in turn state machine (StartOfTurn, EagerEndOfTurn, TurnResumed, EndOfTurn)
- ~200-600ms latency reduction vs pipeline approaches
- ~30% fewer false interruptions
- Configurable thresholds (eot_threshold, eager_eot_threshold, eot_timeout_ms)

API Endpoint: /v2/listen (vs /v1/listen for Nova-3)
"""
import asyncio
import logging
import time
from typing import Optional, List, Any

from .streaming_base import (
    StreamingSTTProvider,
    StreamingSession,
    StreamingConfig,
    InterimResult,
    EndOfTurnEvent,
    EndpointingType,
)

logger = logging.getLogger(__name__)

# SDK imports with fallback
SDK_AVAILABLE = False
try:
    from deepgram import AsyncDeepgramClient
    from deepgram.core.events import EventType
    SDK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Failed to import deepgram SDK: {e}")
    AsyncDeepgramClient = None  # type: ignore
    EventType = None  # type: ignore


class DeepgramFluxProvider(StreamingSTTProvider):
    """
    Deepgram Flux streaming STT provider with semantic turn detection.
    
    Flux is Deepgram's first Conversational Speech Recognition (CSR) model,
    optimized for voice agents with built-in turn detection.
    
    Pricing: Similar to Nova-3 (~$0.0077/min)
    Latency: P50 ~100ms for interim results (faster than Nova-3)
    Turn Detection: Semantic (model understands when speaker is done)
    """
    
    DEFAULT_MODEL = "flux-general-en"
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "flux-general-en",
        eot_threshold: float = 0.7,
        eager_eot_threshold: Optional[float] = None,
        eot_timeout_ms: int = 5000,
        keyterms: Optional[List[str]] = None,
    ):
        """
        Initialize Deepgram Flux provider.
        
        Args:
            api_key: Deepgram API key
            model: Model name (default: flux-general-en)
            eot_threshold: Confidence for EndOfTurn (0.5-0.9, default 0.7)
            eager_eot_threshold: Confidence for EagerEndOfTurn (0.3-0.9, optional)
            eot_timeout_ms: Max silence before forcing EndOfTurn (default 5000)
            keyterms: List of terms to boost (e.g., company names, technical terms)
        """
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL
        self.eot_threshold = max(0.5, min(0.9, eot_threshold))
        self.eager_eot_threshold = eager_eot_threshold
        self.eot_timeout_ms = eot_timeout_ms
        self.keyterms = keyterms or []
        
        if not SDK_AVAILABLE:
            raise ImportError(
                "deepgram-sdk is required for Deepgram Flux streaming. "
                "Install with: pip install deepgram-sdk"
            )
        
        # Create async client for WebSocket connections
        self._client = AsyncDeepgramClient(api_key=api_key)
    
    @property
    def provider_name(self) -> str:
        return "deepgram-flux"
    
    @property
    def supports_semantic_endpointing(self) -> bool:
        """Flux provides TRUE semantic end-of-turn detection."""
        return True
    
    async def connect(self, config: StreamingConfig) -> "DeepgramFluxSession":
        """Establish WebSocket connection to Deepgram Flux using SDK."""
        session = DeepgramFluxSession(self, config)
        await session._connect()
        return session


class DeepgramFluxSession(StreamingSession):
    """
    Active streaming session with Deepgram Flux using SDK v5.x Listen V2 API.
    
    Handles WebSocket connection, audio streaming, and semantic turn events:
    - StartOfTurn: Speaker started talking
    - EagerEndOfTurn: Early prediction speaker may be done (for speculative LLM)
    - TurnResumed: Speaker continued after EagerEndOfTurn (false positive)
    - EndOfTurn: High confidence speaker is done
    """
    
    def __init__(self, provider: DeepgramFluxProvider, config: StreamingConfig):
        super().__init__(provider, config)
        self._connection: Any = None  # SDK AsyncV2SocketClient
        self._context_manager: Any = None
        self._transcript_buffer: str = ""
        self._turn_index: int = 0
        self._start_time_ms: int = 0
        self._in_turn: bool = False
    
    async def _connect(self) -> None:
        """Establish WebSocket connection using SDK v5.x V2 API."""
        provider: DeepgramFluxProvider = self.provider  # type: ignore
        
        # V2 API requires encoding and sample_rate
        connect_kwargs: dict[str, Any] = {
            "model": provider.model,
            "encoding": self.config.encoding or "linear16",
            "sample_rate": str(self.config.sample_rate or 16000),
            # Flux-specific: End-of-turn detection thresholds
            "eot_threshold": str(provider.eot_threshold),
            "eot_timeout_ms": str(provider.eot_timeout_ms),
        }
        
        # Optional eager end-of-turn for speculative processing
        if provider.eager_eot_threshold is not None:
            connect_kwargs["eager_eot_threshold"] = str(provider.eager_eot_threshold)
        
        # Add keyterms for vocabulary boosting
        if provider.keyterms:
            connect_kwargs["keyterm"] = ",".join(provider.keyterms)
        
        try:
            # SDK V2 connect returns async context manager
            self._context_manager = provider._client.listen.v2.connect(**connect_kwargs)
            self._connection = await self._context_manager.__aenter__()
            
            # Register event handlers
            self._connection.on(EventType.OPEN, self._on_open)
            self._connection.on(EventType.MESSAGE, self._on_message)
            self._connection.on(EventType.CLOSE, self._on_close)
            self._connection.on(EventType.ERROR, self._on_error)
            
            # Start listening for events
            await self._connection.start_listening()
            
            self._is_connected = True
            self._start_time_ms = int(time.time() * 1000)
            
            logger.info(
                f"Deepgram Flux streaming connected: model={provider.model}, "
                f"eot_threshold={provider.eot_threshold}"
            )
            
        except Exception as e:
            self._is_connected = False
            self.provider._is_available = False
            logger.error(f"Failed to connect to Deepgram Flux: {e}")
            raise ConnectionError(f"Failed to connect to Deepgram Flux: {e}")
    
    def _on_open(self, _: Any) -> None:
        """Handle connection opened."""
        logger.debug("Deepgram Flux WebSocket connection opened")
    
    def _on_message(self, message: Any) -> None:
        """Handle incoming message from Deepgram Flux."""
        asyncio.create_task(self._handle_message_async(message))
    
    def _on_close(self, _: Any) -> None:
        """Handle connection closed."""
        logger.info("Deepgram Flux WebSocket connection closed")
        self._is_connected = False
    
    def _on_error(self, error: Any) -> None:
        """Handle connection error."""
        logger.error(f"Deepgram Flux WebSocket error: {error}")
    
    async def _handle_message_async(self, message: Any) -> None:
        """Process incoming Flux message asynchronously."""
        if self._is_closed:
            return
        
        try:
            # Flux uses turn_info for turn events
            turn_info = getattr(message, 'turn_info', None)
            if turn_info:
                turn_event = getattr(turn_info, 'event', None)
                if turn_event:
                    await self._handle_turn_event(turn_event, turn_info, message)
                    return
            
            msg_type = getattr(message, 'type', None)
            
            if msg_type == 'Results' or hasattr(message, 'channel'):
                await self._handle_results(message)
            elif msg_type == 'Metadata':
                logger.debug("Deepgram Flux metadata received")
            elif msg_type == 'Error':
                error_msg = getattr(message, 'error', {})
                logger.error(f"Deepgram Flux error: {error_msg}")
            else:
                logger.debug(f"Deepgram Flux message: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling Deepgram Flux message: {e}")
    
    async def _handle_turn_event(self, event: str, turn_info: Any, data: Any) -> None:
        """
        Handle Flux turn events.
        
        Events:
        - StartOfTurn: Speaker started talking
        - EagerEndOfTurn: Early prediction speaker may be done
        - TurnResumed: Speaker continued (EagerEndOfTurn was wrong)
        - EndOfTurn: High confidence speaker is done
        """
        turn_index = getattr(turn_info, 'turn_index', 0)
        confidence = getattr(turn_info, 'end_of_turn_confidence', 0.0)
        
        if event == "StartOfTurn":
            self._in_turn = True
            self._turn_index = turn_index
            logger.debug(f"Flux StartOfTurn: turn_index={turn_index}")
            
        elif event == "EagerEndOfTurn":
            # Early signal - can be used for speculative LLM prefetch
            logger.info(
                f"Flux EagerEndOfTurn: conf={confidence:.2f}, "
                f"transcript='{self._transcript_buffer[:50]}...'"
            )
            # Don't emit EndOfTurn yet - wait for confirmation or TurnResumed
            
        elif event == "TurnResumed":
            # False positive - speaker continued
            logger.debug(f"Flux TurnResumed: turn_index={turn_index}")
            
        elif event == "EndOfTurn":
            self._in_turn = False
            duration_ms = int(time.time() * 1000) - self._start_time_ms
            
            if self._transcript_buffer.strip():
                eot_event = EndOfTurnEvent(
                    final_transcript=self._transcript_buffer.strip(),
                    confidence=confidence,
                    endpointing_type=EndpointingType.SEMANTIC,
                    duration_ms=duration_ms,
                    metadata={
                        "source": "end_of_turn",
                        "turn_index": turn_index,
                    }
                )
                
                await self._emit_result(eot_event)
                
                logger.info(
                    f"Flux EndOfTurn: conf={confidence:.2f}, "
                    f"transcript='{eot_event.final_transcript[:50]}...'"
                )
                
                # Reset for next turn
                self._transcript_buffer = ""
                self._start_time_ms = int(time.time() * 1000)
    
    async def _handle_results(self, data: Any) -> None:
        """Handle transcription results (Update messages in Flux)."""
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
        
        if not transcript:
            return
        
        # Create interim result
        result = InterimResult(
            text=transcript,
            is_final=is_final,
            confidence=confidence,
            timestamp_ms=int(time.time() * 1000),
        )
        
        # Update buffer for final results
        if is_final:
            self._transcript_buffer = transcript
        
        await self._emit_result(result)
        
        logger.debug(
            f"Flux result: {'[FINAL]' if is_final else '[interim]'} "
            f"({confidence:.2f}) {transcript[:50]}..."
        )
    
    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk to Deepgram Flux."""
        if not self.is_connected or self._connection is None:
            raise RuntimeError("Not connected to Deepgram Flux")
        
        try:
            # SDK's send_media accepts raw bytes for V2 as well
            await self._connection.send_media(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio to Deepgram Flux: {e}")
            await self.close()
            raise
    
    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._is_closed = True
        self._is_connected = False
        
        if self._connection and self._context_manager:
            try:
                # V2 uses different control message type
                from deepgram.extensions.types.sockets import ListenV2ControlMessage
                control = ListenV2ControlMessage(type="CloseStream")
                await self._connection.send_control(control)
            except Exception as e:
                logger.debug(f"Error sending close control: {e}")
            
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing Deepgram Flux connection: {e}")
            
            self._connection = None
            self._context_manager = None
        
        logger.info("Deepgram Flux streaming session closed")
    
    async def finalize(self) -> Optional[EndOfTurnEvent]:
        """Signal end of audio and get final result."""
        if not self.is_connected or self._connection is None:
            return None
        
        try:
            from deepgram.extensions.types.sockets import ListenV2ControlMessage
            control = ListenV2ControlMessage(type="CloseStream")
            await self._connection.send_control(control)
            
            # Wait briefly for final results
            await asyncio.sleep(0.3)
            
            # Return pending transcript if any
            if self._transcript_buffer.strip():
                duration_ms = int(time.time() * 1000) - self._start_time_ms
                return EndOfTurnEvent(
                    final_transcript=self._transcript_buffer.strip(),
                    confidence=0.85,
                    endpointing_type=EndpointingType.SEMANTIC,
                    duration_ms=duration_ms,
                    metadata={"source": "finalize", "turn_index": self._turn_index}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finalizing Deepgram Flux stream: {e}")
            return None
