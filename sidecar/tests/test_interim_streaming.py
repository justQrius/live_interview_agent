"""
Tests for Interim Transcript Streaming (STORY-065).

Tests that:
1. Speculative cycle broadcasts interim messages
2. Messages contain correct fields (text, timestamp, isFinal=False)
"""

import pytest
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch
from src.server import SidecarServer
from src.protocol import MessageType, Speaker
from src.providers.base import TranscriptionResult

@pytest.fixture
def mock_server():
    server = SidecarServer()
    server.stt = AsyncMock()
    server.vad = MagicMock()
    server.speculative_retriever = AsyncMock()
    server.broadcast = AsyncMock()
    return server

@pytest.mark.asyncio
async def test_speculative_cycle_broadcasts_interim(mock_server):
    """Test that _run_speculative_cycle broadcasts INTERIM_TRANSCRIPTION."""
    
    # Setup mocks
    mock_server.vad.get_current_audio.return_value = b'\x00' * 32000  # 1s of audio
    mock_server.vad.current_duration = 1.0
    
    mock_server.stt.transcribe.return_value = TranscriptionResult(
        text="Hello world interim",
        confidence=0.9
    )
    
    # Run method
    await mock_server._run_speculative_cycle()
    
    # Verify broadcast called
    assert mock_server.broadcast.called
    args = mock_server.broadcast.call_args[0][0]
    
    # Check message content
    assert args.type == MessageType.INTERIM_TRANSCRIPTION
    data = args.data
    assert data["text"] == "Hello world interim"
    assert data["speaker"] == Speaker.INTERVIEWER.value
    assert data["isFinal"] is False
    assert "timestamp" in data

@pytest.mark.asyncio
async def test_speculative_cycle_skips_empty_audio(mock_server):
    """Test that cycle skips if audio buffer is None or too short."""
    
    # Case 1: None
    mock_server.vad.get_current_audio.return_value = None
    await mock_server._run_speculative_cycle()
    mock_server.stt.transcribe.assert_not_called()
    mock_server.broadcast.assert_not_called()
    
    # Case 2: Too short
    mock_server.vad.get_current_audio.return_value = b'\x00' * 100
    await mock_server._run_speculative_cycle()
    mock_server.stt.transcribe.assert_not_called()

@pytest.mark.asyncio
async def test_speculative_cycle_skips_empty_transcript(mock_server):
    """Test that cycle skips broadcast if transcript is empty."""
    
    mock_server.vad.get_current_audio.return_value = b'\x00' * 32000
    mock_server.stt.transcribe.return_value = TranscriptionResult(text="")
    
    await mock_server._run_speculative_cycle()
    
    mock_server.broadcast.assert_not_called()
    mock_server.speculative_retriever.on_interim_transcript.assert_not_called()
