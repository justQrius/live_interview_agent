import asyncio
import asyncio
import importlib
import os
import sys

import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch

# Mock speechbrain before importing anything that uses it
sys.modules["speechbrain"] = MagicMock()
sys.modules["speechbrain.inference"] = MagicMock()
sys.modules["speechbrain.inference.speaker"] = MagicMock()

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

server_module = importlib.import_module("server")
SidecarServer = getattr(server_module, "SidecarServer")
SessionStatus = getattr(server_module, "SessionStatus")
Speaker = getattr(server_module, "Speaker")

from src.protocol import Message, MessageType
from src.audio.vad import SpeechSegment
from src.providers.base import TranscriptionResult


@pytest.fixture
def mock_components():
    with (
        patch("server.ProviderFactory") as mock_factory_cls,
        patch("server.GeminiCacheManager"),
        patch("server.GeminiFileUploader"),
        patch("server.VADProcessor") as mock_vad_cls,
        patch("server.AudioCapture") as mock_capture_cls,
        patch("server.SpeakerRecognizer") as mock_recognizer_cls,
        patch("server.ModelWarmer") as mock_warmer_cls,
        patch("server.NoiseReducer") as mock_noise_reducer_cls,
        patch("server.SidecarServer._init_rag_background", new_callable=AsyncMock),
    ):
        mock_factory = mock_factory_cls.return_value
        mock_stt = MagicMock()
        mock_vad = mock_vad_cls.return_value
        mock_capture = mock_capture_cls.return_value
        mock_recognizer = mock_recognizer_cls.return_value

        mock_factory.get_stt_provider.return_value = mock_stt
        mock_factory.get_llm_provider.side_effect = Exception("No LLM")

        mock_stt.is_available.return_value = True

        # Configure ModelWarmer mock
        mock_warmer = mock_warmer_cls.get_instance.return_value
        mock_warmer.wait_for_ready.return_value = False
        mock_models = MagicMock()
        mock_models.is_ready = False
        mock_models.vad_processor = None
        mock_models.speaker_recognizer = None
        mock_warmer.get_models.return_value = mock_models

        # Configure NoiseReducer mock - pass through audio unchanged
        mock_noise_reducer = mock_noise_reducer_cls.return_value
        mock_noise_reducer.enabled = True
        mock_noise_reducer.reduce_noise = MagicMock(side_effect=lambda audio: audio)

        # Configure AsyncMocks
        mock_capture.start_capture = AsyncMock()
        mock_capture.stop_capture = AsyncMock()
        mock_stt.transcribe = AsyncMock()
        mock_vad.process_chunk = AsyncMock()
        mock_vad.is_speaking = False
        mock_vad.current_duration = 0.0

        async def mock_stream():
            yield b"audio_chunk_1"
            yield b"audio_chunk_2"
            try:
                while True:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass

        mock_capture.get_audio_stream.return_value = mock_stream()

        yield {
            "stt": mock_stt,
            "vad": mock_vad,
            "capture": mock_capture,
            "recognizer": mock_recognizer,
            "factory": mock_factory,
        }


@pytest.mark.asyncio
async def test_audio_loop_integration(mock_components):
    """Test the audio processing loop integration."""
    server = SidecarServer()

    segment1 = SpeechSegment(audio=b"segment1", start_time=0.0, end_time=1.0, confidence=0.9)
    mock_components["vad"].process_chunk = AsyncMock(side_effect=[[segment1], []])

    mock_components["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="Hello there"))

    mock_socket = AsyncMock()
    start_msg = Message(MessageType.START_SESSION, {"apiKey": "test_key"})
    await server._handle_start_session(mock_socket, start_msg)

    assert server.stt is not None
    assert server.vad is not None
    assert server.audio_capture is not None

    assert server.session_state.status == SessionStatus.LISTENING

    await asyncio.sleep(0.1)

    stop_msg = Message(MessageType.STOP_SESSION)
    await server._handle_stop_session(mock_socket, stop_msg)

    assert server.stt is None
    assert server._audio_task is None

    assert mock_components["vad"].process_chunk.call_count >= 1
    mock_components["stt"].transcribe.assert_called_with(b"segment1")


@pytest.mark.asyncio
async def test_speaker_labeling(mock_components):
    """Test speaker labeling logic."""
    server = SidecarServer()

    server.session_state.voice_calibrated = True
    server.session_state.user_embedding = np.zeros(192)

    segment = SpeechSegment(b"audio1", 0.0, 1.0, 0.9)
    mock_components["vad"].process_chunk = AsyncMock(return_value=[segment])

    mock_components["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="Test"))

    mock_components["recognizer"].verify_speaker.return_value = True

    mock_client = AsyncMock()
    server.clients.add(mock_client)

    mock_socket = AsyncMock()
    await server._handle_start_session(mock_socket, Message(MessageType.START_SESSION, {"apiKey": "test_key"}))

    await asyncio.sleep(0.1)

    await server._handle_stop_session(mock_socket, Message(MessageType.STOP_SESSION))

    mock_components["recognizer"].verify_speaker.assert_called()

    sent_jsons = [call.args[0] for call in mock_client.send.call_args_list]
    assert any("TRANSCRIPTION" in json_str and "User" in json_str for json_str in sent_jsons)
