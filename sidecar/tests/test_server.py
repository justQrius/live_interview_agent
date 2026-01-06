"""
Tests for the WebSocket server.

Following TDD: these tests are written first, before implementation.
"""

import asyncio
import json
import pytest
import pytest_asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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


class TestProtocol:
    """Tests for the message protocol."""

    def test_message_type_values(self):
        """Message types should match the protocol specification."""
        assert MessageType.START_SESSION.value == "START_SESSION"
        assert MessageType.STOP_SESSION.value == "STOP_SESSION"
        assert MessageType.UPLOAD_CONTEXT.value == "UPLOAD_CONTEXT"
        assert MessageType.CALIBRATE_VOICE.value == "CALIBRATE_VOICE"
        assert MessageType.MANUAL_QUESTION.value == "MANUAL_QUESTION"
        assert MessageType.TRANSCRIPTION.value == "TRANSCRIPTION"
        assert MessageType.ANSWER_CHUNK.value == "ANSWER_CHUNK"
        assert MessageType.ERROR.value == "ERROR"
        assert MessageType.STATUS.value == "STATUS"

    def test_session_status_values(self):
        """Session status should match expected values."""
        assert SessionStatus.IDLE.value == "idle"
        assert SessionStatus.LISTENING.value == "listening"
        assert SessionStatus.PROCESSING.value == "processing"
        assert SessionStatus.CALIBRATING.value == "calibrating"

    def test_confidence_level_values(self):
        """Confidence levels should match expected values."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_speaker_values(self):
        """Speaker labels should match expected values."""
        assert Speaker.USER.value == "User"
        assert Speaker.INTERVIEWER.value == "Interviewer"

    def test_message_serialization(self):
        """Messages should serialize to valid JSON."""
        msg = Message(type=MessageType.START_SESSION, data={"apiKey": "test-key"})
        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "START_SESSION"
        assert parsed["data"]["apiKey"] == "test-key"

    def test_message_deserialization(self):
        """Messages should deserialize from valid JSON."""
        json_str = '{"type": "START_SESSION", "data": {"apiKey": "test-key"}}'
        msg = Message.from_json(json_str)

        assert msg.type == MessageType.START_SESSION
        assert msg.data["apiKey"] == "test-key"

    def test_message_without_data(self):
        """Messages without data should serialize correctly."""
        msg = Message(type=MessageType.STOP_SESSION)
        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "STOP_SESSION"
        assert "data" not in parsed

    def test_create_transcription_message(self):
        """Transcription messages should be created correctly."""
        msg = create_transcription_message(
            speaker=Speaker.INTERVIEWER,
            text="Tell me about yourself",
            timestamp=1234567890.123,
            confidence=0.95
        )

        assert msg.type == MessageType.TRANSCRIPTION
        assert msg.data["speaker"] == "Interviewer"
        assert msg.data["text"] == "Tell me about yourself"
        assert msg.data["timestamp"] == 1234567890.123
        assert msg.data["confidence"] == 0.95

    def test_create_answer_chunk_message(self):
        """Answer chunk messages should be created correctly."""
        # Incomplete chunk
        msg = create_answer_chunk_message(chunk="I have experience with...")
        assert msg.type == MessageType.ANSWER_CHUNK
        assert msg.data["chunk"] == "I have experience with..."
        assert msg.data["complete"] is False
        assert "confidence" not in msg.data

        # Complete chunk with confidence
        msg = create_answer_chunk_message(
            chunk="...in Python.",
            complete=True,
            confidence=ConfidenceLevel.HIGH
        )
        assert msg.data["complete"] is True
        assert msg.data["confidence"] == "high"

    def test_create_error_message(self):
        """Error messages should be created correctly."""
        msg = create_error_message("Connection failed", code="ERR_CONNECTION")
        assert msg.type == MessageType.ERROR
        assert msg.data["message"] == "Connection failed"
        assert msg.data["code"] == "ERR_CONNECTION"

    def test_create_status_message(self):
        """Status messages should be created correctly."""
        msg = create_status_message(SessionStatus.LISTENING)
        assert msg.type == MessageType.STATUS
        assert msg.data["state"] == "listening"


class TestWebSocketServer:
    """Tests for the WebSocket server."""

    @pytest.fixture
    def server_port(self):
        """Return the expected server port."""
        return 8765

    @pytest.fixture
    def server_host(self):
        """Return the expected server host."""
        return "127.0.0.1"

    @pytest_asyncio.fixture
    async def server(self, server_host, server_port):
        """Start the server for testing."""
        from server import SidecarServer

        srv = SidecarServer(host=server_host, port=server_port)
        server_task = asyncio.create_task(srv.start())

        # Wait for server to be ready
        await asyncio.sleep(0.1)

        yield srv

        # Cleanup
        await srv.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_server_starts_on_correct_port(self, server, server_port):
        """Server should listen on port 8765."""
        import websockets

        async with websockets.connect(f"ws://127.0.0.1:{server_port}") as ws:
            # Connection successful means server is running
            assert ws is not None
            # Verify connection works by sending a ping
            await ws.ping()

    @pytest.mark.asyncio
    async def test_server_accepts_start_session(self, server, server_port):
        """Server should accept START_SESSION messages."""
        import websockets

        async with websockets.connect(f"ws://127.0.0.1:{server_port}") as ws:
            msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key"}
            )
            await ws.send(msg.to_json())

            # Should receive STATUS message back
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            response_msg = Message.from_json(response)

            assert response_msg.type == MessageType.STATUS

    @pytest.mark.asyncio
    async def test_server_accepts_stop_session(self, server, server_port):
        """Server should accept STOP_SESSION messages."""
        import websockets

        async with websockets.connect(f"ws://127.0.0.1:{server_port}") as ws:
            # First start a session
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key"}
            )
            await ws.send(start_msg.to_json())
            await ws.recv()  # Consume status response

            # Then stop it
            stop_msg = Message(type=MessageType.STOP_SESSION)
            await ws.send(stop_msg.to_json())

            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            response_msg = Message.from_json(response)

            assert response_msg.type == MessageType.STATUS
            assert response_msg.data["state"] == "idle"

    @pytest.mark.asyncio
    async def test_server_handles_invalid_json(self, server, server_port):
        """Server should handle invalid JSON gracefully."""
        import websockets

        async with websockets.connect(f"ws://127.0.0.1:{server_port}") as ws:
            await ws.send("not valid json {{{")

            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            response_msg = Message.from_json(response)

            assert response_msg.type == MessageType.ERROR

    @pytest.mark.asyncio
    async def test_server_handles_unknown_message_type(self, server, server_port):
        """Server should handle unknown message types gracefully."""
        import websockets

        async with websockets.connect(f"ws://127.0.0.1:{server_port}") as ws:
            await ws.send('{"type": "UNKNOWN_TYPE"}')

            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            response_msg = Message.from_json(response)

            assert response_msg.type == MessageType.ERROR

    @pytest.mark.asyncio
    async def test_server_accepts_manual_question(self, server, server_port):
        """Server should accept MANUAL_QUESTION messages."""
        import websockets

        async with websockets.connect(f"ws://127.0.0.1:{server_port}") as ws:
            # Start session first
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key"}
            )
            await ws.send(start_msg.to_json())
            await ws.recv()

            # Send manual question
            question_msg = Message(
                type=MessageType.MANUAL_QUESTION,
                data={"question": "Tell me about your experience"}
            )
            await ws.send(question_msg.to_json())

            # Should receive at least a status update
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            response_msg = Message.from_json(response)

            # Either STATUS (processing) or ANSWER_CHUNK (if mocked)
            assert response_msg.type in [MessageType.STATUS, MessageType.ANSWER_CHUNK]
