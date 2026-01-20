"""
Streaming STT Manager for Live Interview Agent.

Manages streaming STT sessions and coordinates with the main audio pipeline.
Provides a facade that can be used alongside or instead of batch STT.
"""
import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Any, TYPE_CHECKING

from src.providers.stt.streaming_base import (
    StreamingSTTProvider,
    StreamingSession,
    StreamingConfig,
    InterimResult,
    EndOfTurnEvent,
    EndpointingType,
)
from src.protocol import Speaker

if TYPE_CHECKING:
    from src.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


@dataclass
class StreamingSTTCallbacks:
    """Callbacks for streaming STT events."""
    on_interim: Optional[Callable[[str, Speaker], Any]] = None
    on_final: Optional[Callable[[str, Speaker, float], Any]] = None
    on_end_of_turn: Optional[Callable[[str, Speaker, float, EndpointingType], Any]] = None
    on_error: Optional[Callable[[Exception], Any]] = None


class StreamingSTTManager:
    """
    Manages streaming STT sessions for the sidecar server.
    
    This manager:
    1. Creates and manages streaming STT sessions
    2. Routes audio chunks to the streaming provider
    3. Emits interim results and end-of-turn events
    4. Falls back to batch STT if streaming is unavailable
    
    Usage:
        manager = StreamingSTTManager(factory)
        
        # Start streaming session
        await manager.start_session(callbacks)
        
        # Send audio chunks
        await manager.send_audio(audio_data, speaker)
        
        # Stop session
        await manager.stop_session()
    """
    
    # Reconnection settings with exponential backoff
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_BASE_DELAY_S = 1.0
    RECONNECT_MAX_DELAY_S = 30.0
    WATCHDOG_INTERVAL_S = 5.0
    
    def __init__(self, factory: Optional["ProviderFactory"] = None):
        self.factory = factory
        self._session: Optional[StreamingSession] = None
        self._provider: Optional[StreamingSTTProvider] = None
        self._callbacks = StreamingSTTCallbacks()
        self._receive_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._current_speaker: Speaker = Speaker.INTERVIEWER
        self._is_active = False
        self._reconnect_attempts = 0
        self._stored_config: Optional[StreamingConfig] = None
    
    @property
    def is_active(self) -> bool:
        """Check if a streaming session is active."""
        return self._is_active and self._session is not None and self._session.is_connected
    
    @property
    def needs_reconnection(self) -> bool:
        """Check if session needs reconnection (e.g., after keepalive failures)."""
        if not self._session:
            return False
        # Use the standardized needs_reconnection property from base class
        return self._session.needs_reconnection
    
    @property
    def provider_name(self) -> Optional[str]:
        """Get the name of the active streaming provider."""
        return self._provider.provider_name if self._provider else None
    
    @property
    def supports_semantic_endpointing(self) -> bool:
        """Check if current provider supports semantic endpointing."""
        return self._provider.supports_semantic_endpointing if self._provider else False
    
    def set_factory(self, factory: "ProviderFactory") -> None:
        """Set the provider factory."""
        self.factory = factory
    
    async def start_session(
        self,
        callbacks: Optional[StreamingSTTCallbacks] = None,
        config: Optional[StreamingConfig] = None,
    ) -> bool:
        """
        Start a streaming STT session.
        
        Args:
            callbacks: Event callbacks for interim/final results
            config: Optional streaming configuration
            
        Returns:
            True if session started successfully, False otherwise
        """
        if self.is_active:
            logger.warning("Streaming session already active")
            return True
        
        if not self.factory:
            logger.warning("Provider factory not set")
            return False
        
        # Store callbacks
        if callbacks:
            self._callbacks = callbacks
        
        # Get streaming provider from factory
        self._provider = self.factory.get_streaming_stt_provider()
        if not self._provider:
            logger.info("No streaming STT provider available")
            return False
        
        # Create config if not provided
        if config is None:
            config = StreamingConfig(
                enable_endpointing=True,
                emit_interim_results=True,
            )
        
        try:
            # Connect to streaming provider
            self._session = await self._provider.connect(config)
            self._is_active = True
            self._stored_config = config  # Store for reconnection
            self._reconnect_attempts = 0  # Reset on successful connection
            
            # Start receiving results
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # Start watchdog for reconnection detection
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())
            
            logger.info(f"Streaming STT session started: {self._provider.provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming session: {e}")
            self._is_active = False
            self._session = None
            self._provider = None
            
            if self._callbacks.on_error:
                await self._call_callback(self._callbacks.on_error, e)
            
            return False
    
    async def stop_session(self) -> Optional[str]:
        """
        Stop the streaming STT session.
        
        Returns:
            Final transcript if any pending, None otherwise
        """
        if not self._is_active:
            return None
        
        final_transcript = None
        
        try:
            # Cancel watchdog task
            if self._watchdog_task and not self._watchdog_task.done():
                self._watchdog_task.cancel()
                try:
                    await self._watchdog_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel receive task
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
            
            # Finalize session to get any pending audio
            if self._session:
                event = await self._session.finalize()
                if event:
                    final_transcript = event.final_transcript
                    if self._callbacks.on_end_of_turn:
                        await self._call_callback(
                            self._callbacks.on_end_of_turn,
                            event.final_transcript,
                            self._current_speaker,
                            event.confidence,
                            event.endpointing_type,
                        )
                
                # Close session
                await self._session.close()
            
        except Exception as e:
            logger.error(f"Error stopping streaming session: {e}")
        
        finally:
            self._is_active = False
            self._session = None
            self._receive_task = None
            self._watchdog_task = None
            logger.info("Streaming STT session stopped")
        
        return final_transcript
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect a failed streaming session with exponential backoff.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self._reconnect_attempts >= self.MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Max reconnection attempts ({self.MAX_RECONNECT_ATTEMPTS}) reached")
            return False
        
        self._reconnect_attempts += 1
        
        # Calculate delay with exponential backoff + jitter
        delay = min(
            self.RECONNECT_BASE_DELAY_S * (2 ** (self._reconnect_attempts - 1)),
            self.RECONNECT_MAX_DELAY_S
        )
        jitter = random.uniform(0, delay * 0.1)
        total_delay = delay + jitter
        
        logger.info(
            f"Attempting streaming STT reconnection ({self._reconnect_attempts}/{self.MAX_RECONNECT_ATTEMPTS}) "
            f"in {total_delay:.1f}s"
        )
        
        # Clean up old session without triggering callbacks
        try:
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
            
            if self._session:
                # Clear the reconnection flag before closing
                if hasattr(self._session, 'clear_reconnection_flag'):
                    self._session.clear_reconnection_flag()
                await self._session.close()
        except Exception as e:
            logger.debug(f"Cleanup during reconnect: {e}")
        
        self._session = None
        self._receive_task = None
        self._is_active = False
        
        # Wait before reconnecting (exponential backoff)
        await asyncio.sleep(total_delay)
        
        # Reconnect using stored config (don't overwrite callbacks)
        if not self._provider or not self._stored_config:
            logger.error("Cannot reconnect: missing provider or config")
            return False
        
        try:
            self._session = await self._provider.connect(self._stored_config)
            self._is_active = True
            
            # Restart receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info(f"Streaming STT reconnected successfully (attempt {self._reconnect_attempts})")
            self._reconnect_attempts = 0  # Reset on success
            return True
            
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False
    
    async def _watchdog_loop(self) -> None:
        """
        Background task to monitor session health and trigger reconnection.
        
        Checks for:
        1. Session disconnection without explicit stop
        2. Session marked for reconnection (e.g., keepalive failures)
        """
        try:
            while self._is_active:
                await asyncio.sleep(self.WATCHDOG_INTERVAL_S)
                
                if not self._is_active:
                    break
                
                # Check if session needs reconnection
                if self.needs_reconnection:
                    logger.warning("Watchdog detected session needs reconnection")
                    success = await self.reconnect()
                    if not success:
                        logger.error("Watchdog reconnection failed, stopping watchdog")
                        break
                
                # Check if session unexpectedly disconnected
                elif self._session and not self._session.is_connected:
                    logger.warning("Watchdog detected unexpected disconnection")
                    success = await self.reconnect()
                    if not success:
                        logger.error("Watchdog reconnection failed, stopping watchdog")
                        break
                        
        except asyncio.CancelledError:
            logger.debug("Streaming watchdog cancelled")
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
    
    async def send_audio(
        self, 
        audio_data: bytes, 
        speaker: Optional[Speaker] = None
    ) -> bool:
        """
        Send audio chunk to the streaming provider.
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit, mono, 16kHz)
            speaker: Optional speaker identifier
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_active or not self._session:
            return False
        
        if speaker:
            self._current_speaker = speaker
        
        try:
            await self._session.send_audio(audio_data)
            return True
        except Exception as e:
            logger.error(f"Error sending audio to streaming STT: {e}")
            if self._callbacks.on_error:
                await self._call_callback(self._callbacks.on_error, e)
            return False
    
    async def force_end_of_turn(self) -> Optional[EndOfTurnEvent]:
        """
        Force end of current turn and get final result.
        
        Useful when external VAD detects end of speech
        before streaming provider does.
        
        Returns:
            EndOfTurnEvent with final transcript if available
        """
        if not self.is_active or not self._session:
            return None
        
        try:
            event = await self._session.finalize()
            if event and self._callbacks.on_end_of_turn:
                await self._call_callback(
                    self._callbacks.on_end_of_turn,
                    event.final_transcript,
                    self._current_speaker,
                    event.confidence,
                    event.endpointing_type,
                )
            return event
        except Exception as e:
            logger.error(f"Error forcing end of turn: {e}")
            return None
    
    async def _receive_loop(self) -> None:
        """Background task to receive and process streaming results."""
        if not self._session:
            return
        
        try:
            async for result in self._session.results():
                if isinstance(result, EndOfTurnEvent):
                    await self._handle_end_of_turn(result)
                elif isinstance(result, InterimResult):
                    await self._handle_interim_result(result)
                    
        except asyncio.CancelledError:
            logger.debug("Streaming receive loop cancelled")
        except Exception as e:
            logger.error(f"Error in streaming receive loop: {e}")
            if self._callbacks.on_error:
                await self._call_callback(self._callbacks.on_error, e)
    
    async def _handle_interim_result(self, result: InterimResult) -> None:
        """Handle interim/final transcription result."""
        if result.is_final:
            if self._callbacks.on_final:
                await self._call_callback(
                    self._callbacks.on_final,
                    result.text,
                    self._current_speaker,
                    result.confidence,
                )
        else:
            if self._callbacks.on_interim:
                await self._call_callback(
                    self._callbacks.on_interim,
                    result.text,
                    self._current_speaker,
                )
    
    async def _handle_end_of_turn(self, event: EndOfTurnEvent) -> None:
        """Handle end of turn event from provider."""
        if self._callbacks.on_end_of_turn:
            await self._call_callback(
                self._callbacks.on_end_of_turn,
                event.final_transcript,
                self._current_speaker,
                event.confidence,
                event.endpointing_type,
            )
    
    async def _call_callback(self, callback: Callable, *args) -> None:
        """Call a callback, handling both sync and async."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    def get_status(self) -> dict:
        """Get current status of streaming STT."""
        return {
            "active": self.is_active,
            "provider": self.provider_name,
            "semantic_endpointing": self.supports_semantic_endpointing,
        }
