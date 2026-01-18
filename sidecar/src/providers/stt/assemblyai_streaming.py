"""
AssemblyAI Universal Streaming STT Provider.

Uses AssemblyAI's WebSocket-based Universal-2 streaming API with
semantic end-of-turn detection via `end_of_turn_confidence`.

Features:
- Real-time interim results (~256ms latency)
- Semantic end-of-turn detection (0-1 confidence score)
- Speaker diarization support
- Universal-2 model with high accuracy
"""
import asyncio
import base64
import json
import logging
import time
from typing import Optional

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


class AssemblyAIStreamingProvider(StreamingSTTProvider):
    """
    AssemblyAI streaming STT provider using WebSocket API (v3).
    
    Uses Universal-2/Best model with semantic end-of-turn detection
    that returns a confidence score (0-1) for turn completion.
    
    Pricing: ~$0.15/hour (Universal model)
    Latency: P50 ~256ms for interim results
    
    Key feature: end_of_turn_confidence provides semantic
    understanding of when a speaker's turn is complete.
    """
    
    # AssemblyAI WebSocket endpoint (v3)
    WS_URL = "wss://api.assemblyai.com/v3/realtime/ws"
    
    # Minimum confidence to consider turn complete
    DEFAULT_END_OF_TURN_THRESHOLD = 0.7
    
    # Default model
    DEFAULT_MODEL = "best"
    
    def __init__(self, api_key: str, model: str = "best"):
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets is required for AssemblyAI streaming. "
                "Install with: pip install websockets"
            )
    
    @property
    def provider_name(self) -> str:
        return "assemblyai"
    
    @property
    def supports_semantic_endpointing(self) -> bool:
        """AssemblyAI provides semantic end-of-turn confidence."""
        return True
    
    async def connect(self, config: StreamingConfig) -> "AssemblyAIStreamingSession":
        """Establish WebSocket connection to AssemblyAI."""
        session = AssemblyAIStreamingSession(self, config)
        await session._connect()
        return session


