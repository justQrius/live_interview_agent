import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm.gemini_llm import GeminiLLM, GeminiLLMError

@pytest.fixture
def mock_genai():
    with patch("llm.gemini_llm.genai") as mock:
        yield mock

class TestGeminiLLM:
    def test_init(self, mock_genai):
        """Test initialization of GeminiLLM."""
        api_key = "test_key"
        llm = GeminiLLM(api_key)
        
        mock_genai.configure.assert_called_once_with(api_key=api_key)
        assert llm.model is not None
        
    def test_init_missing_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(ValueError):
            GeminiLLM("")

    @pytest.mark.asyncio
    async def test_generate_answer(self, mock_genai):
        """Test generating an answer."""
        llm = GeminiLLM("test_key")
        
        # Mock the response stream
        mock_response = MagicMock()
        mock_response.text = "Test answer"
        
        # Configure the mock model to return a chunk
        mock_chunk = MagicMock()
        mock_chunk.text = "Test answer"
        
        # Setup generate_content_async to return an async generator or similar if needed,
        # but for streaming=True it usually returns a response object that is iterable
        # However, google.generativeai.GenerativeModel.generate_content_stream is the method for streaming
        
        # Let's mock generate_content_async with stream=True
        mock_model = mock_genai.GenerativeModel.return_value
        
        # Create an async iterator for the response
        async def async_response_gen():
            yield mock_chunk
            
        # Fix: Ensure generate_content_async is an AsyncMock that returns the generator
        mock_model.generate_content_async = AsyncMock(return_value=async_response_gen())

        question = "What is X?"
        context = ["Context 1", "Context 2"]
        
        chunks = []
        async for chunk in llm.generate_answer(question, context):
            chunks.append(chunk)
            
        assert "".join(chunks) == "Test answer"
        
        # Verify call arguments
        args, kwargs = mock_model.generate_content_async.call_args
        assert kwargs['stream'] is True
        prompt = args[0]
        assert "Context 1" in prompt
        assert "Context 2" in prompt
        assert "What is X?" in prompt

    @pytest.mark.asyncio
    async def test_generate_answer_empty_context(self, mock_genai):
        """Test generating an answer with empty context."""
        llm = GeminiLLM("test_key")
        
        mock_model = mock_genai.GenerativeModel.return_value
        
        mock_chunk = MagicMock()
        mock_chunk.text = "General answer"
        
        async def async_response_gen():
            yield mock_chunk
            
        mock_model.generate_content_async = AsyncMock(return_value=async_response_gen())

        question = "What is X?"
        context = []
        
        chunks = []
        async for chunk in llm.generate_answer(question, context):
            chunks.append(chunk)
            
        assert "".join(chunks) == "General answer"
        
        # Verify call arguments
        args, kwargs = mock_model.generate_content_async.call_args
        prompt = args[0]
        assert "Context:" in prompt
        assert "Question:" in prompt

    @pytest.mark.asyncio
    async def test_api_error(self, mock_genai):
        """Test handling of API errors."""
        llm = GeminiLLM("test_key")
        mock_model = mock_genai.GenerativeModel.return_value
        mock_model.generate_content_async.side_effect = Exception("API Error")
        
        with pytest.raises(GeminiLLMError):
            async for _ in llm.generate_answer("Q", ["C"]):
                pass
