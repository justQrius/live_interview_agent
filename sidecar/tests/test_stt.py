import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add sidecar/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from stt.gemini_stt import GeminiSTT, GeminiSTTError

@pytest.fixture
def mock_genai():
    with patch("stt.gemini_stt.genai") as mock:
        yield mock

@pytest.mark.asyncio
async def test_init(mock_genai):
    """Test initialization."""
    stt = GeminiSTT(api_key="test_key")
    
    mock_genai.configure.assert_called_once_with(api_key="test_key")
    mock_genai.GenerativeModel.assert_called_once_with("gemini-1.5-flash")
    assert stt.api_key == "test_key"

@pytest.mark.asyncio
async def test_transcribe_success(mock_genai):
    """Test successful transcription."""
    stt = GeminiSTT(api_key="test_key")
    
    # Mock model response
    mock_response = MagicMock()
    mock_response.text = "Hello world"
    stt.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    audio_bytes = b"\x00" * 32000  # 1 sec of silence (approx)
    
    text = await stt.transcribe(audio_bytes)
    
    assert text == "Hello world"
    stt.model.generate_content_async.assert_called_once()
    
    # Verify call arguments
    call_args = stt.model.generate_content_async.call_args
    assert call_args is not None
    args, kwargs = call_args
    assert len(args) == 1
    content = args[0]
    assert isinstance(content, list)
    assert len(content) == 2
    assert isinstance(content[0], str) # prompt
    assert isinstance(content[1], dict) # audio data
    assert content[1]["mime_type"] == "audio/wav"

@pytest.mark.asyncio
async def test_transcribe_empty(mock_genai):
    """Test transcribing empty audio."""
    stt = GeminiSTT(api_key="test_key")
    text = await stt.transcribe(b"")
    assert text == ""
    stt.model.generate_content_async.assert_not_called()

@pytest.mark.asyncio
async def test_transcribe_error(mock_genai):
    """Test transcription error."""
    stt = GeminiSTT(api_key="test_key")
    
    stt.model.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
    
    with pytest.raises(GeminiSTTError):
        await stt.transcribe(b"\x00" * 100)
