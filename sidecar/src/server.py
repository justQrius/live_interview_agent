"""
WebSocket server for Live Interview Agent sidecar.

Handles bidirectional communication with the Tauri UI application.
Coordinates audio capture, STT, RAG, and LLM processing.
"""

import asyncio
import json
import logging
import base64
from dataclasses import dataclass, field
from typing import Any, Optional, Set
import numpy as np

import websockets
from websockets.asyncio.server import serve, ServerConnection

from protocol import (
    Message,
    MessageType,
    SessionStatus,
    ConfidenceLevel,
    Speaker,
    create_transcription_message,
    create_answer_chunk_message,
    create_error_message,
    create_status_message,
)
from audio.diarization import SpeakerRecognizer
from audio.capture import AudioCapture, AudioCaptureError
from audio.vad import VADProcessor, SpeechSegment
from stt.gemini_stt import GeminiSTT, GeminiSTTError
from context.manager import ContextManager
from rag.store import VectorStore
from rag.engine import RAGEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Tracks the current session state."""

    status: SessionStatus = SessionStatus.IDLE
    api_key: Optional[str] = None
    voice_calibrated: bool = False
    user_embedding: Optional[np.ndarray] = field(default=None, repr=False)


class SidecarServer:
    """
    WebSocket server for the Live Interview Agent sidecar.

    Handles client connections and routes messages to appropriate handlers.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        """
        Initialize the sidecar server.

        Args:
            host: Host to bind to (default: localhost only for security)
            port: Port to listen on (default: 8765)
        """
        self.host = host
        self.port = port
        self.clients: Set[ServerConnection] = set()
        self.session_state = SessionState()
        self._server: Optional[Any] = None
        self._running = False
        
        # Audio processing components
        self.stt: Optional[GeminiSTT] = None
        self.vad: Optional[VADProcessor] = None
        self.audio_capture: Optional[AudioCapture] = None
        self._audio_task: Optional[asyncio.Task] = None
        
        # Context management
        self.context_manager = ContextManager()
        self.vector_store: Optional[VectorStore] = None
        self.rag_engine: Optional[RAGEngine] = None
        
        # Initialize components
        try:
            self.speaker_recognizer = SpeakerRecognizer()
        except Exception as e:
            logger.error(f"Failed to initialize SpeakerRecognizer: {e}")
            # We don't crash here, but calibration will fail if called
            self.speaker_recognizer = None

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        self._server = await serve(
            self._handle_client,
            self.host,
            self.port
        )
        logger.info(f"Sidecar server started on ws://{self.host}:{self.port}")

        # Keep running until stopped
        while self._running:
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False

        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
            self.clients.clear()
            
        # Stop audio processing
        await self._stop_audio_processing()

        # Close server
        if self._server:
            self._server.close()
            self._server = None

        # Reset session state
        self.session_state = SessionState()
        self.context_manager.clear_context()

        logger.info("Sidecar server stopped")

    async def _handle_client(self, websocket: ServerConnection) -> None:
        """
        Handle a client connection.

        Args:
            websocket: The WebSocket connection
        """
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")

        try:
            async for raw_message in websocket:
                await self._process_message(websocket, raw_message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            self.clients.discard(websocket)

    async def _process_message(
        self,
        websocket: ServerConnection,
        raw_message: str
    ) -> None:
        """
        Process an incoming message.

        Args:
            websocket: The WebSocket connection
            raw_message: The raw message string
        """
        try:
            message = Message.from_json(raw_message)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON received: {e}")
            error_msg = create_error_message(
                f"Invalid JSON: {e}",
                code="ERR_INVALID_JSON"
            )
            await websocket.send(error_msg.to_json())
            return
        except ValueError as e:
            logger.warning(f"Unknown message type: {e}")
            error_msg = create_error_message(
                f"Unknown message type: {e}",
                code="ERR_UNKNOWN_TYPE"
            )
            await websocket.send(error_msg.to_json())
            return

        # Route message to appropriate handler
        handlers = {
            MessageType.START_SESSION: self._handle_start_session,
            MessageType.STOP_SESSION: self._handle_stop_session,
            MessageType.UPLOAD_CONTEXT: self._handle_upload_context,
            MessageType.CALIBRATE_VOICE: self._handle_calibrate_voice,
            MessageType.MANUAL_QUESTION: self._handle_manual_question,
        }

        handler = handlers.get(message.type)
        if handler:
            await handler(websocket, message)
        else:
            error_msg = create_error_message(
                f"Unsupported message type: {message.type}",
                code="ERR_UNSUPPORTED"
            )
            await websocket.send(error_msg.to_json())

    async def _handle_start_session(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle START_SESSION message."""
        data = message.data or {}
        api_key = data.get("apiKey")

        if not api_key:
            error_msg = create_error_message(
                "API key is required",
                code="ERR_NO_API_KEY"
            )
            await websocket.send(error_msg.to_json())
            return

        # SECURITY: API key stored in memory only, never log session_state
        self.session_state.api_key = api_key
        self.session_state.status = SessionStatus.LISTENING
        
        # Initialize Vector Store
        try:
            self.vector_store = VectorStore(api_key=api_key)
            self.rag_engine = RAGEngine(self.vector_store)
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            # Continue without RAG support, or fail? 
            # We'll log it but let the session start, RAG features will just be unavailable.
        
        # Initialize and start audio processing
        try:
            await self._start_audio_processing(api_key)
        except Exception as e:
            logger.error(f"Failed to start audio processing: {e}")
            error_msg = create_error_message(
                f"Failed to start audio processing: {e}",
                code="ERR_AUDIO_START"
            )
            await websocket.send(error_msg.to_json())
            self.session_state.status = SessionStatus.IDLE
            return

        logger.info("Session started")

        status_msg = create_status_message(self.session_state.status)
        await websocket.send(status_msg.to_json())

    async def _handle_stop_session(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle STOP_SESSION message."""
        self.session_state.status = SessionStatus.IDLE
        self.session_state.api_key = None
        
        # Clear vector store
        if self.vector_store:
            try:
                self.vector_store.clear()
            except Exception as e:
                logger.error(f"Error clearing vector store: {e}")
            self.vector_store = None
        
        self.rag_engine = None
        
        await self._stop_audio_processing()

        logger.info("Session stopped")

        status_msg = create_status_message(SessionStatus.IDLE)
        await websocket.send(status_msg.to_json())

    async def _handle_upload_context(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle UPLOAD_CONTEXT message."""
        data = message.data or {}
        files = data.get("files", [])

        if not files:
            logger.warning("No files provided in context upload")
            error_msg = create_error_message(
                "No files provided",
                code="ERR_NO_FILES"
            )
            await websocket.send(error_msg.to_json())
            return

        logger.info(f"Context upload requested: {len(files)} files")
        
        self.session_state.status = SessionStatus.PROCESSING
        await websocket.send(create_status_message(SessionStatus.PROCESSING).to_json())

        processed_count = 0
        total_chunks = 0
        errors = []

        try:
            for file_data in files:
                filename = file_data.get("name")
                content = file_data.get("content")
                
                if not filename or not content:
                    logger.warning(f"Invalid file data: {filename}")
                    errors.append(f"Invalid data for {filename or 'unknown file'}")
                    continue
                    
                try:
                    new_chunks = await self.context_manager.process_file(filename, content)
                    
                    # Add to vector store if available
                    if new_chunks and self.vector_store:
                        chunk_texts = [c.text for c in new_chunks]
                        chunk_metas = [c.metadata for c in new_chunks]
                        try:
                            self.vector_store.add_documents(chunk_texts, metadatas=chunk_metas)
                        except Exception as e:
                            logger.error(f"Failed to add chunks to vector store: {e}")
                            # We count them as processed even if RAG index failed, 
                            # because they are in memory context
                    
                    total_chunks += len(new_chunks)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process {filename}: {e}")
                    errors.append(f"Failed to process {filename}: {str(e)}")

            if processed_count == 0 and errors:
                 error_msg = create_error_message(
                    f"Failed to process files: {'; '.join(errors)}",
                    code="ERR_CONTEXT_PROCESSING"
                )
                 await websocket.send(error_msg.to_json())
            else:
                logger.info(f"Context processed: {processed_count}/{len(files)} files, {total_chunks} chunks")
                if errors:
                    logger.warning(f"Some files failed: {errors}")
        
        except Exception as e:
            logger.error(f"Context upload fatal error: {e}")
            error_msg = create_error_message(
                f"Context upload failed: {e}",
                code="ERR_CONTEXT_FATAL"
            )
            await websocket.send(error_msg.to_json())

        finally:
            if self.session_state.api_key and self._audio_task:
                 self.session_state.status = SessionStatus.LISTENING
            else:
                 self.session_state.status = SessionStatus.IDLE
                 
            await websocket.send(create_status_message(self.session_state.status).to_json())

    async def _handle_calibrate_voice(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle CALIBRATE_VOICE message."""
        if not self.speaker_recognizer:
            error_msg = create_error_message(
                "Speaker recognizer not initialized",
                code="ERR_COMPONENT_NOT_READY"
            )
            await websocket.send(error_msg.to_json())
            return

        self.session_state.status = SessionStatus.CALIBRATING
        
        # Notify client we are starting
        status_msg = create_status_message(SessionStatus.CALIBRATING)
        await websocket.send(status_msg.to_json())

        try:
            data = message.data or {}
            audio_b64 = data.get("audioData")
            
            if not audio_b64:
                raise ValueError("No audioData provided")
                
            # Decode base64
            audio_bytes = base64.b64decode(audio_b64)
            
            # Convert to numpy array (int16)
            # Assuming incoming data is raw 16kHz mono int16 PCM
            audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Run embedding creation in thread pool to avoid blocking event loop
            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(
                None, 
                self.speaker_recognizer.create_embedding, 
                audio_chunk
            )
            
            self.session_state.user_embedding = embedding
            self.session_state.voice_calibrated = True
            
            logger.info("Voice calibration completed successfully")
            
            self.session_state.status = SessionStatus.IDLE
            status_msg = create_status_message(SessionStatus.IDLE)
            await websocket.send(status_msg.to_json())

        except Exception as e:
            logger.error(f"Voice calibration failed: {e}")
            self.session_state.status = SessionStatus.IDLE
            
            error_msg = create_error_message(
                f"Calibration failed: {str(e)}",
                code="ERR_CALIBRATION_FAILED"
            )
            await websocket.send(error_msg.to_json())
            
            # Send idle status after error
            status_msg = create_status_message(SessionStatus.IDLE)
            await websocket.send(status_msg.to_json())

    async def _handle_manual_question(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle MANUAL_QUESTION message."""
        data = message.data or {}
        question = data.get("question", "")

        if not question:
            error_msg = create_error_message(
                "Question is required",
                code="ERR_NO_QUESTION"
            )
            await websocket.send(error_msg.to_json())
            return

        logger.info(f"Manual question received: {question[:50]}...")

        # Update status to processing
        self.session_state.status = SessionStatus.PROCESSING
        status_msg = create_status_message(SessionStatus.PROCESSING)
        await websocket.send(status_msg.to_json())

        # Retrieve context
        if self.rag_engine:
            try:
                retrieval_results = self.rag_engine.retrieve(question, limit=5)
                logger.info(f"Retrieved {len(retrieval_results)} chunks for question")
                for i, r in enumerate(retrieval_results):
                    logger.debug(f"Chunk {i}: {r.confidence} ({r.distance:.2f}) - {r.text[:50]}...")
            except Exception as e:
                logger.error(f"RAG retrieval failed: {e}")

        # TODO: Implement RAG + LLM pipeline in Stories 011-012
        # For now, send a placeholder response
        answer_msg = create_answer_chunk_message(
            chunk="[Answer generation not yet implemented]",
            complete=True,
            confidence=ConfidenceLevel.LOW
        )
        await websocket.send(answer_msg.to_json())

        # Return to listening state
        self.session_state.status = SessionStatus.LISTENING
        status_msg = create_status_message(SessionStatus.LISTENING)
        await websocket.send(status_msg.to_json())

    async def broadcast(self, message: Message) -> None:
        """
        Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast
        """
        if not self.clients:
            return

        await asyncio.gather(
            *[client.send(message.to_json()) for client in self.clients],
            return_exceptions=True
        )

    async def _start_audio_processing(self, api_key: str) -> None:
        """Initialize and start audio processing components."""
        self.stt = GeminiSTT(api_key=api_key)
        self.vad = VADProcessor()
        self.audio_capture = AudioCapture()
        
        await self.audio_capture.start_capture()
        self._audio_task = asyncio.create_task(self._audio_loop())
        logger.info("Audio processing started")

    async def _stop_audio_processing(self) -> None:
        """Stop audio processing components."""
        if self._audio_task:
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass
            self._audio_task = None
            
        if self.audio_capture:
            await self.audio_capture.stop_capture()
            self.audio_capture = None
            
        self.stt = None
        self.vad = None
        logger.info("Audio processing stopped")

    async def _audio_loop(self) -> None:
        """Main audio processing loop."""
        if not self.audio_capture or not self.vad or not self.stt:
            logger.error("Audio components not initialized")
            return

        logger.info("Starting audio processing loop")
        
        try:
            async for chunk in self.audio_capture.get_audio_stream():
                segments = await self.vad.process_chunk(chunk)
                
                for segment in segments:
                    speaker = Speaker.INTERVIEWER
                    if self.session_state.voice_calibrated and self.session_state.user_embedding is not None:
                         if self.speaker_recognizer:
                             is_user = self.speaker_recognizer.verify_speaker(
                                 np.frombuffer(segment.audio, dtype=np.int16),
                                 self.session_state.user_embedding
                             )
                             if is_user:
                                 speaker = Speaker.USER
                    
                    try:
                        text = await self.stt.transcribe(segment.audio)
                        if text:
                            msg = create_transcription_message(
                                speaker=speaker,
                                text=text,
                                timestamp=segment.start_time,
                                confidence=segment.confidence
                            )
                            await self.broadcast(msg)
                            logger.info(f"Transcribed ({speaker}): {text[:50]}...")
                            
                    except Exception as e:
                        logger.error(f"Error processing speech segment: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Audio loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in audio loop: {e}")
            error_msg = create_error_message(
                f"Audio processing error: {e}",
                code="ERR_AUDIO_LOOP"
            )
            await self.broadcast(error_msg)
            self.session_state.status = SessionStatus.IDLE
            await self.broadcast(create_status_message(SessionStatus.IDLE))


async def main() -> None:
    """Main entry point for the sidecar server."""
    server = SidecarServer()

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
