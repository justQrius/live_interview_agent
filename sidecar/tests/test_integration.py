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
        from unittest.mock import patch, MagicMock, AsyncMock

        # Patch all components to avoid real model loading and API calls
        with patch("server.SpeakerRecognizer") as MockRecognizer, \
             patch("server.ProviderFactory") as MockFactory, \
             patch("server.VADProcessor") as MockVAD, \
             patch("server.AudioCapture") as MockCapture, \
             patch("server.NoiseReducer") as MockNoiseReducer, \
             patch("server.ModelWarmer") as MockWarmer, \
             patch("server.VectorStore") as MockVectorStore, \
             patch("server.RAGEngine") as MockRAGEngine, \
             patch("server.ContextManager") as MockContextManager:

            # Setup mock SpeakerRecognizer
            mock_recognizer = MockRecognizer.return_value
            mock_recognizer.create_embedding = MagicMock(return_value=[0.1, 0.2, 0.3])

            # Setup mock ModelWarmer - return not ready so mocks are used
            mock_warmer = MockWarmer.get_instance.return_value
            mock_warmer.wait_for_ready.return_value = False
            mock_models = MagicMock()
            mock_models.is_ready = False
            mock_models.vad_processor = None
            mock_models.speaker_recognizer = None
            mock_warmer.get_models.return_value = mock_models

            # Setup mock Factory and Providers
            mock_factory = MockFactory.return_value
            mock_stt = MagicMock()
            mock_stt.transcribe = AsyncMock()
            mock_stt.is_available.return_value = True
            mock_factory.get_stt_provider.return_value = mock_stt
            
            mock_llm = MagicMock()
            mock_llm.is_available.return_value = True
            # Mock generate_response (standard interface)
            async def mock_gen_resp(prompt, context, history):
                yield "This is a "
                yield "mock answer."
            mock_llm.generate_response = mock_gen_resp
            mock_factory.get_llm_provider.return_value = mock_llm

            # Setup mock AudioCapture
            mock_capture = MockCapture.return_value
            mock_capture.start_capture = AsyncMock()
            mock_capture.stop_capture = AsyncMock()

            # Mock audio stream that produces nothing (idle)
            async def mock_stream():
                while True:
                    await asyncio.sleep(0.5)
                    yield b""  # Empty chunk
            mock_capture.get_audio_stream = mock_stream

            # Setup mock NoiseReducer
            mock_noise = MockNoiseReducer.return_value
            mock_noise.enabled = True
            mock_noise.reduce_noise = MagicMock(side_effect=lambda x: x)
            
            # Setup mock RAG/Context
            mock_vector_store = MockVectorStore.return_value
            mock_rag = MockRAGEngine.return_value
            mock_ctx = MockContextManager.return_value
            mock_ctx.get_all_chunks.return_value = []

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
    async def test_full_session_lifecycle_new_payload(self, server):
        """Test complete session lifecycle with new payload format."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # 1. Start session with full config
            start_msg = Message(
                type=MessageType.START_SESSION,
                data={
                    "apiKeys": {
                        "gemini": "test-gemini-key",
                        "groq": "test-groq-key"
                    },
                    "preferences": {
                        "sttProvider": "groq",
                        "llmProvider": "gemini"
                    }
                }
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
            for _ in range(5):  # Expect status + 2 chunks + completion + status
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
    async def test_start_session_without_api_key(self):
        """Test that starting session without API key returns error."""
        import websockets
        from server import SidecarServer
        from unittest.mock import patch, MagicMock, AsyncMock
        
        # Patch dependencies but ensure Factory raises error
        with patch("server.SpeakerRecognizer"), \
             patch("server.ProviderFactory") as MockFactory, \
             patch("server.VADProcessor"), \
             patch("server.AudioCapture"), \
             patch("server.NoiseReducer"), \
             patch("server.ModelWarmer"), \
             patch("server.VectorStore"), \
             patch("server.RAGEngine"), \
             patch("server.ContextManager"):
             
             # Configure factory to raise error
             mock_factory = MockFactory.return_value
             mock_factory.get_stt_provider.side_effect = Exception("No STT available")
             
             srv = SidecarServer(host="127.0.0.1", port=8767)
             server_task = asyncio.create_task(srv.start())
             await asyncio.sleep(0.1)
             
             try:
                async with websockets.connect("ws://127.0.0.1:8767") as ws:
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
                    assert "initialize providers" in error_msg.data["message"]
             finally:
                await srv.stop()
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass

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
