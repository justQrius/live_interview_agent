"""
WebSocket message protocol for Live Interview Agent.

Defines message types and data structures for communication
between Tauri UI and Python sidecar.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional
import json


class MessageType(str, Enum):
    """Message types for WebSocket protocol."""

    # Client -> Server
    START_SESSION = "START_SESSION"
    STOP_SESSION = "STOP_SESSION"
    UPLOAD_CONTEXT = "UPLOAD_CONTEXT"
    CALIBRATE_VOICE = "CALIBRATE_VOICE"
    MANUAL_QUESTION = "MANUAL_QUESTION"
    PREPARE_INTERVIEW = "PREPARE_INTERVIEW"  # Phase 3B: Request preparation summary
    ENHANCE_ANSWER = "ENHANCE_ANSWER"  # Phase 5: Request answer enhancement
    CANCEL_ENHANCEMENT = "CANCEL_ENHANCEMENT"  # Phase 5: Cancel ongoing enhancement
    INFER_DOCUMENT_TYPES = "INFER_DOCUMENT_TYPES"  # Phase 5: Request LLM-based type inference
    
    # Phase 8: RAG Persistence
    LOAD_RAG_STATE = "LOAD_RAG_STATE"  # Phase 8: Check existing RAG state on startup
    REFRESH_CACHE = "REFRESH_CACHE"  # Phase 8: Refresh Gemini cache from existing docs
    CLEAR_ALL_DATA = "CLEAR_ALL_DATA"  # Phase 8: Clear all persistent data
    
    # Listening Control
    PAUSE_LISTENING = "PAUSE_LISTENING"  # Pause audio capture and STT
    RESUME_LISTENING = "RESUME_LISTENING"  # Resume audio capture and STT

    # Server -> Client
    TRANSCRIPTION = "TRANSCRIPTION"
    INTERIM_TRANSCRIPTION = "INTERIM_TRANSCRIPTION"
    STORY_SUGGESTION = "STORY_SUGGESTION"  # Phase 4E: Story suggestion
    STRUCTURE_SUGGESTION = "STRUCTURE_SUGGESTION"  # Phase 4E: Structure suggestion
    CONSISTENCY_WARNING = "CONSISTENCY_WARNING"  # Phase 4E: Consistency check
    ANSWER_START = "ANSWER_START"
    ANSWER_CHUNK = "ANSWER_CHUNK"
    ERROR = "ERROR"
    STATUS = "STATUS"

    # Session History - Client -> Server
    LIST_SESSIONS = "LIST_SESSIONS"
    LOAD_SESSION = "LOAD_SESSION"
    EXPORT_SESSION = "EXPORT_SESSION"
    DELETE_SESSION = "DELETE_SESSION"

    # Session History - Server -> Client
    SESSION_LIST = "SESSION_LIST"
    SESSION_DATA = "SESSION_DATA"
    SESSION_EXPORT = "SESSION_EXPORT"
    SESSION_DELETED = "SESSION_DELETED"
    PREPARATION_READY = "PREPARATION_READY"  # Phase 3B: Preparation summary ready
    
    # Phase 4: Extraction Pipeline
    EXTRACTION_PROGRESS = "EXTRACTION_PROGRESS"  # Phase 4: Document extraction progress
    EXTRACTION_COMPLETE = "EXTRACTION_COMPLETE"  # Phase 4: Document extraction complete
    
    # Phase 5: Answer Enhancement
    ENHANCED_ANSWER_START = "ENHANCED_ANSWER_START"  # Phase 5: Enhanced answer streaming start
    ENHANCED_ANSWER_CHUNK = "ENHANCED_ANSWER_CHUNK"  # Phase 5: Enhanced answer chunk
    ENHANCED_ANSWER_COMPLETE = "ENHANCED_ANSWER_COMPLETE"  # Phase 5: Enhancement done
    DOCUMENT_TYPE_SUGGESTIONS = "DOCUMENT_TYPE_SUGGESTIONS"  # Phase 5: LLM-inferred document types
    
    # Document Management
    DELETE_DOCUMENT = "DELETE_DOCUMENT"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    
    # Phase 6: Utterance Accumulation
    ACCUMULATING = "ACCUMULATING"  # Phase 6: Buffering interviewer speech
    
    # Phase 8: RAG Persistence - Server -> Client
    RAG_STATE = "RAG_STATE"  # Phase 8: Response with existing RAG state
    CACHE_REFRESH_COMPLETE = "CACHE_REFRESH_COMPLETE"  # Phase 8: Cache refresh done
    DATA_CLEARED = "DATA_CLEARED"  # Phase 8: All data cleared confirmation

    # Phase 10: LiveKit Turn Detection - Monitoring & Metrics
    GET_LIVEKIT_METRICS = "GET_LIVEKIT_METRICS"  # Client -> Server: Request LiveKit metrics
    GET_LIVEKIT_HEALTH = "GET_LIVEKIT_HEALTH"  # Client -> Server: Request LiveKit health status
    LIVEKIT_METRICS = "LIVEKIT_METRICS"  # Server -> Client: LiveKit metrics data
    LIVEKIT_HEALTH = "LIVEKIT_HEALTH"  # Server -> Client: LiveKit health check status
    
    # Listening Control - Server -> Client
    LISTENING_PAUSED = "LISTENING_PAUSED"  # Confirm listening paused
    LISTENING_RESUMED = "LISTENING_RESUMED"  # Confirm listening resumed


class SessionStatus(str, Enum):
    """Session status values."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    CALIBRATING = "calibrating"
    LISTENING_PAUSED = "listening_paused"  # Audio/STT paused, manual input only


