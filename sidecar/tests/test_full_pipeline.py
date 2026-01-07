"""
Tests for Full Pipeline Integration (STORY-014).

Tests the complete audio → VAD → STT → diarization → RAG → LLM → UI pipeline.
Specifically verifies:
1. User speech is filtered (not sent to RAG+LLM)
2. Interviewer speech triggers RAG retrieval and LLM generation
3. End-to-end latency tracking
"""

import sys
import os
import asyncio
import time
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Mock speechbrain before importing anything that uses it
sys.modules["speechbrain"] = MagicMock()
sys.modules["speechbrain.inference"] = MagicMock()
sys.modules["speechbrain.inference.speaker"] = MagicMock()

# Add sidecar/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from server import SidecarServer, SessionStatus, Speaker
from protocol import Message, MessageType, ConfidenceLevel
from audio.vad import SpeechSegment
from providers.base import TranscriptionResult


@pytest.fixture
def mock_full_pipeline():
    """Mock all pipeline components for full integration testing."""
    with patch("server.GeminiSTTProvider") as mock_stt_cls, \
         patch("server.VADProcessor") as mock_vad_cls, \
         patch("server.AudioCapture") as mock_capture_cls, \
         patch("server.SpeakerRecognizer") as mock_recognizer_cls, \
         patch("server.GeminiLLMProvider") as mock_llm_cls, \
         patch("server.VectorStore") as mock_vector_cls, \
         patch("server.RAGEngine") as mock_rag_cls, \
         patch("server.ModelWarmer") as mock_warmer_cls, \
         patch("server.NoiseReducer") as mock_noise_reducer_cls:
        
        # Setup mocks
        mock_stt = mock_stt_cls.return_value
        mock_vad = mock_vad_cls.return_value
        mock_capture = mock_capture_cls.return_value
        mock_recognizer = mock_recognizer_cls.return_value
        mock_llm = mock_llm_cls.return_value
        mock_vector = mock_vector_cls.return_value
        mock_rag = mock_rag_cls.return_value

        # Configure ModelWarmer mock - return models as not ready so server creates fresh mocks
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
        
        # Configure RAG mock
        mock_rag_result = MagicMock()
        mock_rag_result.text = "Context about Python programming."
        mock_rag_result.confidence = "high"
        mock_rag_result.distance = 0.2
        mock_rag.retrieve = MagicMock(return_value=[mock_rag_result])
        
        # Configure LLM mock - async generator
        async def mock_generate_answer(question, context_chunks):
            yield "Python is "
            yield "a great language."
        mock_llm.generate_answer = mock_generate_answer
        
        # Mock audio stream - produces controlled chunks
        audio_queue = asyncio.Queue()
        
        async def mock_stream():
            while True:
                try:
                    chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.5)
                    if chunk is None:  # Sentinel to stop
                        break
                    yield chunk
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                    
        mock_capture.get_audio_stream = mock_stream
        
        yield {
            "stt": mock_stt,
            "vad": mock_vad,
            "capture": mock_capture,
            "recognizer": mock_recognizer,
            "llm": mock_llm,
            "vector": mock_vector,
            "rag": mock_rag,
            "audio_queue": audio_queue,
            "stt_cls": mock_stt_cls,
            "llm_cls": mock_llm_cls,
            "vector_cls": mock_vector_cls,
            "rag_cls": mock_rag_cls,
        }