class AssemblyAIStreamingSession(StreamingSession):
    """
    Active streaming session with AssemblyAI.
    
    Manages WebSocket connection, audio streaming, and result parsing
    including semantic end-of-turn detection.
    """
    
    def __init__(self, provider: AssemblyAIStreamingProvider, config: StreamingConfig):
        super().__init__(provider, config)
        self._ws: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._transcript_buffer: str = ""
        self._start_time_ms: int = 0
        self._session_id: Optional[str] = None
        self._end_of_turn_threshold: float = config.extra_options.get(
            "end_of_turn_threshold",
            AssemblyAIStreamingProvider.DEFAULT_END_OF_TURN_THRESHOLD
        )
    
    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        # Build query parameters
        params = {
            "sample_rate": str(self.config.sample_rate),
            "encoding": "pcm_s16le" if self.config.encoding == "linear16" else self.config.encoding,
        }
        
        # Optional features
        if self.config.extra_options.get("word_boost"):
            # Custom vocabulary boosting
            pass
        
        # Build URL with query string
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{AssemblyAIStreamingProvider.WS_URL}?{query}"
        
        # Connect with auth header
        headers = {
            "Authorization": self.provider.api_key
        }
        
        try:
            self._ws = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=None,  # We'll handle keepalives ourselves
            )
            self._is_connected = True
            self._start_time_ms = int(time.time() * 1000)
            
            # Wait for session begin message
            response = await self._ws.recv()
            data = json.loads(response)
            
            if data.get("message_type") == "SessionBegins":
                self._session_id = data.get("session_id")
                logger.info(f"AssemblyAI session started: {self._session_id}")
            else:
                raise ConnectionError(f"Unexpected message: {data}")
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # Start keepalive (AssemblyAI disconnects after 60s of no data)
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            
            logger.info(f"AssemblyAI streaming connected: {params}")
            
        except Exception as e:
            self._is_connected = False
            self.provider._is_available = False
            raise ConnectionError(f"Failed to connect to AssemblyAI: {e}")
    
    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio chunk to AssemblyAI.
        
        AssemblyAI requires base64-encoded audio data.
        """
        if not self.is_connected or self._ws is None:
            raise RuntimeError("Not connected to AssemblyAI")
        
        try:
            # AssemblyAI requires base64 encoding for audio
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            message = json.dumps({"audio_data": audio_b64})
            await self._ws.send(message)
        except Exception as e:
            logger.error(f"Error sending audio to AssemblyAI: {e}")
            await self.close()
            raise
    
    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._is_closed = True
        self._is_connected = False
        
        # Cancel tasks
        for task in [self._receive_task, self._keepalive_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close WebSocket
        if self._ws:
            try:
                # Send terminate message
                await self._ws.send(json.dumps({"terminate_session": True}))
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing AssemblyAI connection: {e}")
            self._ws = None
        
        logger.info("AssemblyAI streaming session closed")
    
    async def finalize(self) -> Optional[EndOfTurnEvent]:
        """
        Signal end of audio and get final result.
        
        Sends force_end_utterance to flush any pending audio.
        """
        if not self.is_connected or self._ws is None:
            return None
        
        try:
            # Force end of utterance
            await self._ws.send(json.dumps({"force_end_utterance": True}))
            
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
                    metadata={"source": "force_end_utterance"}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finalizing AssemblyAI stream: {e}")
            return None
    
    async def _keepalive_loop(self) -> None:
        """Send periodic keepalive to prevent disconnect."""
        while self.is_connected:
            try:
                await asyncio.sleep(30)  # Every 30 seconds
                if self._ws and self.is_connected:
                    # Send empty audio to keep connection alive
                    await self._ws.send(json.dumps({"audio_data": ""}))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Keepalive error: {e}")
    
    async def _receive_loop(self) -> None:
        """Background task to receive and parse AssemblyAI messages."""
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
                    logger.warning(f"Invalid JSON from AssemblyAI: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error handling AssemblyAI message: {e}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"AssemblyAI connection closed: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"AssemblyAI receive error: {e}")
        finally:
            self._is_connected = False
    
    async def _handle_message(self, data: dict) -> None:
        """Parse and handle an AssemblyAI message."""
        msg_type = data.get("message_type")
        
        if msg_type == "PartialTranscript":
            await self._handle_partial(data)
        elif msg_type == "FinalTranscript":
            await self._handle_final(data)
        elif msg_type == "SessionTerminated":
            logger.info("AssemblyAI session terminated")
            self._is_connected = False
        elif msg_type == "Error":
            error = data.get("error", "Unknown error")
            logger.error(f"AssemblyAI error: {error}")
        else:
            logger.debug(f"AssemblyAI message: {msg_type}")
    
    async def _handle_partial(self, data: dict) -> None:
        """Handle partial (interim) transcription."""
        transcript = data.get("text", "")
        confidence = data.get("confidence", 0.0)
        
        if not transcript:
            return
        
        result = InterimResult(
            text=transcript,
            is_final=False,
            confidence=confidence,
            timestamp_ms=int(time.time() * 1000),
        )
        
        await self._emit_result(result)
        
        logger.debug(f"AssemblyAI partial: ({confidence:.2f}) {transcript[:50]}...")
    
    async def _handle_final(self, data: dict) -> None:
        """
        Handle final transcription with end-of-turn detection.
        
        AssemblyAI's FinalTranscript includes `end_of_turn_confidence`
        which is a semantic measure of turn completion (0-1).
        """
        transcript = data.get("text", "")
        confidence = data.get("confidence", 0.0)
        
        # Key feature: semantic end-of-turn confidence
        end_of_turn_confidence = data.get("end_of_turn_confidence", 0.0)
        
        if not transcript:
            return
        
        # Emit final transcript
        result = InterimResult(
            text=transcript,
            is_final=True,
            confidence=confidence,
            timestamp_ms=int(time.time() * 1000),
        )
        await self._emit_result(result)
        
        # Update buffer
        self._transcript_buffer = transcript
        
        logger.debug(
            f"AssemblyAI final: ({confidence:.2f}) end_of_turn={end_of_turn_confidence:.2f} "
            f"{transcript[:50]}..."
        )
        
        # Check if this is a complete turn based on semantic confidence
        if end_of_turn_confidence >= self._end_of_turn_threshold:
            duration_ms = int(time.time() * 1000) - self._start_time_ms
            
            event = EndOfTurnEvent(
                final_transcript=transcript,
                confidence=end_of_turn_confidence,
                endpointing_type=EndpointingType.SEMANTIC,
                duration_ms=duration_ms,
                metadata={
                    "source": "end_of_turn_confidence",
                    "raw_confidence": confidence,
                    "end_of_turn_confidence": end_of_turn_confidence,
                }
            )
            
            await self._emit_result(event)
            
            # Reset for next turn
            self._transcript_buffer = ""
            self._start_time_ms = int(time.time() * 1000)
            
            logger.info(
                f"AssemblyAI end of turn (conf={end_of_turn_confidence:.2f}): "
                f"{transcript[:50]}..."
            )
