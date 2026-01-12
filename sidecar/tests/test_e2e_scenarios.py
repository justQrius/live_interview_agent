"""
End-to-End integration tests for system verification (Story 020).

Covers:
- Provider switching (Phase 2)
- Latency checks (Pipeline overhead)
"""

import asyncio
import importlib
import time
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.protocol import Message, MessageType
from src.audio.vad import SpeechSegment


class TestE2EScenarios:
    """End-to-End Scenarios for System Verification."""

    @pytest_asyncio.fixture
    async def server(self):
        """Start the server for testing with mocked components."""
        server_module = importlib.import_module("server")
        SidecarServer = getattr(server_module, "SidecarServer")

        async def fast_start_audio_processing(self) -> None:
            """Test-only fast path: skip model warmup wait; start loop."""
            if not getattr(self, "stt", None):
                raise RuntimeError("STT provider not initialized")

            VADProcessor = getattr(server_module, "VADProcessor")
            SpeakerRecognizer = getattr(server_module, "SpeakerRecognizer")
            NoiseReducer = getattr(server_module, "NoiseReducer")
            AudioCapture = getattr(server_module, "AudioCapture")

            self.vad = VADProcessor()
            self.vad.reset()
            self.speaker_recognizer = SpeakerRecognizer()
            self.noise_reducer = NoiseReducer(enabled=True)
            self.audio_capture = AudioCapture()

            await self.audio_capture.start_capture()
            self._audio_task = asyncio.create_task(self._audio_loop())

        # Patch all components
        with (
            patch("server.SpeakerRecognizer") as MockRecognizer,
            patch("server.ProviderFactory") as MockFactory,
            patch("server.VADProcessor") as MockVAD,
            patch("server.AudioCapture") as MockCapture,
            patch("server.NoiseReducer") as MockNoiseReducer,
            patch("server.ModelWarmer") as MockWarmer,
            patch("server.VectorStore") as MockVectorStore,
            patch("server.RAGEngine") as MockRAGEngine,
            patch("server.ContextManager") as MockContextManager,
            patch("server.GeminiCacheManager") as _MockGeminiCacheManager,
            patch("server.GeminiFileUploader") as _MockGeminiFileUploader,
            patch("server.SidecarServer._start_audio_processing", new=fast_start_audio_processing),
            patch("server.SidecarServer._init_rag_background", new_callable=AsyncMock),
        ):
            # 1. Setup Mock SpeakerRecognizer
            mock_recognizer = MockRecognizer.return_value
            mock_recognizer.create_embedding = MagicMock(return_value=np.zeros(192))
            mock_recognizer.verify_speaker.return_value = True

            # 2. Setup Mock ModelWarmer
            mock_warmer = MockWarmer.get_instance.return_value
            mock_warmer.wait_for_ready.return_value = False
            mock_models = MagicMock()
            mock_models.is_ready = False
            mock_models.vad_processor = None
            mock_models.speaker_recognizer = None
            mock_warmer.get_models.return_value = mock_models

            # 3. Setup Mock Factory and Providers
            mock_factory_instance = MockFactory.return_value

            mock_stt = MagicMock()
            mock_stt.transcribe = AsyncMock()
            mock_stt.transcribe.return_value = MagicMock(text="Hello world")
            mock_stt.is_available.return_value = True
            mock_factory_instance.get_stt_provider.return_value = mock_stt

            mock_llm = MagicMock()
            mock_llm.is_available.return_value = True

            async def mock_gen_resp(prompt, context, history):
                yield "This is a "
                yield "mock answer."

            mock_llm.generate_response = mock_gen_resp
            mock_factory_instance.get_llm_provider.return_value = mock_llm

            # 4. Setup Mock AudioCapture
            mock_capture = MockCapture.return_value
            mock_capture.start_capture = AsyncMock()
            mock_capture.stop_capture = AsyncMock()

            # Create a controllable audio stream
            self.audio_queue = asyncio.Queue()

            async def mock_stream():
                while True:
                    chunk = await self.audio_queue.get()
                    if chunk is None:
                        break
                    yield chunk

            mock_capture.get_audio_stream = mock_stream

            # 5. Setup Mock VAD
            mock_vad = MockVAD.return_value
            self.vad_segments_queue = asyncio.Queue()

            async def mock_process_chunk(chunk):
                if not self.vad_segments_queue.empty():
                    return await self.vad_segments_queue.get()
                return []

            mock_vad.process_chunk = mock_process_chunk
            mock_vad.reset = MagicMock()
            mock_vad.is_speaking = False
            mock_vad.current_duration = 0.0

            # 6. Setup other components
            mock_noise = MockNoiseReducer.return_value
            mock_noise.enabled = True
            mock_noise.reduce_noise = MagicMock(side_effect=lambda x: x)

            _mock_vector_store = MockVectorStore.return_value
            _mock_rag = MockRAGEngine.return_value
            mock_ctx = MockContextManager.return_value
            mock_ctx.get_all_chunks.return_value = []

            # Start Server
            srv = SidecarServer(host="127.0.0.1", port=8768)
            server_task = asyncio.create_task(srv.start())

            await asyncio.sleep(0.1)

            srv.mocks = {
                "factory_class": MockFactory,
                "factory_instance": mock_factory_instance,
                "stt": mock_stt,
                "llm": mock_llm,
                "vad": mock_vad,
                "audio_queue": self.audio_queue,
                "vad_queue": self.vad_segments_queue,
            }

            yield srv

            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_provider_switching(self, server):
        """Scenario 1: Switching Providers."""
        import websockets
        from src.providers.config import ProviderConfig, ProviderType

        async with websockets.connect(f"ws://{server.host}:{server.port}") as ws:
            start_msg_1 = Message(
                type=MessageType.START_SESSION,
                data={"apiKeys": {"gemini": "key1"}, "preferences": {"sttProvider": "gemini"}},
            )
            await ws.send(start_msg_1.to_json())

            resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(resp, str)

            calls = server.mocks["factory_class"].call_args_list
            assert len(calls) >= 1
            args, _ = calls[-1]
            config: ProviderConfig = args[0]
            assert config.preferred_stt == ProviderType.GEMINI

            await ws.send(Message(type=MessageType.STOP_SESSION).to_json())
            resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(resp, str)

            start_msg_2 = Message(
                type=MessageType.START_SESSION,
                data={"apiKeys": {"gemini": "key1", "groq": "key2"}, "preferences": {"sttProvider": "groq"}},
            )
            await ws.send(start_msg_2.to_json())
            resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(resp, str)

            calls = server.mocks["factory_class"].call_args_list
            args, _ = calls[-1]
            config = args[0]
            assert config.preferred_stt == ProviderType.GROQ

    @pytest.mark.asyncio
    async def test_pipeline_latency_check(self, server):
        """Scenario 2: Latency Check."""
        import websockets

        async with websockets.connect(f"ws://{server.host}:{server.port}") as ws:
            await ws.send(Message(type=MessageType.START_SESSION, data={"apiKey": "test"}).to_json())
            resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
            assert isinstance(resp, str)

            audio_chunk = b"\x00" * 1024

            segment = SpeechSegment(
                audio=audio_chunk,
                start_time=0.0,
                end_time=0.5,
                confidence=0.9,
            )
            await server.mocks["vad_queue"].put([segment])

            start_time = time.time()

            await server.mocks["audio_queue"].put(audio_chunk)

            transcription_received = False
            while not transcription_received:
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if not isinstance(resp, str):
                        continue
                    msg = Message.from_json(resp)
                    if msg.type == MessageType.TRANSCRIPTION:
                        transcription_received = True
                except asyncio.TimeoutError:
                    break

            end_time = time.time()
            latency = end_time - start_time

            assert transcription_received, "Did not receive transcription"
            assert latency < 0.5, f"Pipeline overhead too high: {latency}s"
