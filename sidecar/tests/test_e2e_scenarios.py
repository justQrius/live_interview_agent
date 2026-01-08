"""
End-to-End integration tests for system verification (Story 020).

Covers:
- Provider switching (Phase 2)
- Latency checks (Pipeline overhead)
"""

import asyncio
import json
import time
import pytest
import pytest_asyncio
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from protocol import (
    Message,
    MessageType,
    SessionStatus,
    Speaker
)
from audio.vad import SpeechSegment

class TestE2EScenarios:
    """End-to-End Scenarios for System Verification."""

    @pytest_asyncio.fixture
    async def server(self):
        """Start the server for testing with mocked components."""
        from server import SidecarServer

        # Patch all components
        with patch("server.SpeakerRecognizer") as MockRecognizer, \
             patch("server.ProviderFactory") as MockFactory, \
             patch("server.VADProcessor") as MockVAD, \
             patch("server.AudioCapture") as MockCapture, \
             patch("server.NoiseReducer") as MockNoiseReducer, \
             patch("server.ModelWarmer") as MockWarmer, \
             patch("server.VectorStore") as MockVectorStore, \
             patch("server.RAGEngine") as MockRAGEngine, \
             patch("server.ContextManager") as MockContextManager:

            # 1. Setup Mock SpeakerRecognizer
            mock_recognizer = MockRecognizer.return_value
            mock_recognizer.create_embedding = MagicMock(return_value=np.zeros(192))
            mock_recognizer.verify_speaker.return_value = True  # Always verify as user for now

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
            
            # Create distinct mocks for different providers if needed, 
            # or just use a generic one that tracks calls.
            mock_stt = MagicMock()
            mock_stt.transcribe = AsyncMock()
            # Default transcription
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
            # We will inject chunks into this queue
            self.audio_queue = asyncio.Queue()
            
            async def mock_stream():
                while True:
                    chunk = await self.audio_queue.get()
                    if chunk is None: # Signal to stop
                        break
                    yield chunk
                    
            mock_capture.get_audio_stream = mock_stream

            # 5. Setup Mock VAD
            mock_vad = MockVAD.return_value
            # We will control what VAD returns via a side_effect or property we can change
            self.vad_segments_queue = asyncio.Queue()
            
            async def mock_process_chunk(chunk):
                # Check if we have pre-queued segments for this chunk interaction
                if not self.vad_segments_queue.empty():
                    return await self.vad_segments_queue.get()
                return []
            
            mock_vad.process_chunk = mock_process_chunk
            mock_vad.reset = MagicMock()

            # 6. Setup other components
            mock_noise = MockNoiseReducer.return_value
            mock_noise.enabled = True
            mock_noise.reduce_noise = MagicMock(side_effect=lambda x: x)
            
            mock_vector_store = MockVectorStore.return_value
            mock_rag = MockRAGEngine.return_value
            mock_ctx = MockContextManager.return_value
            mock_ctx.get_all_chunks.return_value = []

            # Start Server
            srv = SidecarServer(host="127.0.0.1", port=8768)
            server_task = asyncio.create_task(srv.start())

            await asyncio.sleep(0.1)

            # Expose mocks to tests via the server object (hacky but effective)
            srv.mocks = {
                "factory_class": MockFactory,
                "factory_instance": mock_factory_instance,
                "stt": mock_stt,
                "llm": mock_llm,
                "vad": mock_vad,
                "audio_queue": self.audio_queue,
                "vad_queue": self.vad_segments_queue
            }

            yield srv

            # Cleanup
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_provider_switching(self, server):
        """
        Scenario 1: Switching Providers.
        Verify that restarting the session with different preferences 
        re-initializes the ProviderFactory with the new config.
        """
        import websockets
        from providers.config import ProviderConfig, ProviderType

        async with websockets.connect(f"ws://{server.host}:{server.port}") as ws:
            # --- Step 1: Start with Gemini STT ---
            start_msg_1 = Message(
                type=MessageType.START_SESSION,
                data={
                    "apiKeys": {"gemini": "key1"},
                    "preferences": {"sttProvider": "gemini"}
                }
            )
            await ws.send(start_msg_1.to_json())
            
            # Wait for listening status
            await asyncio.wait_for(ws.recv(), timeout=1.0) # Status: Listening

            # Verify Factory was initialized with gemini
            # server.mocks["factory_class"] is the Mock class. 
            # It is instantiated as ProviderFactory(config).
            # We check the arguments of the constructor call.
            
            calls = server.mocks["factory_class"].call_args_list
            assert len(calls) >= 1
            args, _ = calls[-1] # Get most recent call
            config: ProviderConfig = args[0]
            assert config.preferred_stt == ProviderType.GEMINI
            
            # --- Step 2: Stop Session ---
            await ws.send(Message(type=MessageType.STOP_SESSION).to_json())
            await asyncio.wait_for(ws.recv(), timeout=1.0) # Status: Idle

            # --- Step 3: Switch to Groq STT ---
            start_msg_2 = Message(
                type=MessageType.START_SESSION,
                data={
                    "apiKeys": {"gemini": "key1", "groq": "key2"},
                    "preferences": {"sttProvider": "groq"}
                }
            )
            await ws.send(start_msg_2.to_json())
            await asyncio.wait_for(ws.recv(), timeout=1.0) # Status: Listening

            # Verify Factory was initialized with groq
            calls = server.mocks["factory_class"].call_args_list
            args, _ = calls[-1]
            config: ProviderConfig = args[0]
            assert config.preferred_stt == ProviderType.GROQ

    @pytest.mark.asyncio
    async def test_pipeline_latency_check(self, server):
        """
        Scenario 2: Latency Check.
        Measure time from Audio Input -> Transcription Message.
        This verifies the pipeline overhead (VAD -> STT -> WS) is minimal.
        """
        import websockets

        async with websockets.connect(f"ws://{server.host}:{server.port}") as ws:
            # Start Session
            await ws.send(Message(
                type=MessageType.START_SESSION,
                data={"apiKey": "test"}
            ).to_json())
            await asyncio.wait_for(ws.recv(), timeout=1.0)

            # Prepare simulated audio event
            audio_chunk = b"\x00" * 1024
            
            # Prepare VAD to detect speech
            # When process_chunk is called, it will return this segment
            segment = SpeechSegment(
                audio=audio_chunk,
                start_time=0.0,
                end_time=0.5,
                confidence=0.9
            )
            await server.mocks["vad_queue"].put([segment])

            # Start timer
            start_time = time.time()
            
            # Inject audio
            await server.mocks["audio_queue"].put(audio_chunk)

            # Wait for TRANSCRIPTION message
            # We might get other messages first? (maybe logs/status if changed)
            # Loop until we find it
            transcription_received = False
            while not transcription_received:
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = Message.from_json(resp)
                    if msg.type == MessageType.TRANSCRIPTION:
                        transcription_received = True
                except asyncio.TimeoutError:
                    break
            
            end_time = time.time()
            latency = end_time - start_time
            
            assert transcription_received, "Did not receive transcription"
            
            # The mocked STT and VAD are instant, so this measures pure pipeline overhead
            # We expect it to be very fast (e.g., < 100ms)
            print(f"Pipeline Latency: {latency*1000:.2f}ms")
            assert latency < 0.5, f"Pipeline overhead too high: {latency}s"
