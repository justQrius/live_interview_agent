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


class TestQuestionDetectionIntegration:
    """Tests for question detection integration in the server."""

    def test_server_has_question_detector(self):
        """Server should initialize QuestionDetector."""
        from server import SidecarServer
        server = SidecarServer()
        
        assert hasattr(server, 'question_detector')
        assert server.question_detector is not None

    def test_server_has_question_detection_config(self):
        """Server should have question detection configuration."""
        from server import SidecarServer
        server = SidecarServer()
        
        assert hasattr(server, 'question_detection_enabled')
        assert hasattr(server, 'question_confidence_threshold')
        assert server.question_detection_enabled is True
        assert server.question_confidence_threshold == 0.7

    def test_question_detector_classifies_questions(self):
        """QuestionDetector in server should classify questions correctly."""
        from server import SidecarServer
        server = SidecarServer()
        
        # Test interview question
        is_q, conf, q_type = server.question_detector.is_actionable_question(
            "What is your experience with Python?"
        )
        assert is_q is True
        assert conf >= 0.7
        assert q_type == "interview_question"

    def test_question_detector_classifies_statements(self):
        """QuestionDetector in server should classify statements correctly."""
        from server import SidecarServer
        server = SidecarServer()
        
        # Test acknowledgment
        is_q, conf, q_type = server.question_detector.is_actionable_question(
            "Okay, that makes sense"
        )
        assert is_q is False
        assert q_type == "acknowledgment"

    def test_question_detector_with_history(self):
        """QuestionDetector in server should work with conversation history."""
        from server import SidecarServer
        server = SidecarServer()
        
        history = [
            {"speaker": "Interviewer", "text": "Tell me about your experience"},
            {"speaker": "Candidate", "text": "I have 5 years of experience..."},
        ]
        
        is_q, conf, q_type = server.question_detector.is_actionable_question(
            "What about testing?",
            history
        )
        assert is_q is True
        assert q_type == "follow_up"

    def test_feature_flag_can_be_disabled(self):
        """Question detection feature flag should be configurable."""
        from server import SidecarServer
        server = SidecarServer()
        
        # Feature flag should be enabled by default
        assert server.question_detection_enabled is True
        
        # Should be configurable
        server.question_detection_enabled = False
        assert server.question_detection_enabled is False

    def test_threshold_can_be_configured(self):
        """Question confidence threshold should be configurable."""
        from server import SidecarServer
        server = SidecarServer()
        
        # Default threshold
        assert server.question_confidence_threshold == 0.7
        
        # Should be configurable
        server.question_confidence_threshold = 0.5
        assert server.question_confidence_threshold == 0.5


class TestSessionPersistenceIntegration:
    """Tests for session persistence integration in the server."""

    def test_server_has_session_store(self):
        """Server should initialize SessionHistoryStore."""
        from server import SidecarServer
        server = SidecarServer()
        
        assert hasattr(server, 'session_store')
        assert server.session_store is not None

    def test_server_has_persistence_config(self):
        """Server should have session persistence configuration."""
        from server import SidecarServer
        server = SidecarServer()
        
        assert hasattr(server, 'session_persistence_enabled')
        assert server.session_persistence_enabled is True

    def test_session_state_has_persistent_session_id(self):
        """SessionState should have persistent_session_id field."""
        from server import SessionState
        state = SessionState()
        
        assert hasattr(state, 'persistent_session_id')
        assert state.persistent_session_id is None

    def test_session_store_can_create_sessions(self):
        """Session store in server should be able to create sessions."""
        from server import SidecarServer
        server = SidecarServer()
        
        session_id = server.session_store.create_session(
            context_files=["resume.pdf"]
        )
        
        assert session_id is not None
        session = server.session_store.get_session(session_id)
        assert session is not None
        assert session.context_files == ["resume.pdf"]

    def test_session_store_can_add_transcriptions(self):
        """Session store in server should be able to add transcriptions."""
        from server import SidecarServer
        server = SidecarServer()
        
        session_id = server.session_store.create_session()
        server.session_store.add_transcription(
            session_id=session_id,
            speaker="Interviewer",
            text="Tell me about yourself",
            timestamp=0.0,
            confidence=0.95
        )
        
        session = server.session_store.get_session(session_id)
        assert len(session.transcriptions) == 1
        assert session.transcriptions[0]["text"] == "Tell me about yourself"

    def test_session_store_can_add_answers(self):
        """Session store in server should be able to add answers."""
        from server import SidecarServer
        server = SidecarServer()
        
        session_id = server.session_store.create_session()
        server.session_store.add_answer(
            session_id=session_id,
            question="What is your experience?",
            answer="I have 5 years of experience...",
            confidence="high",
            latency_ms=500
        )
        
        session = server.session_store.get_session(session_id)
        assert len(session.answers) == 1
        assert session.answers[0]["question"] == "What is your experience?"

    def test_persistence_feature_flag_can_be_disabled(self):
        """Session persistence feature flag should be configurable."""
        from server import SidecarServer
        server = SidecarServer()
        
        assert server.session_persistence_enabled is True
        
        server.session_persistence_enabled = False
        assert server.session_persistence_enabled is False