class ConfidenceLevel(str, Enum):
    """Confidence levels for answers."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Speaker(str, Enum):
    """Speaker labels for diarization."""

    USER = "User"
    INTERVIEWER = "Interviewer"


class EnhancementType(str, Enum):
    """Types of answer enhancement available."""
    
    ADD_DETAIL = "add_detail"  # Re-query RAG with higher limit, add more context
    MAKE_SPECIFIC = "make_specific"  # Add metrics, examples, specifics
    SUGGEST_STAR = "suggest_star"  # Link a relevant STAR story from memory
    ADJUST_TONE = "adjust_tone"  # Rewrite with different tone
    SHORTEN = "shorten"  # Compress to key points


@dataclass
class Message:
    """Base message structure."""

    type: MessageType
    data: Optional[dict[str, Any]] = None

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        payload: dict[str, Any] = {"type": self.type.value}
        if self.data is not None:
            payload["data"] = self.data
        return json.dumps(payload)

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Deserialize message from JSON string."""
        payload = json.loads(json_str)
        msg_type = MessageType(payload["type"])
        data = payload.get("data")
        return cls(type=msg_type, data=data)


@dataclass
class TranscriptionData:
    """Data for TRANSCRIPTION messages."""

    speaker: Speaker
    text: str
    timestamp: float
    confidence: float = 0.0
    is_final: bool = True

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker.value,
            "text": self.text,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "isFinal": self.is_final
        }


@dataclass
class InterimTranscriptionData:
    """Data for INTERIM_TRANSCRIPTION messages."""

    text: str
    timestamp: float
    speaker: Speaker = Speaker.INTERVIEWER

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "timestamp": self.timestamp,
            "speaker": self.speaker.value,
            "isFinal": False
        }


@dataclass
class AnswerChunkData:
    """Data for ANSWER_CHUNK messages."""

    chunk: str
    complete: bool = False
    confidence: Optional[ConfidenceLevel] = None

    def to_dict(self) -> dict:
        result = {
            "chunk": self.chunk,
            "complete": self.complete
        }
        if self.confidence:
            result["confidence"] = self.confidence.value
        return result


@dataclass
class ErrorData:
    """Data for ERROR messages."""

    message: str
    code: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"message": self.message}
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class StatusData:
    """Data for STATUS messages."""

    state: SessionStatus

    def to_dict(self) -> dict:
        return {"state": self.state.value}


# Helper functions for creating common messages

def create_transcription_message(
    speaker: Speaker,
    text: str,
    timestamp: float,
    confidence: float = 0.0
) -> Message:
    """Create a TRANSCRIPTION message."""
    data = TranscriptionData(speaker, text, timestamp, confidence, is_final=True)
    return Message(type=MessageType.TRANSCRIPTION, data=data.to_dict())


def create_interim_transcription_message(
    text: str,
    timestamp: float,
    speaker: Speaker = Speaker.INTERVIEWER
) -> Message:
    """Create an INTERIM_TRANSCRIPTION message."""
    data = InterimTranscriptionData(text, timestamp, speaker)
    return Message(type=MessageType.INTERIM_TRANSCRIPTION, data=data.to_dict())


def create_story_suggestion_message(
    story_id: str,
    title: str,
    situation: str,
    relevance_score: float,
    suggested_opening: str,
    key_metrics: list[str],
    tags: list[str]
) -> Message:
    """Create a STORY_SUGGESTION message."""
    return Message(
        type=MessageType.STORY_SUGGESTION,
        data={
            "storyId": story_id,
            "title": title,
            "situation": situation,
            "relevanceScore": relevance_score,
            "suggestedOpening": suggested_opening,
            "keyMetrics": key_metrics,
            "tags": tags
        }
    )


