"""
Integration tests for bidirectional WebSocket communication.

Tests the complete message flow between client and server.
"""

import asyncio
import importlib
import json
import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.protocol import (
    ConfidenceLevel,
    Message,
    MessageType,
    SessionStatus,
)


class TestBidirectionalMessaging:
    """Integration tests for bidirectional WebSocket messaging."""

    @pytest_asyncio.fixture
    async def server(self):
        """Start the server for testing."""
        from unittest.mock import AsyncMock, MagicMock, patch

        server_module = importlib.import_module("server")
        SidecarServer = getattr(server_module, "SidecarServer")

        # Patch all components to avoid real model loading and API calls.
        # Also stub audio startup so START_SESSION responds quickly.
        with (
            patch("server.SpeakerRecognizer") as MockRecognizer,
            patch("server.ProviderFactory") as MockFactory,
            patch("server.VADProcessor") as _MockVAD,
            patch("server.AudioCapture") as _MockCapture,
            patch("server.NoiseReducer") as _MockNoiseReducer,
            patch("server.ModelWarmer") as MockWarmer,
            patch("server.VectorStore") as _MockVectorStore,
            patch("server.RAGEngine") as _MockRAGEngine,
            patch("server.ContextManager") as _MockContextManager,
            patch("server.GeminiCacheManager") as _MockGeminiCacheManager,
            patch("server.GeminiFileUploader") as _MockGeminiFileUploader,
            patch("server.SidecarServer._start_audio_processing", new_callable=AsyncMock),
            patch("server.SidecarServer._init_rag_background", new_callable=AsyncMock),
        ):
            # Setup mock SpeakerRecognizer
            mock_recognizer = MockRecognizer.return_value
            mock_recognizer.create_embedding = MagicMock(return_value=[0.1, 0.2, 0.3])

            # Setup mock ModelWarmer
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

            async def mock_gen_resp(prompt, context, history):
                yield "This is a "
                yield "mock answer."

            mock_llm.generate_response = mock_gen_resp
            mock_factory.get_llm_provider.return_value = mock_llm

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
                    "apiKeys": {"gemini": "test-gemini-key", "groq": "test-groq-key"},
                    "preferences": {"sttProvider": "groq", "llmProvider": "gemini"},
                },
            )
            await ws.send(start_msg.to_json())

            # Should receive STATUS: listening
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(response, str)
            status_msg = Message.from_json(response)
            assert status_msg.type == MessageType.STATUS
            assert status_msg.data is not None
            assert status_msg.data["state"] == "listening"

            # 2. Stop session
            stop_msg = Message(type=MessageType.STOP_SESSION)
            await ws.send(stop_msg.to_json())

            # Should receive STATUS: idle
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(response, str)
            status_msg = Message.from_json(response)
            assert status_msg.type == MessageType.STATUS
            assert status_msg.data is not None
            assert status_msg.data["state"] == "idle"

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, server):
        """Test complete session lifecycle: connect -> start -> stop -> disconnect."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # 1. Start session with API key
            start_msg = Message(type=MessageType.START_SESSION, data={"apiKey": "test-api-key-12345"})
            await ws.send(start_msg.to_json())

            # Should receive STATUS: listening
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(response, str)
            status_msg = Message.from_json(response)
            assert status_msg.type == MessageType.STATUS
            assert status_msg.data is not None
            assert status_msg.data["state"] == "listening"

            # 2. Stop session
            stop_msg = Message(type=MessageType.STOP_SESSION)
            await ws.send(stop_msg.to_json())

            # Should receive STATUS: idle
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(response, str)
            status_msg = Message.from_json(response)
            assert status_msg.type == MessageType.STATUS
            assert status_msg.data is not None
            assert status_msg.data["state"] == "idle"

    @pytest.mark.asyncio
    async def test_manual_question_flow(self, server):
        """Test sending a manual question and receiving a response."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            # Start session first
            start_msg = Message(type=MessageType.START_SESSION, data={"apiKey": "test-api-key"})
            await ws.send(start_msg.to_json())
            await ws.recv()  # Consume status response

            # Send manual question
            question_msg = Message(type=MessageType.MANUAL_QUESTION, data={"question": "What is Python?"})
            await ws.send(question_msg.to_json())

            # Should receive:
            # 1. STATUS: processing
            # 2. ANSWER_CHUNK (possibly multiple)
            # 3. STATUS: listening
            responses = []
            for _ in range(5):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(response, str):
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
        from unittest.mock import AsyncMock, patch

        server_module = importlib.import_module("server")
        SidecarServer = getattr(server_module, "SidecarServer")

        # Patch dependencies but ensure Factory raises error
        with (
            patch("server.SpeakerRecognizer"),
            patch("server.ProviderFactory") as MockFactory,
            patch("server.VADProcessor"),
            patch("server.AudioCapture"),
            patch("server.NoiseReducer"),
            patch("server.ModelWarmer"),
            patch("server.VectorStore"),
            patch("server.RAGEngine"),
            patch("server.ContextManager"),
            patch("server.GeminiCacheManager"),
            patch("server.GeminiFileUploader"),
            patch("server.SidecarServer._start_audio_processing", new_callable=AsyncMock),
            patch("server.SidecarServer._init_rag_background", new_callable=AsyncMock),
        ):
            # Configure factory to raise error
            mock_factory = MockFactory.return_value
            mock_factory.get_stt_provider.side_effect = Exception("No STT available")

            srv = SidecarServer(host="127.0.0.1", port=8767)
            server_task = asyncio.create_task(srv.start())
            await asyncio.sleep(0.1)

            try:
                async with websockets.connect("ws://127.0.0.1:8767") as ws:
                    start_msg = Message(type=MessageType.START_SESSION, data={})
                    await ws.send(start_msg.to_json())

                    response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    assert isinstance(response, str)
                    error_msg = Message.from_json(response)
                    assert error_msg.type == MessageType.ERROR
                    assert error_msg.data is not None
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
            calibrate_msg = Message(
                type=MessageType.CALIBRATE_VOICE,
                data={"audioData": "base64-audio-data-here"},
            )
            await ws.send(calibrate_msg.to_json())

            responses = []
            for _ in range(2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(response, str):
                        responses.append(Message.from_json(response))
                except asyncio.TimeoutError:
                    break

            assert len(responses) >= 1
            states = [r.data["state"] for r in responses if r.type == MessageType.STATUS and r.data is not None]
            assert "calibrating" in states

    @pytest.mark.asyncio
    async def test_context_upload(self, server):
        """Test context upload message handling."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            start_msg = Message(type=MessageType.START_SESSION, data={"apiKey": "test-api-key"})
            await ws.send(start_msg.to_json())
            await ws.recv()

            upload_msg = Message(
                type=MessageType.UPLOAD_CONTEXT,
                data={
                    "files": [
                        {"name": "resume.pdf", "content": "base64-pdf-content"},
                        {"name": "job_description.txt", "content": "base64-txt-content"},
                    ]
                },
            )
            await ws.send(upload_msg.to_json())

            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(response, str)
            msg = Message.from_json(response)
            assert msg.type == MessageType.STATUS

    @pytest.mark.asyncio
    async def test_multiple_clients(self, server):
        """Test that server handles multiple simultaneous clients."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws1:
            async with websockets.connect("ws://127.0.0.1:8766") as ws2:
                start_msg = Message(type=MessageType.START_SESSION, data={"apiKey": "test-api-key"})

                await ws1.send(start_msg.to_json())
                await ws2.send(start_msg.to_json())

                response1 = await asyncio.wait_for(ws1.recv(), timeout=1.0)
                response2 = await asyncio.wait_for(ws2.recv(), timeout=1.0)
                assert isinstance(response1, str)
                assert isinstance(response2, str)

                msg1 = Message.from_json(response1)
                msg2 = Message.from_json(response2)

                assert msg1.type == MessageType.STATUS
                assert msg2.type == MessageType.STATUS

    @pytest.mark.asyncio
    async def test_rapid_message_exchange(self, server):
        """Test that server handles rapid message exchange."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            start_msg = Message(type=MessageType.START_SESSION, data={"apiKey": "test-api-key"})
            await ws.send(start_msg.to_json())
            await ws.recv()

            for i in range(5):
                question_msg = Message(type=MessageType.MANUAL_QUESTION, data={"question": f"Question {i}?"})
                await ws.send(question_msg.to_json())

            responses = []
            for _ in range(15):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    if isinstance(response, str):
                        responses.append(Message.from_json(response))
                except asyncio.TimeoutError:
                    break

            assert len(responses) >= 5

    @pytest.mark.asyncio
    async def test_message_format_validation(self, server):
        """Test that messages maintain correct format throughout exchange."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:8766") as ws:
            start_msg = Message(type=MessageType.START_SESSION, data={"apiKey": "test-api-key"})
            await ws.send(start_msg.to_json())

            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(response, str)

            parsed = json.loads(response)
            assert "type" in parsed
            assert parsed["type"] in [t.value for t in MessageType]

            msg = Message.from_json(response)
            assert msg.type in MessageType
