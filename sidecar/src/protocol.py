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

    # Server -> Client
    TRANSCRIPTION = "TRANSCRIPTION"
    ANSWER_START = "ANSWER_START"
    ANSWER_CHUNK = "ANSWER_CHUNK"
    ERROR = "ERROR"
    STATUS = "STATUS"


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

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker.value,
            "text": self.text,
            "timestamp": self.timestamp,
            "confidence": self.confidence
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
    data = TranscriptionData(speaker, text, timestamp, confidence)
    return Message(type=MessageType.TRANSCRIPTION, data=data.to_dict())


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