def create_answer_chunk_message(
    chunk: str,
    complete: bool = False,
    confidence: Optional[ConfidenceLevel] = None
) -> Message:
    """Create an ANSWER_CHUNK message."""
    data = AnswerChunkData(chunk, complete, confidence)
    return Message(type=MessageType.ANSWER_CHUNK, data=data.to_dict())


def create_error_message(message: str, code: Optional[str] = None) -> Message:
    """Create an ERROR message."""
    data = ErrorData(message, code)
    return Message(type=MessageType.ERROR, data=data.to_dict())


def create_status_message(state: SessionStatus) -> Message:
    """Create a STATUS message."""
    data = StatusData(state)
    return Message(type=MessageType.STATUS, data=data.to_dict())


# Session History Helper Functions

def create_document_deleted_message(filename: str, success: bool, error: Optional[str] = None) -> Message:
    """Create a document deleted confirmation message."""
    return Message(
        type=MessageType.DOCUMENT_DELETED,
        data={
            "filename": filename,
            "success": success,
            "error": error
        }
    )


def create_document_deleted_message(filename: str, success: bool, error: Optional[str] = None) -> Message:
    """Create a document deleted confirmation message."""
    return Message(
        type=MessageType.DOCUMENT_DELETED,
        data={
            "filename": filename,
            "success": success,
            "error": error
        }
    )


def create_session_list_message(
    sessions: list[dict],
    total: int,
    has_more: bool
) -> Message:
    """Create a SESSION_LIST response message."""
    return Message(
        type=MessageType.SESSION_LIST,
        data={
            "sessions": sessions,
            "total": total,
            "hasMore": has_more
        }
    )


def create_session_data_message(session_data: dict) -> Message:
    """Create a SESSION_DATA response message."""
    return Message(
        type=MessageType.SESSION_DATA,
        data=session_data
    )


def create_session_export_message(content: str, format: str) -> Message:
    """Create a SESSION_EXPORT response message."""
    return Message(
        type=MessageType.SESSION_EXPORT,
        data={
            "content": content,
            "format": format
        }
    )


def create_session_deleted_message(session_id: str, success: bool) -> Message:
    """Create a SESSION_DELETED response message."""
    return Message(
        type=MessageType.SESSION_DELETED,
        data={
            "sessionId": session_id,
            "success": success
        }
    )


def create_preparation_ready_message(summary: str) -> Message:
    """Create a PREPARATION_READY response message."""
    return Message(
        type=MessageType.PREPARATION_READY,
        data={
            "summary": summary
        }
    )


def create_structure_suggestion_message(
    name: str,
    sections: list[dict],
    tips: list[str]
) -> Message:
    """Create a STRUCTURE_SUGGESTION message."""
    return Message(
        type=MessageType.STRUCTURE_SUGGESTION,
        data={
            "name": name,
            "sections": sections,
            "tips": tips
        }
    )


def create_consistency_warning_message(
    contradictions: list[dict]
) -> Message:
    """Create a CONSISTENCY_WARNING message."""
    return Message(
        type=MessageType.CONSISTENCY_WARNING,
        data={
            "contradictions": contradictions
        }
    )


def create_extraction_progress_message(
    stage: str,
    progress: float,
    document_id: str,
    filename: str,
    message: str = ""
) -> Message:
    return Message(
        type=MessageType.EXTRACTION_PROGRESS,
        data={
            "stage": stage,
            "progress": progress,
            "documentId": document_id,
            "filename": filename,
            "message": message
        }
    )


def create_extraction_complete_message(
    document_id: str,
    filename: str,
    success: bool,
    summary: dict
) -> Message:
    return Message(
        type=MessageType.EXTRACTION_COMPLETE,
        data={
            "documentId": document_id,
            "filename": filename,
            "success": success,
            "summary": summary
        }
    )


# Answer Enhancement Helper Functions

def create_enhanced_answer_start_message(
    enhancement_type: EnhancementType,
    original_question: str
) -> Message:
    """Create an ENHANCED_ANSWER_START message."""
    return Message(
        type=MessageType.ENHANCED_ANSWER_START,
        data={
            "enhancementType": enhancement_type.value,
            "originalQuestion": original_question
        }
    )


def create_enhanced_answer_chunk_message(
    chunk: str,
    complete: bool = False
) -> Message:
    """Create an ENHANCED_ANSWER_CHUNK message."""
    return Message(
        type=MessageType.ENHANCED_ANSWER_CHUNK,
        data={
            "chunk": chunk,
            "complete": complete
        }
    )


def create_enhanced_answer_complete_message(
    enhancement_type: EnhancementType,
    success: bool = True
) -> Message:
    """Create an ENHANCED_ANSWER_COMPLETE message."""
    return Message(
        type=MessageType.ENHANCED_ANSWER_COMPLETE,
        data={
            "enhancementType": enhancement_type.value,
            "success": success
        }
    )


