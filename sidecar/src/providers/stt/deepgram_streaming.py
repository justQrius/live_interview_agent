"""
Deepgram Streaming STT Provider.

Uses Deepgram's WebSocket-based live transcription API with
Nova-2 model for real-time streaming transcription.

Features:
- Real-time interim results (~150ms latency)
- utterance_end_ms for acoustic-based endpointing
- Smart formatting for numbers, dates, etc.
"""
import asyncio
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


class DeepgramStreamingProvider(StreamingSTTProvider):
    """
    Deepgram streaming STT provider using WebSocket API.
    
    Uses Nova-3 model (Gen 1 Flagship) with utterance_end_ms for detecting
    when speaker has finished an utterance based on acoustic analysis.
    
    Pricing: ~$0.0077/min (Nova-3 streaming)
    Latency: P50 ~150ms for interim results
    """
    
    # Deepgram WebSocket endpoint
    WS_URL = "wss://api.deepgram.com/v1/listen"
    
    # Default model
    DEFAULT_MODEL = "nova-3"
    
    def __init__(self, api_key: str, model: str = "nova-3"):
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets is required for Deepgram streaming. "
                "Install with: pip install websockets"
            )
    
    @property
    def provider_name(self) -> str:
        return "deepgram"
    
    @property
    def supports_semantic_endpointing(self) -> bool:
        """Deepgram uses acoustic endpointing, not semantic."""
        return False
    
    async def connect(self, config: StreamingConfig) -> "DeepgramStreamingSession":
        """Establish WebSocket connection to Deepgram."""
        session = DeepgramStreamingSession(self, config)
        await session._connect()
        return session


class DeepgramStreamingSession(StreamingSession):
    """
    Active streaming session with Deepgram.
    
    Manages WebSocket connection, audio streaming, and result parsing.
    """
    
    def __init__(self, provider: DeepgramStreamingProvider, config: StreamingConfig):
        super().__init__(provider, config)
        self._ws: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._transcript_buffer: str = ""
        self._start_time_ms: int = 0
        self._last_audio_time_ms: int = 0
    
    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        # Build query parameters
        params = {
            "model": self.provider.model,  # Use configured model
            "language": self.config.language,
            "punctuate": "true",
            "smart_format": "true",
            "encoding": self.config.encoding,
            "sample_rate": str(self.config.sample_rate),
            "channels": str(self.config.channels),
        }
        
        # Enable interim results
        if self.config.emit_interim_results:
            params["interim_results"] = "true"
        
        # Enable endpointing with configurable timeout
        if self.config.enable_endpointing:
            # utterance_end_ms triggers after this much silence
            timeout_ms = self.config.extra_options.get(
                "utterance_end_ms", 
                self.config.endpointing_timeout_ms
            )
            params["utterance_end_ms"] = str(timeout_ms)
        
        # Additional options from config
        if self.config.extra_options.get("diarize"):
            params["diarize"] = "true"
        
        # Build URL with query string
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{DeepgramStreamingProvider.WS_URL}?{query}"
        
        # Connect with auth header
        headers = {
            "Authorization": f"Token {self.provider.api_key}"
        }
        
        try:
            self._ws = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
            )
            self._is_connected = True
            self._start_time_ms = int(time.time() * 1000)
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info(f"Deepgram streaming connected: {params}")
            
        except Exception as e:
            self._is_connected = False
            self.provider._is_available = False
            raise ConnectionError(f"Failed to connect to Deepgram: {e}")
    
    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk to Deepgram."""
        if not self.is_connected or self._ws is None:
            raise RuntimeError("Not connected to Deepgram")
        
        try:
            await self._ws.send(audio_data)
            self._last_audio_time_ms = int(time.time() * 1000)
        except Exception as e:
            logger.error(f"Error sending audio to Deepgram: {e}")
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
                # Send close frame to finalize
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing Deepgram connection: {e}")
            self._ws = None
        
        logger.info("Deepgram streaming session closed")
    
    async def finalize(self) -> Optional[EndOfTurnEvent]:
        """
        Signal end of audio and get final result.
        
        Sends FinishStream message to Deepgram to flush any pending audio.
        """
        if not self.is_connected or self._ws is None:
            return None
        
        try:
            # Send finalize message
            await self._ws.send(json.dumps({"type": "FinishStream"}))
            
            # Wait briefly for final results
            await asyncio.sleep(0.5)
            
            # Return pending transcript if any
            if self._transcript_buffer.strip():
                duration_ms = int(time.time() * 1000) - self._start_time_ms
                return EndOfTurnEvent(
                    final_transcript=self._transcript_buffer.strip(),
                    confidence=0.85,  # Deepgram doesn't give word-level confidence in streaming
                    endpointing_type=EndpointingType.ACOUSTIC,
                    duration_ms=duration_ms,
                    metadata={"source": "finalize"}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finalizing Deepgram stream: {e}")
            return None
    
    async def _receive_loop(self) -> None:
        """Background task to receive and parse Deepgram messages."""
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
                    logger.warning(f"Invalid JSON from Deepgram: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error handling Deepgram message: {e}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Deepgram connection closed: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"Deepgram receive error: {e}")
        finally:
            self._is_connected = False
    
    async def _handle_message(self, data: dict) -> None:
        """Parse and handle a Deepgram message."""
        msg_type = data.get("type")
        
        if msg_type == "Results":
            await self._handle_results(data)
        elif msg_type == "UtteranceEnd":
            await self._handle_utterance_end(data)
        elif msg_type == "SpeechStarted":
            logger.debug("Deepgram: Speech started")
        elif msg_type == "Metadata":
            logger.debug(f"Deepgram metadata: {data}")
        elif msg_type == "Error":
            error = data.get("error", {})
            logger.error(f"Deepgram error: {error.get('message', data)}")
        else:
            logger.debug(f"Deepgram message: {msg_type}")
    
    async def _handle_results(self, data: dict) -> None:
        """Handle transcription results."""
        channel = data.get("channel", {})
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            return
        
        alt = alternatives[0]
        transcript = alt.get("transcript", "")
        confidence = alt.get("confidence", 0.0)
        is_final = data.get("is_final", False)
        speech_final = data.get("speech_final", False)
        
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
    
    async def _handle_utterance_end(self, data: dict) -> None:
        """
        Handle UtteranceEnd event from Deepgram.
        
        This is triggered when Deepgram detects the speaker has
        finished based on the utterance_end_ms silence threshold.
        """
        duration_ms = int(time.time() * 1000) - self._start_time_ms
        
        # Get last word timing if available
        last_word_end = data.get("last_word_end", 0)
        
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
