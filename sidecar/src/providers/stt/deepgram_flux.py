"""
Deepgram Flux Streaming STT Provider.

Uses Deepgram's Flux model - a Conversational Speech Recognition (CSR) model
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
import json
import logging
import time
from typing import Optional, Dict, Any

from .streaming_base import (
    StreamingSTTProvider,
    StreamingSession,
    StreamingConfig,
    InterimResult,
    EndOfTurnEvent,
    EndpointingType,
)

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None


class DeepgramFluxProvider(StreamingSTTProvider):
    """
    Deepgram Flux streaming STT provider with semantic turn detection.
    
    Flux is Deepgram's first Conversational Speech Recognition (CSR) model,
    optimized for voice agents with built-in turn detection.
    
    Pricing: Similar to Nova-3 (~$0.0077/min)
    Latency: P50 ~100ms for interim results (faster than Nova-3)
    Turn Detection: Semantic (model understands when speaker is done)
    """
    
    # Flux uses v2 API endpoint
    WS_URL = "wss://api.deepgram.com/v2/listen"
    
    # Default model
    DEFAULT_MODEL = "flux-general-en"
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "flux-general-en",
        eot_threshold: float = 0.7,
        eager_eot_threshold: Optional[float] = None,
        eot_timeout_ms: int = 5000,
    ):
        """
        Initialize Deepgram Flux provider.
        
        Args:
            api_key: Deepgram API key
            model: Model name (default: flux-general-en)
            eot_threshold: Confidence for EndOfTurn (0.5-0.9, default 0.7)
            eager_eot_threshold: Confidence for EagerEndOfTurn (0.3-0.9, optional)
            eot_timeout_ms: Max silence before forcing EndOfTurn (default 5000)
        """
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL
        self.eot_threshold = max(0.5, min(0.9, eot_threshold))
        self.eager_eot_threshold = eager_eot_threshold
        self.eot_timeout_ms = eot_timeout_ms
        
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets is required for Deepgram Flux streaming. "
                "Install with: pip install websockets"
            )
    
    @property
    def provider_name(self) -> str:
        return "deepgram-flux"
    
    @property
    def supports_semantic_endpointing(self) -> bool:
        """Flux provides TRUE semantic end-of-turn detection."""
        return True
    
    async def connect(self, config: StreamingConfig) -> "DeepgramFluxSession":
        """Establish WebSocket connection to Deepgram Flux."""
        session = DeepgramFluxSession(self, config)
        await session._connect()
        return session


class DeepgramFluxSession(StreamingSession):
    """
    Active streaming session with Deepgram Flux.
    
    Manages WebSocket connection, audio streaming, and semantic turn events:
    - StartOfTurn: Speaker started talking
    - EagerEndOfTurn: Early prediction speaker may be done (for speculative LLM)
    - TurnResumed: Speaker continued after EagerEndOfTurn (false positive)
    - EndOfTurn: High confidence speaker is done
    """
    
    def __init__(self, provider: DeepgramFluxProvider, config: StreamingConfig):
        super().__init__(provider, config)
        self._ws: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._transcript_buffer: str = ""
        self._turn_index: int = 0
        self._start_time_ms: int = 0
        self._in_turn: bool = False
    
    async def _connect(self) -> None:
        """Establish WebSocket connection to Flux v2 API."""
        provider: DeepgramFluxProvider = self.provider
        
        # Build query parameters for Flux
        params = {
            "model": provider.model,
            "language": self.config.language,
            "punctuate": "true",
            "smart_format": "true",
            "encoding": self.config.encoding,
            "sample_rate": str(self.config.sample_rate),
            "channels": str(self.config.channels),
            # Flux-specific: End-of-turn detection thresholds
            "eot_threshold": str(provider.eot_threshold),
            "eot_timeout_ms": str(provider.eot_timeout_ms),
        }
        
        # Optional eager end-of-turn for speculative processing
        if provider.eager_eot_threshold is not None:
            params["eager_eot_threshold"] = str(provider.eager_eot_threshold)
        
        # Additional options from config
        if self.config.extra_options.get("diarize"):
            params["diarize"] = "true"
        
        # Build URL with query string
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{DeepgramFluxProvider.WS_URL}?{query}"
        
        # Connect with auth header
        headers = {
            "Authorization": f"Token {provider.api_key}"
        }
        
        try:
            self._ws = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=30,  # Flux uses 60s timeout with pings
                ping_timeout=20,
            )
            self._is_connected = True
            self._start_time_ms = int(time.time() * 1000)
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info(f"Deepgram Flux streaming connected: {params}")
            
        except Exception as e:
            self._is_connected = False
            self.provider._is_available = False
            raise ConnectionError(f"Failed to connect to Deepgram Flux: {e}")
    
    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk to Deepgram Flux."""
        if not self.is_connected or self._ws is None:
            raise RuntimeError("Not connected to Deepgram Flux")
        
        try:
            await self._ws.send(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio to Deepgram Flux: {e}")
            await self.close()
            raise
    
    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._is_closed = True
        self._is_connected = False
        
        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing Deepgram Flux connection: {e}")
            self._ws = None
        
        logger.info("Deepgram Flux streaming session closed")
    
    async def finalize(self) -> Optional[EndOfTurnEvent]:
        """Signal end of audio and get final result."""
        if not self.is_connected or self._ws is None:
            return None
        
        try:
            # Send finalize message
            await self._ws.send(json.dumps({"type": "FinishStream"}))
            
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
    
    async def _receive_loop(self) -> None:
        """Background task to receive and parse Flux messages."""
        if self._ws is None:
            return
        
        try:
            async for message in self._ws:
                if self._is_closed:
                    break
                
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from Deepgram Flux: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error handling Deepgram Flux message: {e}")
                    
        except Exception as e:
            if "ConnectionClosed" in str(type(e)):
                logger.info(f"Deepgram Flux connection closed")
            else:
                logger.error(f"Deepgram Flux receive error: {e}")
        finally:
            self._is_connected = False
    
    async def _handle_message(self, data: dict) -> None:
        """Parse and handle a Deepgram Flux message."""
        msg_type = data.get("type")
        
        # Flux uses TurnInfo for turn events
        turn_info = data.get("turn_info", {})
        turn_event = turn_info.get("event")
        
        if turn_event:
            await self._handle_turn_event(turn_event, turn_info, data)
        elif msg_type == "Results" or "channel" in data:
            await self._handle_results(data)
        elif msg_type == "Metadata":
            logger.debug(f"Deepgram Flux metadata: {data}")
        elif msg_type == "Error":
            error = data.get("error", {})
            logger.error(f"Deepgram Flux error: {error.get('message', data)}")
        else:
            logger.debug(f"Deepgram Flux message: {msg_type or 'unknown'}")
    
    async def _handle_turn_event(
        self, 
        event: str, 
        turn_info: Dict[str, Any], 
        data: dict
    ) -> None:
        """
        Handle Flux turn events.
        
        Events:
        - StartOfTurn: Speaker started talking
        - EagerEndOfTurn: Early prediction speaker may be done
        - TurnResumed: Speaker continued (EagerEndOfTurn was wrong)
        - EndOfTurn: High confidence speaker is done
        """
        turn_index = turn_info.get("turn_index", 0)
        confidence = turn_info.get("end_of_turn_confidence", 0.0)
        
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
    
    async def _handle_results(self, data: dict) -> None:
        """Handle transcription results (Update messages in Flux)."""
        channel = data.get("channel", {})
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            return
        
        alt = alternatives[0]
        transcript = alt.get("transcript", "")
        confidence = alt.get("confidence", 0.0)
        is_final = data.get("is_final", False)
        
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
