import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add sidecar/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.llm.openai import OpenAILLMProvider
from providers.base import LLMProvider

class TestOpenAILLMProvider:
    @pytest.fixture
    def mock_openai_class(self):
        with patch("sidecar.src.providers.llm.openai.AsyncOpenAI") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield mock

    def test_init_success(self, mock_openai_class):
        """Test successful initialization with API key."""
        provider = OpenAILLMProvider("test-api-key")
        assert isinstance(provider, LLMProvider)
        assert provider.is_available() is True
        mock_openai_class.assert_called_once()

    def test_init_raises_error_without_api_key(self):
        """Test error raised when initialized without API key."""
        with pytest.raises(ValueError):
            OpenAILLMProvider("")
        with pytest.raises(ValueError):
            OpenAILLMProvider(None)

    @pytest.mark.asyncio
    async def test_generate_response_success(self, mock_openai_class):
        """Test successful streaming response generation."""
        mock_client = mock_openai_class.return_value
        provider = OpenAILLMProvider("test-key")
        
        # Mock streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock(delta=MagicMock(content=" World"))]
        
        # Async iterator mock
        async def async_gen():
            yield mock_chunk1
            yield mock_chunk2
            
        mock_client.chat.completions.create.return_value = async_gen()
        
        prompt = "test prompt"
        context = "test context"
        history = [{"role": "user", "content": "prev"}]
        
        chunks = []
        async for chunk in provider.generate_response(prompt, context, history):
            chunks.append(chunk)
            
        assert chunks == ["Hello", " World"]
        
        # Verify call arguments
        call_args = mock_client.chat.completions.create.call_args
        assert call_args is not None
        kwargs = call_args.kwargs
        
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["stream"] is True
        assert len(kwargs["messages"]) > 0
        
        # Verify context injection
        messages = kwargs["messages"]
        system_msg = next(m for m in messages if m["role"] == "system")
        assert "helpful interview assistant" in system_msg["content"]
        
        user_msg = messages[-1]
        assert prompt in user_msg["content"]
        assert context in user_msg["content"]

    @pytest.mark.asyncio
    async def test_generate_response_error(self, mock_openai_class):
        """Test error handling during generation."""
        mock_client = mock_openai_class.return_value
        provider = OpenAILLMProvider("test-key")
        
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            async for _ in provider.generate_response("prompt", "context", []):
                pass
