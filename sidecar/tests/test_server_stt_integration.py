import sys
import os
import asyncio
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock speechbrain before importing anything that uses it
sys.modules["speechbrain"] = MagicMock()
sys.modules["speechbrain.inference"] = MagicMock()
sys.modules["speechbrain.inference.speaker"] = MagicMock()

# Add sidecar/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from server import SidecarServer, SessionStatus, Speaker
from protocol import Message, MessageType
from audio.vad import SpeechSegment
from providers.base import TranscriptionResult

@pytest.fixture
def mock_components():
    with patch("server.GeminiSTTProvider") as mock_stt_cls, \
         patch("server.VADProcessor") as mock_vad_cls, \
         patch("server.AudioCapture") as mock_capture_cls, \
         patch("server.SpeakerRecognizer") as mock_recognizer_cls, \
         patch("server.ModelWarmer") as mock_warmer_cls, \
         patch("server.NoiseReducer") as mock_noise_reducer_cls:

        # Setup mocks
        mock_stt = mock_stt_cls.return_value
        mock_vad = mock_vad_cls.return_value
        mock_capture = mock_capture_cls.return_value
        mock_recognizer = mock_recognizer_cls.return_value

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
        
        # Mock audio stream
        async def mock_stream():
            yield b"audio_chunk_1"
            yield b"audio_chunk_2"
            # Keep running until cancelled to simulate infinite stream
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
            "recognizer": mock_recognizer
        }

@pytest.mark.asyncio
async def test_audio_loop_integration(mock_components):
    """Test the audio processing loop integration."""
    server = SidecarServer()
    
    # Configure VAD to return segments
    segment1 = SpeechSegment(
        audio=b"segment1", # 8 bytes - valid
        start_time=0.0,
        end_time=1.0,
        confidence=0.9
    )
    mock_components["vad"].process_chunk = AsyncMock(side_effect=[
        [segment1], # First chunk returns one segment
        []          # Second chunk returns nothing
    ])
    
    # Configure STT to return TranscriptionResult
    mock_components["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="Hello there"))
    
    # Start session (which starts audio loop)
    mock_socket = AsyncMock()
    start_msg = Message(MessageType.START_SESSION, {"apiKey": "test_key"})
    await server._handle_start_session(mock_socket, start_msg)
    
    # Verify components initialized
    assert server.stt is not None
    assert server.vad is not None
    assert server.audio_capture is not None
    
    # Verify processing started
    assert server.session_state.status == SessionStatus.LISTENING
    
    # Let the loop run for a bit
    await asyncio.sleep(0.1)
    
    # Stop session
    stop_msg = Message(MessageType.STOP_SESSION)
    await server._handle_stop_session(mock_socket, stop_msg)
    
    # Verify processing stopped
    assert server.stt is None
    assert server._audio_task is None
    
    # Verify interactions
    # VAD processed chunks
    assert mock_components["vad"].process_chunk.call_count >= 1
    
    # STT transcribed segment
    mock_components["stt"].transcribe.assert_called_with(b"segment1")
    
    # Should have broadcasted transcription (need to mock broadcast or check client send)
    # Since we didn't add client to server.clients in this test, broadcast does nothing.
    # But we can check if logic flowed correctly.

@pytest.mark.asyncio
async def test_speaker_labeling(mock_components):
    """Test speaker labeling logic."""
    server = SidecarServer()
    
    # Setup calibrated user
    server.session_state.voice_calibrated = True
    server.session_state.user_embedding = np.zeros(192)
    
    # Configure VAD
    segment = SpeechSegment(b"audio1", 0.0, 1.0, 0.9) # 6 bytes - valid (even length)
    mock_components["vad"].process_chunk = AsyncMock(return_value=[segment])
    
    # Configure STT
    mock_components["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="Test"))
    
    # Configure Speaker Recognizer - Match User
    mock_components["recognizer"].verify_speaker.return_value = True
    
    # Manually trigger one iteration of loop logic (hard to do without private method access or running loop)
    # Instead, we'll verify verify_speaker is called if we run the loop
    
    await server._start_audio_processing("api_key")
    
    # Add a mock client to capture broadcast
    mock_client = AsyncMock()
    server.clients.add(mock_client)
    
    # Let loop run
    await asyncio.sleep(0.1)
    
    await server._stop_audio_processing()
    
    # Verify verify_speaker was called
    mock_components["recognizer"].verify_speaker.assert_called()
    
    # Verify transcription message has Speaker.USER
    # Capture calls to mock_client.send
    sent_jsons = [call.args[0] for call in mock_client.send.call_args_list]
    found_user_msg = False
    for json_str in sent_jsons:
        if "TRANSCRIPTION" in json_str and "User" in json_str:
            found_user_msg = True
            break
            
    assert found_user_msg
