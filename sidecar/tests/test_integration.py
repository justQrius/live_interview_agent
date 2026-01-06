"""
Integration tests for bidirectional WebSocket communication.

Tests the complete message flow between client and server.
"""

import asyncio
import json
import pytest
import pytest_asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from protocol import (
    Message,
    MessageType,
    SessionStatus,
    ConfidenceLevel,
)


class TestBidirectionalMessaging:
    """Integration tests for bidirectional WebSocket messaging."""

    @pytest_asyncio.fixture
    async def server(self):
        """Start the server for testing."""
        from server import SidecarServer

        srv = SidecarServer(host="127.0.0.1", port=8766)  # Different port for tests
        server_task = asyncio.create_task(srv.start())

        await asyncio.sleep(0.1)

        yield srv

        await srv.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, server):
        """Test complete session lifecycle: connect -> start -> stop -> disconnect."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # 1. Start session with API key
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key-12345"}
            )
            await ws.send(start_msg.to_json())

            # Should receive STATUS: listening
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            status_msg = Message.from_json(response)
            assert status_msg.type == MessageType.STATUS
            assert status_msg.data["state"] == "listening"

            # 2. Stop session
            stop_msg = Message(type=MessageType.STOP_SESSION)
            await ws.send(stop_msg.to_json())

            # Should receive STATUS: idle
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            status_msg = Message.from_json(response)
            assert status_msg.type == MessageType.STATUS
            assert status_msg.data["state"] == "idle"

    @pytest.mark.asyncio
    async def test_manual_question_flow(self, server):
        """Test sending a manual question and receiving a response."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # Start session first
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key"}
            )
            await ws.send(start_msg.to_json())
            await ws.recv()  # Consume status response

            # Send manual question
            question_msg = Message(
                type=MessageType.MANUAL_QUESTION,
                data={"question": "What is Python?"}
            )
            await ws.send(question_msg.to_json())

            # Should receive:
            # 1. STATUS: processing
            # 2. ANSWER_CHUNK (possibly multiple)
            # 3. STATUS: listening

            responses = []
            for _ in range(3):  # Expect up to 3 messages
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    responses.append(Message.from_json(response))
                except asyncio.TimeoutError:
                    break

            # Verify we got at least a status update and an answer
            message_types = [r.type for r in responses]
            assert MessageType.STATUS in message_types
            assert MessageType.ANSWER_CHUNK in message_types

    @pytest.mark.asyncio
    async def test_start_session_without_api_key(self, server):
        """Test that starting session without API key returns error."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # Try to start session without API key
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={}
            )
            await ws.send(start_msg.to_json())

            # Should receive ERROR
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            error_msg = Message.from_json(response)
            assert error_msg.type == MessageType.ERROR
            assert "API key" in error_msg.data["message"]

    @pytest.mark.asyncio
    async def test_calibration_flow(self, server):
        """Test voice calibration message flow."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # Send calibration request
            calibrate_msg = Message(
                type=MessageType.CALIBRATE_VOICE,
                data={"audioData": "base64-audio-data-here"}
            )
            await ws.send(calibrate_msg.to_json())

            # Should receive STATUS: calibrating, then STATUS: idle
            responses = []
            for _ in range(2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    responses.append(Message.from_json(response))
                except asyncio.TimeoutError:
                    break

            # Verify calibration flow
            assert len(responses) >= 1
            states = [r.data["state"] for r in responses if r.type == MessageType.STATUS]
            assert "calibrating" in states

    @pytest.mark.asyncio
    async def test_context_upload(self, server):
        """Test context upload message handling."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # Start session first
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key"}
            )
            await ws.send(start_msg.to_json())
            await ws.recv()

            # Upload context files
            upload_msg = Message(
                type=MessageType.UPLOAD_CONTEXT,
                data={
                    "files": [
                        {"name": "resume.pdf", "content": "base64-pdf-content"},
                        {"name": "job_description.txt", "content": "base64-txt-content"},
                    ]
                }
            )
            await ws.send(upload_msg.to_json())

            # Should receive acknowledgment (STATUS message)
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            msg = Message.from_json(response)
            assert msg.type == MessageType.STATUS

    @pytest.mark.asyncio
    async def test_multiple_clients(self, server):
        """Test that server handles multiple simultaneous clients."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws1:
            async with websockets.connect("ws://127.0.0.1:8766") as ws2:
                # Both clients start sessions
                start_msg = Message(
                    type=MessageType.START_SESSION,
                    data={"apiKey": "test-api-key"}
                )

                await ws1.send(start_msg.to_json())
                await ws2.send(start_msg.to_json())

                # Both should receive responses
                response1 = await asyncio.wait_for(ws1.recv(), timeout=1.0)
                response2 = await asyncio.wait_for(ws2.recv(), timeout=1.0)

                msg1 = Message.from_json(response1)
                msg2 = Message.from_json(response2)

                assert msg1.type == MessageType.STATUS
                assert msg2.type == MessageType.STATUS

    @pytest.mark.asyncio
    async def test_rapid_message_exchange(self, server):
        """Test that server handles rapid message exchange."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # Start session
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key"}
            )
            await ws.send(start_msg.to_json())
            await ws.recv()

            # Send multiple questions rapidly
            for i in range(5):
                question_msg = Message(
                    type=MessageType.MANUAL_QUESTION,
                    data={"question": f"Question {i}?"}
                )
                await ws.send(question_msg.to_json())

            # Collect all responses
            responses = []
            for _ in range(15):  # Expect multiple responses per question
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    responses.append(Message.from_json(response))
                except asyncio.TimeoutError:
                    break

            # Should have received responses for all questions
            assert len(responses) >= 5  # At least one response per question

    @pytest.mark.asyncio
    async def test_message_format_validation(self, server):
        """Test that messages maintain correct format throughout exchange."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # Send well-formed message
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test-api-key"}
            )
            await ws.send(start_msg.to_json())

            response = await asyncio.wait_for(ws.recv(), timeout=1.0)

            # Verify response is valid JSON
            parsed = json.loads(response)
            assert "type" in parsed
            assert parsed["type"] in [t.value for t in MessageType]

            # Verify we can parse it back to Message
            msg = Message.from_json(response)
            assert msg.type in MessageType
