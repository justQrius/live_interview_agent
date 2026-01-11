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
from typing import Any, Dict, List, Optional, Set, cast
import numpy as np

import websockets
from websockets.asyncio.server import serve, ServerConnection

from .protocol import (
    Message,
    MessageType,
    SessionStatus,
    ConfidenceLevel,
    Speaker,
    create_transcription_message,
    create_answer_chunk_message,
    create_error_message,
    create_status_message,
    create_session_list_message,
    create_session_data_message,
    create_session_export_message,
    create_session_deleted_message,
    create_preparation_ready_message,
    create_extraction_progress_message,
    create_extraction_complete_message,
    create_interim_transcription_message,
    create_story_suggestion_message,
    create_structure_suggestion_message,
    create_consistency_warning_message,
)
from .audio.diarization import SpeakerRecognizer
from .audio.capture import AudioCapture, AudioCaptureError
from .audio.vad import VADProcessor, SpeechSegment
from .audio.noise_reduction import NoiseReducer
from .providers.base import STTProvider, LLMProvider
from .providers.factory import ProviderFactory
from .providers.config import ProviderConfig
from .context.manager import ContextManager
from .rag.store import VectorStore
from .rag.engine import RAGEngine
from .rag.speculative import SpeculativeRetriever
from .warmup import ModelWarmer
from .classification.question_detector import QuestionDetector
from .classification.query_reformulator import QueryReformulator
from .classification.question_splitter import QuestionSplitter
from .storage.session_store import SessionHistoryStore
from .storage.exporter import SessionExporter, ExportFormat
from .memory.store import MemoryStore
from .memory.models import DocumentType
from .extraction.pipeline import ExtractionPipeline
from .coaching.story_recaller import StoryRecaller
from .coaching.structure_suggester import StructureSuggester
from .coaching.consistency_tracker import ConsistencyTracker
from rag.speculative import SpeculativeRetriever

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
    # Conversation history for LLM context (list of {"role": "user"|"assistant", "content": str})
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    # Phase 3: Persistent session ID for history storage
    persistent_session_id: Optional[str] = None
    # Phase 3B: Pre-interview preparation summary
    preparation_summary: Optional[str] = None


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
        
        self.provider_factory: Optional[ProviderFactory] = None
        self.stt: Optional[STTProvider] = None
        self.vad: Optional[VADProcessor] = None
        self.noise_reducer: Optional[NoiseReducer] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.vad: Optional[VADProcessor] = None
        self.stt: Optional[STTProvider] = None
        self.llm: Optional[LLMProvider] = None
        self.vector_store: Optional[VectorStore] = None
        self.rag_engine: Optional[RAGEngine] = None
        self.speculative_retriever: Optional[SpeculativeRetriever] = None
        self.story_recaller: Optional[StoryRecaller] = None
        self.structure_suggester: Optional[StructureSuggester] = None
        
        # Initialize storage
        self.session_store = SessionHistoryStore()
        
        # Phase 4E: Initialize Consistency Tracker (needs session store)
        self.consistency_tracker = ConsistencyTracker(self.session_store)
        
        self.model_warmer = ModelWarmer.get_instance()
        self.model_warmer.start_warming()
        
        self.speaker_recognizer = None 
        
        # Phase 3: Intelligent Question Detection
        self.question_detector = QuestionDetector()
        self.question_detection_enabled = True  # Feature flag for rollout
        self.question_confidence_threshold = 0.7  # Configurable threshold
        
        # Phase 3C: Conversational Intelligence
        self.query_reformulator = QueryReformulator()
        self.question_splitter = QuestionSplitter()
        
        # Phase 3: Session History Persistence
        self.session_store = SessionHistoryStore()
        self.session_persistence_enabled = True  # Feature flag for rollout 
        
        # Phase 4: Persistent Memory & Extraction Pipeline
        self.memory_store = MemoryStore()
        self.extraction_pipeline = ExtractionPipeline(memory_store=self.memory_store)
        self.extraction_enabled = True  # Feature flag for rollout

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        self._server = await serve(
            self._handle_client,
            self.host,
            self.port
        )
        logger.info(f"Sidecar server started on ws://{self.host}:{self.port}")

        while self._running:
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False

        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
            self.clients.clear()
            
        await self._stop_audio_processing()

        if self._server:
            self._server.close()
            self._server = None

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
                if isinstance(raw_message, bytes):
                    raw_message = raw_message.decode('utf-8')
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

        handlers = {
            MessageType.START_SESSION: self._handle_start_session,
            MessageType.STOP_SESSION: self._handle_stop_session,
            MessageType.UPLOAD_CONTEXT: self._handle_upload_context,
            MessageType.CALIBRATE_VOICE: self._handle_calibrate_voice,
            MessageType.MANUAL_QUESTION: self._handle_manual_question,
            # Session History handlers (Phase 3: STORY-039)
            MessageType.LIST_SESSIONS: self._handle_list_sessions,
            MessageType.LOAD_SESSION: self._handle_load_session,
            MessageType.EXPORT_SESSION: self._handle_export_session,
            MessageType.DELETE_SESSION: self._handle_delete_session,
            # Pre-interview preparation (Phase 3B: STORY-047)
            MessageType.PREPARE_INTERVIEW: self._handle_prepare_interview,
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
        
        if "apiKeys" not in data and "apiKey" in data:
            data = {
                "apiKeys": {"gemini": data["apiKey"]},
                "preferences": {}
            }
            
        try:
            config = ProviderConfig.from_dict(data)
            self.provider_factory = ProviderFactory(config)
            
            self.stt = self.provider_factory.get_stt_provider()
            
            try:
                self.llm = self.provider_factory.get_llm_provider()
                # Phase 4: Load existing profile for context injection
                if self.memory_store:
                    existing_profile = self.memory_store.get_profile()
                    if existing_profile:
                        logger.info(f"Loaded existing candidate profile ({len(existing_profile.profile_text)} chars)")
                        self.llm.set_candidate_profile(existing_profile.get_prompt_injection())
                
                # Phase 4C: Set LLM for Tier 3 Question Detection
                self.question_detector.set_llm_provider(self.llm)
                
            except Exception as e:
                logger.warning(f"No LLM provider available: {e}")
                self.llm = None

        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
            error_msg = create_error_message(
                f"Failed to initialize providers: {e}",
                code="ERR_PROVIDER_INIT"
            )
            await websocket.send(error_msg.to_json())
            return

        self.session_state.api_key = "multi-provider-active" 
        self.session_state.status = SessionStatus.LISTENING
        
        # CRITICAL: Start audio processing FIRST - this is the user's primary need
        # RAG initialization can happen in background and may timeout on network issues
        try:
            await self._start_audio_processing()
        except Exception as e:
            logger.error(f"Failed to start audio processing: {e}")
            error_msg = create_error_message(
                f"Failed to start audio processing: {e}",
                code="ERR_AUDIO_START"
            )
            await websocket.send(error_msg.to_json())
            self.session_state.status = SessionStatus.IDLE
            return

        logger.info("Session started - audio processing active")

        status_msg = create_status_message(self.session_state.status)
        await websocket.send(status_msg.to_json())
        
        # Phase 3: Create persistent session for history storage
        if self.session_persistence_enabled:
            try:
                context_files = [f.get("name", "") for f in data.get("files", [])]
                self.session_state.persistent_session_id = self.session_store.create_session(
                    context_files=context_files
                )
                logger.info(f"Created persistent session: {self.session_state.persistent_session_id}")
                
                # Phase 4E: Start consistency tracking
                if self.consistency_tracker:
                    self.consistency_tracker.start_session(self.session_state.persistent_session_id)
                    
            except Exception as e:
                logger.warning(f"Failed to create persistent session: {e}")
                # Continue without persistence - don't break main flow
        
        # Initialize RAG in background - don't block audio processing
        # Session works even if RAG fails (graceful degradation)
        rag_key = config.gemini_api_key or config.openai_api_key or "dummy"
        asyncio.create_task(self._init_rag_background(rag_key))

    async def _handle_stop_session(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle STOP_SESSION message."""
        # Phase 3: End persistent session before clearing state
        if self.session_persistence_enabled and self.session_state.persistent_session_id:
            try:
                self.session_store.end_session(self.session_state.persistent_session_id)
                logger.info(f"Ended persistent session: {self.session_state.persistent_session_id}")
            except Exception as e:
                logger.warning(f"Failed to end persistent session: {e}")
        
        self.session_state.status = SessionStatus.IDLE
        self.session_state.api_key = None
        # Clear conversation history for fresh start on next session
        self.session_state.conversation_history.clear()
        self.session_state.persistent_session_id = None
        
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
                doc_type_str = file_data.get("documentType", "other")
                
                if not filename or not content:
                    logger.warning(f"Invalid file data: {filename}")
                    errors.append(f"Invalid data for {filename or 'unknown file'}")
                    continue
                
                # Map document type string to enum
                doc_type_map = {
                    "resume": DocumentType.RESUME,
                    "job_description": DocumentType.JOB_DESCRIPTION,
                    "company_info": DocumentType.COMPANY_INFO,
                    "interviewer_info": DocumentType.INTERVIEWER_INFO,
                }
                doc_type = doc_type_map.get(doc_type_str, DocumentType.OTHER)
                    
                try:
                    # Process through context manager for RAG chunks
                    new_chunks = await self.context_manager.process_file(filename, content)
                    
                    if new_chunks and self.vector_store:
                        chunk_texts = [c.text for c in new_chunks]
                        chunk_metas = [c.metadata for c in new_chunks]
                        try:
                            self.vector_store.add_documents(chunk_texts, metadatas=chunk_metas)
                        except Exception as e:
                            logger.error(f"Failed to add chunks to vector store: {e}")
                    
                    total_chunks += len(new_chunks)
                    
                    # Phase 4: Run extraction pipeline in background
                    if self.extraction_enabled and self.extraction_pipeline:
                        import uuid
                        doc_id = str(uuid.uuid4())
                        
                        async def extraction_progress(stage: str, progress: float, msg: str = ""):
                            try:
                                progress_msg = create_extraction_progress_message(
                                    stage=stage,
                                    progress=progress,
                                    message=msg
                                )
                                await websocket.send(progress_msg.to_json())
                            except Exception as e:
                                logger.debug(f"Failed to send progress: {e}")
                        
                        # Set LLM provider for extraction if available
                        if self.llm:
                            self.extraction_pipeline.set_llm_provider(self.llm)
                        
                        # Run extraction (non-blocking for UI responsiveness)
                        asyncio.create_task(self._run_extraction(
                            websocket, doc_id, content, doc_type, filename, extraction_progress
                        ))
                    
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
    
    async def _run_extraction(
        self,
        websocket: ServerConnection,
        doc_id: str,
        content: str,
        doc_type: DocumentType,
        filename: str,
        progress_callback
    ) -> None:
        """Run extraction pipeline in background."""
        try:
            result = await self.extraction_pipeline.process_document(
                document_id=doc_id,
                text=content,
                document_type=doc_type,
                filename=filename,
                progress_callback=progress_callback,
            )
            
            # Phase 4: Inject updated profile into LLM if available
            if result.profile and self.llm:
                logger.info(f"Injecting updated candidate profile ({len(result.profile.profile_text)} chars)")
                self.llm.set_candidate_profile(result.profile.get_prompt_injection())
            
            complete_msg = create_extraction_complete_message(
                document_id=doc_id,
                filename=filename,
                success=result.success,
                summary=result.to_dict()
            )
            await websocket.send(complete_msg.to_json())
            
        except Exception as e:
            logger.error(f"Extraction pipeline failed for {filename}: {e}")
            complete_msg = create_extraction_complete_message(
                document_id=doc_id,
                filename=filename,
                success=False,
                summary={"error": str(e)}
            )
            try:
                await websocket.send(complete_msg.to_json())
            except Exception:
                pass

    async def _handle_calibrate_voice(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle CALIBRATE_VOICE message."""
        if not self.speaker_recognizer:
            # Try to get from warmer
            if self.model_warmer.wait_for_ready(timeout=2.0):
                models = self.model_warmer.get_models()
                if models.speaker_recognizer:
                    self.speaker_recognizer = cast(SpeakerRecognizer, models.speaker_recognizer)
            
            # If still None, try synchronous load
            if not self.speaker_recognizer:
                try:
                    logger.info("Loading SpeakerRecognizer synchronously for calibration")
                    self.speaker_recognizer = SpeakerRecognizer()
                except Exception as e:
                    logger.error(f"Failed to load SpeakerRecognizer: {e}")

        if not self.speaker_recognizer:
            error_msg = create_error_message(
                "Speaker recognizer not initialized",
                code="ERR_COMPONENT_NOT_READY"
            )
            await websocket.send(error_msg.to_json())
            return

        self.session_state.status = SessionStatus.CALIBRATING
        
        status_msg = create_status_message(SessionStatus.CALIBRATING)
        await websocket.send(status_msg.to_json())

        try:
            data = message.data or {}
            audio_b64 = data.get("audioData")
            
            if not audio_b64:
                raise ValueError("No audioData provided")
                
            audio_bytes = base64.b64decode(audio_b64)
            
            audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
            
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

        self.session_state.status = SessionStatus.PROCESSING
        status_msg = create_status_message(SessionStatus.PROCESSING)
        await websocket.send(status_msg.to_json())

        retrieval_results = []
        context_chunks = []
        rag_confidence = ConfidenceLevel.LOW

        if self.rag_engine:
            try:
                retrieval_results = self.rag_engine.retrieve(question, limit=5)
                logger.info(f"Retrieved {len(retrieval_results)} chunks for question")
                context_chunks = [r.text for r in retrieval_results]

                if retrieval_results:
                    rag_confidence = self._confidence_from_string(retrieval_results[0].confidence)

                for i, r in enumerate(retrieval_results):
                    logger.debug(f"Chunk {i}: {r.confidence} ({r.distance:.2f}) - {r.text[:50]}...")
            except Exception as e:
                logger.error(f"RAG retrieval failed: {e}")

        if self.llm:
            try:
                # Signal start of answer
                await self.broadcast(Message(type=MessageType.ANSWER_START))
                
                context_str = "\n\n".join(context_chunks)
                # Collect full answer for history
                full_answer_parts: List[str] = []
                
                async for chunk in self.llm.generate_response(
                    question, context_str, self.session_state.conversation_history
                ):
                    full_answer_parts.append(chunk)
                    answer_msg = create_answer_chunk_message(
                        chunk=chunk,
                        complete=False
                    )
                    await websocket.send(answer_msg.to_json())

                await websocket.send(create_answer_chunk_message(
                    chunk="",
                    complete=True,
                    confidence=rag_confidence
                ).to_json())
                
                # Append Q&A to conversation history for future context
                full_answer = "".join(full_answer_parts)
                self.session_state.conversation_history.append({
                    "role": "user",
                    "content": question
                })
                self.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": full_answer
                })
                logger.debug(f"Added manual Q&A to history. Total exchanges: {len(self.session_state.conversation_history) // 2}")
                
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                error_msg = create_error_message(
                    f"Failed to generate answer: {e}",
                    code="ERR_LLM_GENERATION"
                )
                await websocket.send(error_msg.to_json())
        else:
             error_msg = create_error_message(
                "LLM not initialized",
                code="ERR_LLM_NOT_READY"
            )
             await websocket.send(error_msg.to_json())

        self.session_state.status = SessionStatus.LISTENING
        status_msg = create_status_message(SessionStatus.LISTENING)
        await websocket.send(status_msg.to_json())

    # Session History Handlers (Phase 3: STORY-039)

    async def _handle_list_sessions(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle LIST_SESSIONS message - returns paginated session list."""
        data = message.data or {}
        limit = data.get("limit", 20)
        offset = data.get("offset", 0)
        
        try:
            sessions = self.session_store.list_sessions(limit=limit, offset=offset)
            session_summaries = [self._session_summary_to_dict(s) for s in sessions]
            
            response = create_session_list_message(
                sessions=session_summaries,
                total=len(session_summaries),
                has_more=len(sessions) == limit
            )
            await websocket.send(response.to_json())
            logger.info(f"Listed {len(sessions)} sessions (offset={offset}, limit={limit})")
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            error_msg = create_error_message(
                f"Failed to list sessions: {e}",
                code="ERR_LIST_SESSIONS"
            )
            await websocket.send(error_msg.to_json())

    async def _handle_load_session(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle LOAD_SESSION message - returns full session data."""
        data = message.data or {}
        session_id = data.get("sessionId")
        
        if not session_id:
            error_msg = create_error_message(
                "sessionId is required",
                code="ERR_MISSING_SESSION_ID"
            )
            await websocket.send(error_msg.to_json())
            return
        
        try:
            session = self.session_store.get_session(session_id)
            if not session:
                error_msg = create_error_message(
                    f"Session not found: {session_id}",
                    code="ERR_SESSION_NOT_FOUND"
                )
                await websocket.send(error_msg.to_json())
                return
            
            response = create_session_data_message(self._session_to_full_dict(session))
            await websocket.send(response.to_json())
            logger.info(f"Loaded session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            error_msg = create_error_message(
                f"Failed to load session: {e}",
                code="ERR_LOAD_SESSION"
            )
            await websocket.send(error_msg.to_json())

    async def _handle_export_session(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle EXPORT_SESSION message - returns formatted session content."""
        data = message.data or {}
        session_id = data.get("sessionId")
        export_format = data.get("format", "md")
        
        if not session_id:
            error_msg = create_error_message(
                "sessionId is required",
                code="ERR_MISSING_SESSION_ID"
            )
            await websocket.send(error_msg.to_json())
            return
        
        try:
            session = self.session_store.get_session(session_id)
            if not session:
                error_msg = create_error_message(
                    f"Session not found: {session_id}",
                    code="ERR_SESSION_NOT_FOUND"
                )
                await websocket.send(error_msg.to_json())
                return
            
            if export_format == "json":
                content = self._export_session_as_json(session)
            elif export_format == "txt":
                content = SessionExporter.export(session, ExportFormat.TEXT)
            else:
                content = self._export_session_as_markdown(session)
                export_format = "md"
            
            response = create_session_export_message(content=content, format=export_format)
            await websocket.send(response.to_json())
            logger.info(f"Exported session {session_id} as {export_format}")
        except Exception as e:
            logger.error(f"Failed to export session: {e}")
            error_msg = create_error_message(
                f"Failed to export session: {e}",
                code="ERR_EXPORT_SESSION"
            )
            await websocket.send(error_msg.to_json())

    async def _handle_delete_session(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """Handle DELETE_SESSION message - deletes session and confirms."""
        data = message.data or {}
        session_id = data.get("sessionId")
        
        if not session_id:
            error_msg = create_error_message(
                "sessionId is required",
                code="ERR_MISSING_SESSION_ID"
            )
            await websocket.send(error_msg.to_json())
            return
        
        try:
            success = self.session_store.delete_session(session_id)
            response = create_session_deleted_message(session_id=session_id, success=success)
            await websocket.send(response.to_json())
            
            if success:
                logger.info(f"Deleted session: {session_id}")
            else:
                logger.warning(f"Session not found for deletion: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            error_msg = create_error_message(
                f"Failed to delete session: {e}",
                code="ERR_DELETE_SESSION"
            )
            await websocket.send(error_msg.to_json())

    async def _handle_prepare_interview(
        self,
        websocket: ServerConnection,
        message: Message
    ) -> None:
        """
        Handle PREPARE_INTERVIEW message - generates pre-interview preparation summary.
        
        Phase 3B: STORY-047
        """
        logger.info("Starting interview preparation...")
        
        data = message.data or {}
        if not self.llm and data.get("apiKeys"):
            try:
                config = ProviderConfig.from_dict(data)
                factory = ProviderFactory(config)
                self.llm = factory.get_llm_provider()
                logger.info("Initialized LLM provider for preparation")
            except Exception as e:
                logger.warning(f"Could not initialize LLM from preparation data: {e}")
        
        chunks = self.context_manager.get_all_chunks()
        
        if not chunks:
            summary = """## Interview Preparation

**No documents uploaded.** Upload your resume and job description for personalized preparation.

To get started:
1. Upload your resume/CV
2. Upload the job description
3. Optionally add company information
4. Click "Prepare for Interview" again"""
            
            response = create_preparation_ready_message(summary)
            await websocket.send(response.to_json())
            return
        
        # Build preparation prompt from context
        try:
            preparation_prompt = self._build_preparation_prompt(chunks)
            
            if not self.llm:
                # Fallback if no LLM available
                summary = self._generate_fallback_preparation(chunks)
            else:
                # Generate preparation using LLM
                summary = await self._generate_preparation_with_llm(preparation_prompt)
            
            # Store in session state
            self.session_state.preparation_summary = summary
            
            response = create_preparation_ready_message(summary)
            await websocket.send(response.to_json())
            logger.info("Interview preparation complete")
            
        except Exception as e:
            logger.error(f"Failed to generate preparation: {e}")
            error_msg = create_error_message(
                f"Failed to generate preparation: {e}",
                code="ERR_PREPARATION_FAILED"
            )
            await websocket.send(error_msg.to_json())
    
    def _build_preparation_prompt(self, chunks: list) -> str:
        """Build prompt for preparation generation from context chunks."""
        # Group chunks by source/type
        resume_text = []
        jd_text = []
        company_text = []
        other_text = []
        
        for chunk in chunks:
            meta = chunk.metadata or {}
            source = meta.get("source", "").lower()
            doc_type = meta.get("document_type", "").lower()
            
            if "resume" in source or "cv" in source or doc_type == "resume":
                resume_text.append(chunk.text)
            elif "job" in source or "jd" in source or doc_type == "job_description":
                jd_text.append(chunk.text)
            elif "company" in source or "about" in source or doc_type == "company_info":
                company_text.append(chunk.text)
            else:
                other_text.append(chunk.text)
        
        sections = []
        
        if resume_text:
            sections.append(f"## CANDIDATE BACKGROUND\n{' '.join(resume_text[:5])}")
        
        if jd_text:
            sections.append(f"## ROLE REQUIREMENTS\n{' '.join(jd_text[:5])}")
        
        if company_text:
            sections.append(f"## COMPANY CONTEXT\n{' '.join(company_text[:3])}")
        
        if other_text and not (resume_text or jd_text):
            sections.append(f"## ADDITIONAL CONTEXT\n{' '.join(other_text[:3])}")
        
        return f"""Based on the following documents, prepare a comprehensive interview briefing:

{chr(10).join(sections)}

Generate a structured preparation summary with:
1. **Key Talking Points**: 3-5 points that align the candidate's experience with role requirements
2. **Potential Challenges**: 2-3 areas where the candidate may need to address gaps
3. **Company-Specific Insights**: 2-3 talking points that reference company values/products (if available)
4. **STAR Story Suggestions**: 2-3 specific experiences from the resume that could be used for behavioral questions
5. **Questions to Ask**: 2-3 intelligent questions the candidate could ask

Keep the briefing concise and actionable. Use bullet points and markdown formatting."""
    
    async def _generate_preparation_with_llm(self, prompt: str) -> str:
        """Generate preparation summary using LLM."""
        if not self.llm:
            raise RuntimeError("LLM not available")
        
        full_response_parts: List[str] = []
        
        async for chunk in self.llm.generate_response(
            prompt,
            "",  # No additional context
            []   # No conversation history
        ):
            full_response_parts.append(chunk)
        
        return "".join(full_response_parts)
    
    def _generate_fallback_preparation(self, chunks: list) -> str:
        """Generate basic preparation without LLM."""
        doc_count = len(chunks)
        
        return f"""## Interview Preparation Summary

**Documents Analyzed**: {doc_count} context chunks loaded

### Key Points from Your Documents

Based on the uploaded documents, here are the main topics to prepare:

{chr(10).join([f"- {chunk.text[:100]}..." for chunk in chunks[:5]])}

### General Preparation Tips

1. **Review your experience** aligned with the role requirements
2. **Prepare STAR stories** for behavioral questions
3. **Research the company** culture and recent news
4. **Prepare thoughtful questions** to ask the interviewer

*Note: For personalized insights, ensure an LLM provider is configured.*"""

    # Session History Helper Methods

    def _session_summary_to_dict(self, session) -> dict:
        """Convert a Session object to a summary dict for list responses."""
        from storage.session_store import SessionData
        s: SessionData = session
        return {
            "id": s.id,
            "startedAt": int(s.started_at.timestamp() * 1000) if s.started_at else None,
            "endedAt": int(s.ended_at.timestamp() * 1000) if s.ended_at else None,
            "contextFiles": s.context_files,
            "transcriptionCount": len(s.transcriptions),
            "answerCount": len(s.answers)
        }

    def _session_to_full_dict(self, session) -> dict:
        """Convert a Session object to a full dict with all data."""
        from storage.session_store import SessionData
        s: SessionData = session
        return {
            "id": s.id,
            "startedAt": int(s.started_at.timestamp() * 1000) if s.started_at else None,
            "endedAt": int(s.ended_at.timestamp() * 1000) if s.ended_at else None,
            "contextFiles": s.context_files,
            "transcriptions": s.transcriptions,
            "answers": s.answers
        }

    def _export_session_as_markdown(self, session) -> str:
        """Export a session as formatted markdown using SessionExporter."""
        return SessionExporter.export(session, ExportFormat.MARKDOWN)

    def _export_session_as_json(self, session) -> str:
        """Export a session as JSON string using SessionExporter."""
        return SessionExporter.export(session, ExportFormat.JSON)

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

    async def _start_audio_processing(self) -> None:
        """Initialize and start audio processing components."""
        # STT is already initialized in _handle_start_session via factory
        if not self.stt:
             logger.error("STT provider not initialized")
             raise RuntimeError("STT provider not initialized")
        
        if not self.model_warmer.wait_for_ready(timeout=2.0):
             logger.warning("Models not ready after timeout")
        
        models = self.model_warmer.get_models()
        if models.is_ready and models.vad_processor and models.speaker_recognizer:
             self.vad = cast(VADProcessor, models.vad_processor)
             self.vad.reset()
             self.speaker_recognizer = cast(SpeakerRecognizer, models.speaker_recognizer)
        else:
             logger.info("Initializing models synchronously")
             self.vad = VADProcessor()
             self.speaker_recognizer = SpeakerRecognizer()

        self.noise_reducer = NoiseReducer(enabled=True)
        self.audio_capture = AudioCapture()
        
        await self.audio_capture.start_capture()
        self._audio_task = asyncio.create_task(self._audio_loop())
        logger.info("Audio processing started")

    async def _init_rag_background(self, api_key: str) -> None:
        """
        Initialize RAG components in background.
        
        This runs asynchronously to avoid blocking audio processing.
        Session continues to work even if RAG initialization fails.
        """
        try:
            logger.info("Initializing RAG in background...")
            
            # Run blocking VectorStore initialization in executor
            loop = asyncio.get_event_loop()
            vector_store = await loop.run_in_executor(
                None, 
                lambda: VectorStore(api_key=api_key)
            )
            self.vector_store = vector_store
            self.rag_engine = RAGEngine(vector_store)
            
            # Phase 4D: Initialize Speculative Retriever
            self.speculative_retriever = SpeculativeRetriever(self.rag_engine)
            
            # Phase 4E: Initialize Story Recaller
            if self.memory_store:
                self.story_recaller = StoryRecaller(self.memory_store, self.vector_store)
                # Warm up stories in background
                asyncio.create_task(self.story_recaller.warm_up())
            
            self.structure_suggester = StructureSuggester()
            
            # Add pre-loaded context chunks
            pre_loaded_chunks = self.context_manager.get_all_chunks()
            if pre_loaded_chunks:
                logger.info(f"Adding {len(pre_loaded_chunks)} pre-loaded chunks to vector store (background)")
                chunk_texts = [c.text for c in pre_loaded_chunks]
                chunk_metas = [c.metadata for c in pre_loaded_chunks]
                try:
                    # Run blocking add_documents in executor
                    def add_docs():
                        vector_store.add_documents(chunk_texts, metadatas=chunk_metas)
                    await loop.run_in_executor(None, add_docs)
                    logger.info("RAG initialization complete - context loaded")
                except Exception as e:
                    logger.warning(f"Failed to add pre-loaded chunks (RAG degraded): {e}")
            else:
                logger.info("RAG initialization complete - no pre-loaded chunks")
                    
        except Exception as e:
            logger.warning(f"RAG initialization failed (session continues without RAG): {e}")
            # Don't raise - session continues without RAG support
            self.vector_store = None
            self.rag_engine = None

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
        self.noise_reducer = None
        logger.info("Audio processing stopped")

    async def _audio_loop(self) -> None:
        """
        Main audio processing loop.
        
        Pipeline: Audio → VAD → NoiseReducer → STT → Diarization → RAG → LLM → UI
        
        - User speech: transcribed and displayed (filtered from RAG+LLM)
        - Interviewer speech: transcribed, then triggers RAG retrieval and LLM generation
        """
        import time
        if not self.audio_capture or not self.vad or not self.stt:
            logger.error("Audio components not initialized")
            return

        logger.info("Starting audio processing loop")
        
        last_speculation_time = 0.0
        
        try:
            async for chunk in self.audio_capture.get_audio_stream():
                segments = await self.vad.process_chunk(chunk)
                
                for segment in segments:
                    # Reset speculation state on segment completion
                    if self.speculative_retriever:
                        self.speculative_retriever.reset()
                    await self._process_speech_segment(segment)
                
                # Phase 4D: Speculative Retrieval Trigger
                # Check periodically if we should speculatively retrieve for ongoing speech
                now = time.time()
                if (self.speculative_retriever and 
                    self.vad.is_speaking and 
                    self.vad.current_duration > 2.0 and 
                    now - last_speculation_time > 2.0):
                    
                    # Run in background to avoid blocking audio loop
                    asyncio.create_task(self._run_speculative_cycle())
                    last_speculation_time = now
                        
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

    async def _run_speculative_cycle(self) -> None:
        """
        Run a single cycle of speculative retrieval.
        Captures current audio buffer, transcribes it, and triggers retrieval.
        """
        import time
        if not self.stt or not self.speculative_retriever or not self.vad:
            return
            
        try:
            audio_buffer = self.vad.get_current_audio()
            # Need at least ~1s of audio (16000 samples * 2 bytes = 32000 bytes)
            if not audio_buffer or len(audio_buffer) < 32000:
                return
                
            # Quick transcription of partial buffer
            # Note: This relies on STT provider being able to handle short partials
            result = await self.stt.transcribe(audio_buffer)
            if result.text:
                # Phase 4D: Broadcast interim transcript
                # Calculate approx start time based on current duration
                start_time = time.time() - self.vad.current_duration
                interim_msg = create_interim_transcription_message(
                    text=result.text,
                    timestamp=start_time,
                    speaker=Speaker.INTERVIEWER
                )
                await self.broadcast(interim_msg)
                
                await self.speculative_retriever.on_interim_transcript(result.text)
                
        except Exception as e:
            logger.debug(f"Speculative cycle failed: {e}")

    async def _process_speech_segment(self, segment) -> None:
        """Process a speech segment: NoiseReducer → Speaker ID → STT → Broadcast → (RAG+LLM if Interviewer)."""
        import time
        pipeline_start = time.time()
        
        audio_for_stt = segment.audio
        if self.noise_reducer and self.noise_reducer.enabled:
            clean_audio = self.noise_reducer.reduce_noise(segment.audio)
            if isinstance(clean_audio, bytes):
                audio_for_stt = clean_audio
        
        speaker = self._identify_speaker(segment.audio)
        
        try:
            if not self.stt:
                logger.error("STT component is None during speech processing")
                return

            result = await self.stt.transcribe(audio_for_stt)
            text = result.text
            if not text:
                return
        except Exception as e:
            logger.error(f"STT error: {e}")
            return
        
        transcription_msg = create_transcription_message(
            speaker=speaker,
            text=text,
            timestamp=segment.start_time,
            confidence=segment.confidence
        )
        await self.broadcast(transcription_msg)
        logger.info(f"Transcribed ({speaker.value}): {text[:50]}...")
        
        # Phase 3: Persist transcription to session history
        if self.session_persistence_enabled and self.session_state.persistent_session_id:
            try:
                self.session_store.add_transcription(
                    session_id=self.session_state.persistent_session_id,
                    speaker=speaker.value,
                    text=text,
                    timestamp=segment.start_time,
                    confidence=segment.confidence
                )
            except Exception as e:
                logger.warning(f"Failed to persist transcription: {e}")
        
        if speaker == Speaker.INTERVIEWER:
            # Phase 3: Question detection before answer generation
            if self.question_detection_enabled:
                is_question, confidence, q_type = await self.question_detector.is_actionable_question(
                    text,
                    self.session_state.conversation_history
                )
                logger.info(f"Question detection: {q_type} (confidence={confidence:.2f})")
                
                if is_question and confidence >= self.question_confidence_threshold:
                    # Phase 3C: Enhanced processing pipeline
                    await self._process_question_pipeline(text, q_type, pipeline_start)
                else:
                    logger.info(f"Skipping answer for non-question ({q_type}): {text[:50]}...")
            else:
                # Feature flag disabled - original behavior
                await self._generate_answer_for_question(text, pipeline_start)

    def _identify_speaker(self, audio: bytes) -> Speaker:
        """Identify speaker as User or Interviewer based on voice calibration."""
        if not self.session_state.voice_calibrated or self.session_state.user_embedding is None:
            return Speaker.INTERVIEWER
            
        if not self.speaker_recognizer:
            return Speaker.INTERVIEWER
            
        try:
            is_user = self.speaker_recognizer.verify_speaker(
                np.frombuffer(audio, dtype=np.int16),
                self.session_state.user_embedding
            )
            return Speaker.USER if is_user else Speaker.INTERVIEWER
        except Exception as e:
            logger.warning(f"Speaker verification failed: {e}, defaulting to Interviewer")
            return Speaker.INTERVIEWER

    async def _recall_and_suggest_story(self, question: str, q_type: str) -> None:
        """Find and broadcast relevant story match."""
        if not self.story_recaller:
            return
            
        try:
            match = await self.story_recaller.find_relevant_story(question, q_type)
            if match:
                msg = create_story_suggestion_message(
                    story_id=match.story.id,
                    title=match.story.title,
                    situation=match.story.situation,
                    relevance_score=match.relevance_score,
                    suggested_opening=match.suggested_opening,
                    key_metrics=match.key_metrics,
                    tags=match.story.tags
                )
                await self.broadcast(msg)
        except Exception as e:
            logger.warning(f"Story recall failed: {e}")

    async def _suggest_structure(self, question: str, q_type: str) -> None:
        """Suggest an answer structure framework."""
        if not self.structure_suggester:
            return
            
        try:
            hint = self.structure_suggester.suggest_structure(question, q_type)
            msg = create_structure_suggestion_message(
                name=hint.name,
                sections=[s.to_dict() for s in hint.sections],
                tips=hint.tips
            )
            await self.broadcast(msg)
        except Exception as e:
            logger.warning(f"Structure suggestion failed: {e}")

    async def _process_question_pipeline(
        self,
        original_question: str,
        question_type: str,
        start_time: float
    ) -> None:
        """
        Phase 3C: Enhanced question processing pipeline.
        
        Pipeline: Query Reformulation → Question Splitting → Enhanced Retrieval → Answer Generation
        
        Args:
            original_question: The raw question text from transcription
            question_type: The detected question type (behavioral, technical, etc.)
            start_time: Pipeline start time for latency tracking
        """
        import time
        
        # Phase 4E: Recall relevant stories (parallel)
        if self.story_recaller and question_type in ("behavioral", "interview_question"):
            asyncio.create_task(self._recall_and_suggest_story(original_question, question_type))
            
        # Phase 4E: Suggest structure (parallel)
        asyncio.create_task(self._suggest_structure(original_question, question_type))
        
        # Step 1: Query Reformulation (expand follow-ups)
        reformulated_question = original_question
        try:
            # Build conversation history in format expected by reformulator
            history_for_reformulator = []
            for i in range(0, len(self.session_state.conversation_history) - 1, 2):
                if i + 1 < len(self.session_state.conversation_history):
                    history_for_reformulator.append({
                        "question": self.session_state.conversation_history[i].get("content", ""),
                        "answer": self.session_state.conversation_history[i + 1].get("content", "")
                    })
            
            reformulated_question, was_reformulated = self.query_reformulator.reformulate_if_needed(
                original_question, history_for_reformulator
            )
            if was_reformulated:
                logger.info(f"Reformulated: '{original_question[:50]}...' → '{reformulated_question[:50]}...'")
        except Exception as e:
            logger.warning(f"Query reformulation failed: {e}")
            reformulated_question = original_question
        
        # Step 2: Question Splitting (handle compound questions)
        sub_questions = [reformulated_question]
        try:
            split_result = self.question_splitter.split_questions(reformulated_question)
            if len(split_result) > 1:
                sub_questions = split_result
                logger.info(f"Split into {len(sub_questions)} sub-questions: {sub_questions}")
        except Exception as e:
            logger.warning(f"Question splitting failed: {e}")
        
        # Step 3: Retrieve context (using question type for enhanced retrieval when available)
        context_chunks, rag_confidence = await self._retrieve_context_enhanced(
            reformulated_question, question_type, sub_questions
        )
        
        # Step 4: Generate answer
        await self._generate_answer_with_context(
            original_question=original_question,
            reformulated_question=reformulated_question,
            context_chunks=context_chunks,
            rag_confidence=rag_confidence,
            start_time=start_time
        )
    
    async def _retrieve_context_enhanced(
        self,
        question: str,
        question_type: str,
        sub_questions: List[str]
    ) -> tuple[list[str], ConfidenceLevel]:
        """
        Enhanced context retrieval using question type, sub-questions, and speculative cache.
        
        Args:
            question: The reformulated question
            question_type: Detected question type for priority filtering
            sub_questions: List of sub-questions for compound queries
            
        Returns:
            Tuple of (context_chunks, confidence)
        """
        # Phase 4D: Use speculative results if available
        if self.speculative_retriever:
            try:
                results = await self.speculative_retriever.on_segment_complete(question)
                if results:
                    chunks = [r.text for r in results]
                    confidence = self._confidence_from_string(results[0].confidence)
                    logger.info(f"Using {len(chunks)} speculative/retrieved chunks")
                    return chunks, confidence
            except Exception as e:
                logger.warning(f"Speculative retrieval failed in pipeline: {e}")
        
        # Fallback to standard retrieval
        return self._retrieve_context(question)
    
    async def _check_consistency(self, text: str) -> None:
        """Extract claims and check for contradictions."""
        if not self.consistency_tracker or not self.session_state.persistent_session_id:
            return
            
        try:
            result = self.consistency_tracker.extract_and_check(text)
            if result.contradictions:
                msg = create_consistency_warning_message([c.to_dict() for c in result.contradictions])
                await self.broadcast(msg)
        except Exception as e:
            logger.warning(f"Consistency check failed: {e}")

    async def _generate_answer_with_context(
        self,
        original_question: str,
        reformulated_question: str,
        context_chunks: List[str],
        rag_confidence: ConfidenceLevel,
        start_time: float
    ) -> None:
        """
        Generate answer with provided context and persist.
        
        Args:
            original_question: Original transcribed question
            reformulated_question: Reformulated question (may be same as original)
            context_chunks: Retrieved context chunks
            rag_confidence: Confidence level from retrieval
            start_time: Pipeline start time for latency tracking
        """
        import time
        
        if not self.llm:
            logger.warning("LLM not initialized, cannot generate answer")
            return
        
        try:
            context_str = "\n\n".join(context_chunks)
            full_answer_parts: List[str] = []
            
            # Use reformulated question for generation but track original
            async for chunk in self.llm.generate_response(
                reformulated_question, context_str, self.session_state.conversation_history
            ):
                full_answer_parts.append(chunk)
                answer_msg = create_answer_chunk_message(chunk=chunk, complete=False)
                await self.broadcast(answer_msg)
            
            latency = time.time() - start_time
            logger.info(f"Answer generation complete. Latency: {latency:.2f}s")
            
            final_msg = create_answer_chunk_message(
                chunk="",
                complete=True,
                confidence=rag_confidence
            )
            await self.broadcast(final_msg)
            
            # Append Q&A to conversation history (use original question for history)
            full_answer = "".join(full_answer_parts)
            
            # Phase 4E: Check consistency
            asyncio.create_task(self._check_consistency(full_answer))
            
            self.session_state.conversation_history.append({
                "role": "user",
                "content": original_question
            })
            self.session_state.conversation_history.append({
                "role": "assistant",
                "content": full_answer
            })
            logger.debug(f"Added Q&A to history. Total exchanges: {len(self.session_state.conversation_history) // 2}")
            
            # Phase 3: Persist answer to session history
            if self.session_persistence_enabled and self.session_state.persistent_session_id:
                try:
                    self.session_store.add_answer(
                        session_id=self.session_state.persistent_session_id,
                        question=original_question,
                        answer=full_answer,
                        confidence=rag_confidence.value,
                        rag_chunks=context_chunks[:3] if context_chunks else None,
                        latency_ms=int(latency * 1000)
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist answer: {e}")
                    
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            error_msg = create_error_message(
                f"Failed to generate answer: {e}",
                code="ERR_LLM_GENERATION"
            )
            await self.broadcast(error_msg)

    async def _generate_answer_for_question(self, question: str, start_time: float) -> None:
        """Generate answer using RAG retrieval + LLM streaming."""
        import time
        
        context_chunks, rag_confidence = self._retrieve_context(question)
        
        if not self.llm:
            logger.warning("LLM not initialized, cannot generate answer")
            return
            
        try:
            context_str = "\n\n".join(context_chunks)
            # Collect full answer for history
            full_answer_parts: List[str] = []
            
            async for chunk in self.llm.generate_response(
                question, context_str, self.session_state.conversation_history
            ):
                full_answer_parts.append(chunk)
                answer_msg = create_answer_chunk_message(chunk=chunk, complete=False)
                await self.broadcast(answer_msg)
            
            latency = time.time() - start_time
            logger.info(f"Answer generation complete. Latency: {latency:.2f}s")
            
            final_msg = create_answer_chunk_message(
                chunk="",
                complete=True,
                confidence=rag_confidence
            )
            await self.broadcast(final_msg)
            
            # Append Q&A to conversation history for future context
            full_answer = "".join(full_answer_parts)
            
            # Phase 4E: Check consistency
            asyncio.create_task(self._check_consistency(full_answer))
            
            self.session_state.conversation_history.append({
                "role": "user",
                "content": question
            })
            self.session_state.conversation_history.append({
                "role": "assistant", 
                "content": full_answer
            })
            logger.debug(f"Added Q&A to history. Total exchanges: {len(self.session_state.conversation_history) // 2}")
            
            # Phase 3: Persist answer to session history
            if self.session_persistence_enabled and self.session_state.persistent_session_id:
                try:
                    self.session_store.add_answer(
                        session_id=self.session_state.persistent_session_id,
                        question=question,
                        answer=full_answer,
                        confidence=rag_confidence.value,
                        rag_chunks=context_chunks[:3] if context_chunks else None,  # Top 3 chunks
                        latency_ms=int(latency * 1000)
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist answer: {e}")
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            error_msg = create_error_message(
                f"Failed to generate answer: {e}",
                code="ERR_LLM_GENERATION"
            )
            await self.broadcast(error_msg)

    def _retrieve_context(self, question: str) -> tuple[list[str], ConfidenceLevel]:
        """Retrieve context chunks from RAG engine for the given question."""
        context_chunks = []
        rag_confidence = ConfidenceLevel.LOW
        
        if not self.rag_engine:
            return context_chunks, rag_confidence
            
        try:
            retrieval_results = self.rag_engine.retrieve(question, limit=5)
            logger.info(f"Retrieved {len(retrieval_results)} chunks for question")
            
            if retrieval_results:
                context_chunks = [r.text for r in retrieval_results]
                rag_confidence = self._confidence_from_string(retrieval_results[0].confidence)
                
                for i, r in enumerate(retrieval_results):
                    logger.debug(f"Chunk {i}: {r.confidence} ({r.distance:.2f}) - {r.text[:50]}...")
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            
        return context_chunks, rag_confidence

    def _confidence_from_string(self, confidence_str: str) -> ConfidenceLevel:
        """Convert string confidence to ConfidenceLevel enum."""
        mapping = {
            "high": ConfidenceLevel.HIGH,
            "medium": ConfidenceLevel.MEDIUM,
            "low": ConfidenceLevel.LOW,
        }
        return mapping.get(confidence_str.lower(), ConfidenceLevel.LOW)


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