# Document Type Inference Helper Functions

def create_document_type_suggestions_message(
    suggestions: list[dict]
) -> Message:
    """
    Create a DOCUMENT_TYPE_SUGGESTIONS message.
    
    Args:
        suggestions: List of dicts with keys:
            - id: File identifier from request
            - documentType: Inferred type (resume, job_description, etc.)
            - confidence: Float 0.0-1.0
            - reason: Brief explanation
    """
    return Message(
        type=MessageType.DOCUMENT_TYPE_SUGGESTIONS,
        data={
            "suggestions": suggestions
        }
    )


# Utterance Accumulation Helper Functions

def create_accumulating_message(
    speaker: str,
    buffer_preview: str,
    segment_count: int,
    duration_s: float
) -> Message:
    """
    Create an ACCUMULATING message to notify UI that speech is being buffered.
    
    Args:
        speaker: Speaker identifier (e.g., "Interviewer")
        buffer_preview: Preview of accumulated text (truncated)
        segment_count: Number of segments accumulated so far
        duration_s: Time since first segment in seconds
    """
    return Message(
        type=MessageType.ACCUMULATING,
        data={
            "speaker": speaker,
            "bufferPreview": buffer_preview,
            "segmentCount": segment_count,
            "durationSeconds": duration_s
        }
    )


# RAG Persistence Helper Functions (Phase 8)

def create_rag_state_message(
    has_documents: bool,
    document_count: int,
    documents: list[dict],
    cache_expired: bool,
    last_cache_timestamp: str | None = None
) -> Message:
    """
    Create a RAG_STATE response message.
    
    Args:
        has_documents: Whether any documents are in RAG storage
        document_count: Number of documents
        documents: List of document info dicts
        cache_expired: Whether Gemini cache needs refresh
        last_cache_timestamp: ISO timestamp of last cache creation
    """
    return Message(
        type=MessageType.RAG_STATE,
        data={
            "hasDocuments": has_documents,
            "documentCount": document_count,
            "documents": documents,
            "cacheExpired": cache_expired,
            "lastCacheTimestamp": last_cache_timestamp
        }
    )


def create_cache_refresh_complete_message(
    success: bool,
    cache_name: str | None = None,
    error: str | None = None
) -> Message:
    """
    Create a CACHE_REFRESH_COMPLETE message.
    
    Args:
        success: Whether cache refresh succeeded
        cache_name: New cache name if successful
        error: Error message if failed
    """
    return Message(
        type=MessageType.CACHE_REFRESH_COMPLETE,
        data={
            "success": success,
            "cacheName": cache_name,
            "error": error
        }
    )


def create_data_cleared_message(
    success: bool,
    cleared_items: dict | None = None,
    error: str | None = None
) -> Message:
    """
    Create a DATA_CLEARED message.

    Args:
        success: Whether clearing succeeded
        cleared_items: Dict with counts of cleared items
        error: Error message if failed
    """
    return Message(
        type=MessageType.DATA_CLEARED,
        data={
            "success": success,
            "clearedItems": cleared_items or {},
            "error": error
        }
    )


# Phase 10: LiveKit Turn Detection Metrics Helper Functions


def create_livekit_metrics_message(
    metrics: dict,
    format: str = "json"
) -> Message:
    """
    Create a LIVEKIT_METRICS message.

    Args:
        metrics: Metrics data (from LiveKitMetricsCollector.get_stats())
        format: Export format ("json", "prometheus", "csv")
    """
    return Message(
        type=MessageType.LIVEKIT_METRICS,
        data={
            "metrics": metrics,
            "format": format,
            "timestamp": __import__("time").time()
        }
    )


def create_livekit_health_message(
    status: str,
    uptime_seconds: float,
    total_checks: int,
    error_rate: float,
    avg_latency_ms: float,
    last_check_time: str | None = None
) -> Message:
    """
    Create a LIVEKIT_HEALTH message.

    Args:
        status: Health status ("healthy", "warning", "unhealthy", "degraded")
        uptime_seconds: Uptime in seconds
        total_checks: Total number of checks performed
        error_rate: Error rate (0.0 - 1.0)
        avg_latency_ms: Average latency in milliseconds
        last_check_time: ISO timestamp of last check (if any)
    """
    return Message(
        type=MessageType.LIVEKIT_HEALTH,
        data={
            "status": status,
            "uptimeSeconds": uptime_seconds,
            "totalChecks": total_checks,
            "errorRate": error_rate,
            "avgLatencyMs": avg_latency_ms,
            "lastCheckTime": last_check_time
        }
    )