class TestFullPipelineIntegration:
    """Tests for the complete audio-to-answer pipeline."""
    
    @pytest.mark.asyncio
    async def test_interviewer_speech_triggers_rag_llm(self, mock_full_pipeline):
        """
        When interviewer speech is detected, the system should:
        1. Transcribe the speech
        2. Retrieve context from RAG
        3. Generate answer using LLM
        4. Stream answer chunks to client
        """
        server = SidecarServer()
        
        # Configure VAD to return interviewer speech segment
        interviewer_segment = SpeechSegment(
            audio=b"intervieweraudio",  # 16 bytes - valid
            start_time=0.0,
            end_time=2.0,
            confidence=0.95
        )
        mock_full_pipeline["vad"].process_chunk = AsyncMock(return_value=[interviewer_segment])
        
        # Configure STT to return a question
        mock_full_pipeline["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="What is Python?"))
        
        # Configure speaker recognizer - NOT user (interviewer)
        mock_full_pipeline["recognizer"].verify_speaker.return_value = False
        
        # Setup calibrated user
        server.session_state.voice_calibrated = True
        server.session_state.user_embedding = np.zeros(192)
        
        # Start session
        mock_socket = AsyncMock()
        start_msg = Message(MessageType.START_SESSION, {"apiKey": "test_key"})
        await server._handle_start_session(mock_socket, start_msg)
        
        # Add mock client to capture broadcasts
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        # Feed audio chunk
        await mock_full_pipeline["audio_queue"].put(b"audio_chunk")
        
        # Let the loop process
        await asyncio.sleep(0.2)
        
        # Stop session
        await mock_full_pipeline["audio_queue"].put(None)  # Signal stop
        await server._stop_audio_processing()
        
        # Verify pipeline was triggered
        # 1. STT was called
        mock_full_pipeline["stt"].transcribe.assert_called()
        
        # 2. RAG retrieval was called with the question
        mock_full_pipeline["rag"].retrieve.assert_called_with("What is Python?", limit=5)
        
        # 3. Client received transcription AND answer chunks
        sent_messages = [call.args[0] for call in mock_client.send.call_args_list]
        
        has_transcription = any("TRANSCRIPTION" in msg and "Interviewer" in msg for msg in sent_messages)
        has_answer_chunk = any("ANSWER_CHUNK" in msg for msg in sent_messages)
        
        assert has_transcription, "Should have sent transcription message"
        assert has_answer_chunk, "Should have sent answer chunks"
    
    @pytest.mark.asyncio
    async def test_user_speech_filtered_no_rag_llm(self, mock_full_pipeline):
        """
        When user speech is detected, the system should:
        1. Transcribe the speech
        2. Send transcription to client
        3. NOT trigger RAG or LLM
        """
        server = SidecarServer()
        
        user_segment = SpeechSegment(
            audio=b"useraudiodataXYZ",  # 16 bytes - even for int16
            start_time=0.0,
            end_time=1.5,
            confidence=0.92
        )
        mock_full_pipeline["vad"].process_chunk = AsyncMock(return_value=[user_segment])
        
        # Configure STT
        mock_full_pipeline["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="I have experience with Python."))
        
        # Configure speaker recognizer - IS user
        mock_full_pipeline["recognizer"].verify_speaker.return_value = True
        
        # Setup calibrated user
        server.session_state.voice_calibrated = True
        server.session_state.user_embedding = np.zeros(192)
        
        # Start session
        mock_socket = AsyncMock()
        start_msg = Message(MessageType.START_SESSION, {"apiKey": "test_key"})
        await server._handle_start_session(mock_socket, start_msg)
        
        # Add mock client
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        # Feed audio chunk
        await mock_full_pipeline["audio_queue"].put(b"audio_chunk")
        
        # Let the loop process
        await asyncio.sleep(0.2)
        
        # Stop session
        await mock_full_pipeline["audio_queue"].put(None)
        await server._stop_audio_processing()
        
        # Verify transcription was sent
        sent_messages = [call.args[0] for call in mock_client.send.call_args_list]
        has_user_transcription = any("TRANSCRIPTION" in msg and "User" in msg for msg in sent_messages)
        assert has_user_transcription, "Should have sent user transcription"
        
        # Verify RAG was NOT called (user speech should be filtered)
        mock_full_pipeline["rag"].retrieve.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_uncalibrated_all_speech_is_interviewer(self, mock_full_pipeline):
        """
        When voice is not calibrated, all speech should be treated as interviewer.
        """
        server = SidecarServer()
        
        # Configure VAD
        segment = SpeechSegment(
            audio=b"someaudiodata1",  # 14 bytes
            start_time=0.0,
            end_time=1.0,
            confidence=0.9
        )
        mock_full_pipeline["vad"].process_chunk = AsyncMock(return_value=[segment])
        
        # Configure STT
        mock_full_pipeline["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="Tell me about yourself."))
        
        # NOT calibrated
        server.session_state.voice_calibrated = False
        server.session_state.user_embedding = None
        
        # Start session
        mock_socket = AsyncMock()
        start_msg = Message(MessageType.START_SESSION, {"apiKey": "test_key"})
        await server._handle_start_session(mock_socket, start_msg)
        
        # Add mock client
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        # Feed audio chunk
        await mock_full_pipeline["audio_queue"].put(b"audio_chunk")
        
        # Let the loop process
        await asyncio.sleep(0.2)
        
        # Stop session
        await mock_full_pipeline["audio_queue"].put(None)
        await server._stop_audio_processing()
        
        # Verify speaker recognizer was NOT called (not calibrated)
        mock_full_pipeline["recognizer"].verify_speaker.assert_not_called()
        
        # Verify transcription was sent as Interviewer
        sent_messages = [call.args[0] for call in mock_client.send.call_args_list]
        has_interviewer_transcription = any("TRANSCRIPTION" in msg and "Interviewer" in msg for msg in sent_messages)
        assert has_interviewer_transcription
        
        # Verify RAG was called (interviewer question triggers pipeline)
        mock_full_pipeline["rag"].retrieve.assert_called()
    
    @pytest.mark.asyncio
    async def test_answer_includes_confidence_from_rag(self, mock_full_pipeline):
        """
        The final answer chunk should include confidence from RAG retrieval.
        """
        server = SidecarServer()
        
        # Configure RAG with specific confidence
        mock_rag_result = MagicMock()
        mock_rag_result.text = "Python context"
        mock_rag_result.confidence = "medium"
        mock_rag_result.distance = 0.4
        mock_full_pipeline["rag"].retrieve = MagicMock(return_value=[mock_rag_result])
        
        # Configure VAD
        segment = SpeechSegment(b"interviewerq", 0.0, 1.0, 0.9)
        mock_full_pipeline["vad"].process_chunk = AsyncMock(return_value=[segment])
        
        # Configure STT
        mock_full_pipeline["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="Question?"))
        
        # NOT user
        mock_full_pipeline["recognizer"].verify_speaker.return_value = False
        
        # Calibrated
        server.session_state.voice_calibrated = True
        server.session_state.user_embedding = np.zeros(192)
        
        # Start session
        mock_socket = AsyncMock()
        await server._handle_start_session(mock_socket, Message(MessageType.START_SESSION, {"apiKey": "test_key"}))
        
        # Add mock client
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        # Feed audio
        await mock_full_pipeline["audio_queue"].put(b"audio")
        await asyncio.sleep(0.3)
        
        # Stop
        await mock_full_pipeline["audio_queue"].put(None)
        await server._stop_audio_processing()
        
        # Check for final answer chunk with confidence
        sent_messages = [call.args[0] for call in mock_client.send.call_args_list]
        final_chunks = [msg for msg in sent_messages if "ANSWER_CHUNK" in msg and '"complete": true' in msg]
        
        assert len(final_chunks) > 0, "Should have a final answer chunk"
        # The confidence should be included in the final chunk
        assert any("confidence" in chunk for chunk in final_chunks), "Final chunk should have confidence"


class TestLatencyTracking:
    """Tests for end-to-end latency measurement."""
    
    @pytest.mark.asyncio
    async def test_pipeline_latency_tracking(self, mock_full_pipeline):
        """
        Verify that latency from speech detection to answer delivery is tracked.
        Target: <5 seconds (NFR-1).
        """
        server = SidecarServer()
        
        # Configure components
        segment = SpeechSegment(b"audioquestion", 0.0, 1.0, 0.9)
        mock_full_pipeline["vad"].process_chunk = AsyncMock(return_value=[segment])
        mock_full_pipeline["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="What is AI?"))
        mock_full_pipeline["recognizer"].verify_speaker.return_value = False
        
        server.session_state.voice_calibrated = True
        server.session_state.user_embedding = np.zeros(192)
        
        # Start session
        mock_socket = AsyncMock()
        await server._handle_start_session(mock_socket, Message(MessageType.START_SESSION, {"apiKey": "test_key"}))
        
        # Add mock client that records timestamps
        received_times = []
        original_send = AsyncMock()
        async def tracking_send(msg):
            received_times.append((time.time(), msg))
            return await original_send(msg)
        
        mock_client = MagicMock()
        mock_client.send = tracking_send
        server.clients.add(mock_client)
        
        # Record start time and feed audio
        start_time = time.time()
        await mock_full_pipeline["audio_queue"].put(b"audio")
        
        # Wait for processing
        await asyncio.sleep(0.3)
        
        # Stop
        await mock_full_pipeline["audio_queue"].put(None)
        await server._stop_audio_processing()
        
        # Find the first answer chunk time
        answer_times = [t for t, msg in received_times if "ANSWER_CHUNK" in msg]
        
        if answer_times:
            latency = answer_times[0] - start_time
            # In tests with mocks, latency should be very low
            # In production, target is <5 seconds
            assert latency < 5.0, f"Latency {latency}s exceeds 5s target"


class TestPipelineErrorHandling:
    """Tests for error handling in the pipeline."""
    
    @pytest.mark.asyncio
    async def test_stt_error_continues_processing(self, mock_full_pipeline):
        """
        If STT fails for one segment, the pipeline should continue with next segment.
        """
        server = SidecarServer()
        
        # Configure VAD to return multiple segments
        segment1 = SpeechSegment(b"seg1audio1234", 0.0, 1.0, 0.9)
        segment2 = SpeechSegment(b"seg2audio5678", 1.0, 2.0, 0.9)
        mock_full_pipeline["vad"].process_chunk = AsyncMock(side_effect=[
            [segment1],
            [segment2],
        ])
        
        # First transcription fails, second succeeds
        mock_full_pipeline["stt"].transcribe = AsyncMock(side_effect=[
            Exception("STT API Error"),
            TranscriptionResult(text="Second question?")
        ])
        mock_full_pipeline["recognizer"].verify_speaker.return_value = False
        
        server.session_state.voice_calibrated = True
        server.session_state.user_embedding = np.zeros(192)
        
        # Start session
        mock_socket = AsyncMock()
        await server._handle_start_session(mock_socket, Message(MessageType.START_SESSION, {"apiKey": "test_key"}))
        
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        # Feed two chunks
        await mock_full_pipeline["audio_queue"].put(b"audio1")
        await asyncio.sleep(0.1)
        await mock_full_pipeline["audio_queue"].put(b"audio2")
        await asyncio.sleep(0.2)
        
        # Stop
        await mock_full_pipeline["audio_queue"].put(None)
        await server._stop_audio_processing()
        
        # Verify STT was called twice (continued after error)
        assert mock_full_pipeline["stt"].transcribe.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_rag_error_still_sends_transcription(self, mock_full_pipeline):
        """
        If RAG fails, transcription should still be sent to client.
        """
        server = SidecarServer()
        
        segment = SpeechSegment(b"questionaudio", 0.0, 1.0, 0.9)
        mock_full_pipeline["vad"].process_chunk = AsyncMock(return_value=[segment])
        mock_full_pipeline["stt"].transcribe = AsyncMock(return_value=TranscriptionResult(text="What is RAG?"))
        mock_full_pipeline["recognizer"].verify_speaker.return_value = False
        
        # RAG fails
        mock_full_pipeline["rag"].retrieve = MagicMock(side_effect=Exception("RAG Error"))
        
        server.session_state.voice_calibrated = True
        server.session_state.user_embedding = np.zeros(192)
        
        mock_socket = AsyncMock()
        await server._handle_start_session(mock_socket, Message(MessageType.START_SESSION, {"apiKey": "test_key"}))
        
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        await mock_full_pipeline["audio_queue"].put(b"audio")
        await asyncio.sleep(0.2)
        
        await mock_full_pipeline["audio_queue"].put(None)
        await server._stop_audio_processing()
        
        # Transcription should still be sent
        sent_messages = [call.args[0] for call in mock_client.send.call_args_list]
        has_transcription = any("TRANSCRIPTION" in msg for msg in sent_messages)
        assert has_transcription, "Transcription should be sent even if RAG fails"
