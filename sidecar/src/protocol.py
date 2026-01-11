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


class SessionStatus(str, Enum):
    """Session status values."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    CALIBRATING = "calibrating"


class ConfidenceLevel(str, Enum):
    """Confidence levels for answers."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Speaker(str, Enum):
    """Speaker labels for diarization."""

    USER = "User"
    INTERVIEWER = "Interviewer"


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
    message: str = ""
) -> Message:
    return Message(
        type=MessageType.EXTRACTION_PROGRESS,
        data={
            "stage": stage,
            "progress": progress,
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
