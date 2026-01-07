import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the class to be tested (will fail if file doesn't exist yet, but that's TDD)
# We will create the file in the next step.
# For now, we mock the import of 'anthropic' to avoid ModuleNotFoundError during test collection
# if the package isn't installed yet.
import sys
from typing import AsyncGenerator

# Mock anthropic module if not installed
if "anthropic" not in sys.modules:
    sys.modules["anthropic"] = MagicMock()

# Now we can safely import the provider (once created)
# Since the file doesn't exist yet, we can't import it at top level for this step.
# But I will write the test assuming the file exists.

@pytest.mark.asyncio
async def test_anthropic_initialization():
    """Test that the provider initializes correctly."""
    with patch("sidecar.src.providers.llm.anthropic.AsyncAnthropic") as MockClient:
        from sidecar.src.providers.llm.anthropic import AnthropicLLMProvider
        
        provider = AnthropicLLMProvider(api_key="test-key")
        
        MockClient.assert_called_once_with(api_key="test-key")
        assert provider.model == "claude-3-5-sonnet-20240620"
        assert provider.is_available() is True

@pytest.mark.asyncio
async def test_generate_response_streaming():
    """Test that generate_response streams chunks correctly."""
    with patch("sidecar.src.providers.llm.anthropic.AsyncAnthropic") as MockClient:
        from sidecar.src.providers.llm.anthropic import AnthropicLLMProvider
        
        # Setup mock stream
        mock_client_instance = MockClient.return_value
        
        # Create a mock stream that yields events
        # In Anthropic SDK, stream context manager yields the stream
        # which we iterate over.
        
        # Mocking: async with client.messages.stream(...) as stream:
        #              async for text in stream.text_stream:
        #                  yield text
        
        # So we need to mock client.messages.stream to return an async context manager
        # The context manager returns an object that has a text_stream property which is an async iterator
        
        async def async_text_stream():
            yield "Hello"
            yield " world"
            yield "!"

        mock_stream = MagicMock()
        mock_stream.text_stream = async_text_stream()
        
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__.return_value = mock_stream
        mock_context_manager.__aexit__ = AsyncMock()
        
        mock_client_instance.messages.stream.return_value = mock_context_manager
        
        provider = AnthropicLLMProvider(api_key="test-key")
        
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
        
        chunks = []
        async for chunk in provider.generate_response(
            prompt="Current question",
            context="Some context",
            history=history
        ):
            chunks.append(chunk)
            
        assert chunks == ["Hello", " world", "!"]
        
        # Verify call arguments
        mock_client_instance.messages.stream.assert_called_once()
        call_kwargs = mock_client_instance.messages.stream.call_args.kwargs
        
        assert call_kwargs["model"] == "claude-3-5-sonnet-20240620"
        assert call_kwargs["max_tokens"] == 1024
        
        # Check system prompt
        assert call_kwargs["system"] == "Use the following context to answer the user's question:\n\nSome context"
        
        # Check messages
        expected_messages = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
            {"role": "user", "content": "Current question"}
        ]
        assert call_kwargs["messages"] == expected_messages

@pytest.mark.asyncio
async def test_generate_response_empty_history():
    """Test generate_response with empty history."""
    with patch("sidecar.src.providers.llm.anthropic.AsyncAnthropic") as MockClient:
        from sidecar.src.providers.llm.anthropic import AnthropicLLMProvider
        
        mock_client_instance = MockClient.return_value
        
        async def async_text_stream():
            yield "Response"

        mock_stream = MagicMock()
        mock_stream.text_stream = async_text_stream()
        
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__.return_value = mock_stream
        mock_context_manager.__aexit__ = AsyncMock()
        
        mock_client_instance.messages.stream.return_value = mock_context_manager
        
        provider = AnthropicLLMProvider(api_key="test-key")
        
        async for _ in provider.generate_response("Question", "Context", []):
            pass
            
        call_kwargs = mock_client_instance.messages.stream.call_args.kwargs
        
        expected_messages = [
            {"role": "user", "content": "Question"}
        ]
        assert call_kwargs["messages"] == expected_messages

@pytest.mark.asyncio
async def test_generate_response_error_handling():
    """Test error handling during generation."""
    with patch("sidecar.src.providers.llm.anthropic.AsyncAnthropic") as MockClient:
        from sidecar.src.providers.llm.anthropic import AnthropicLLMProvider
        
        mock_client_instance = MockClient.return_value
        mock_client_instance.messages.stream.side_effect = Exception("API Error")
        
        provider = AnthropicLLMProvider(api_key="test-key")
        
        with pytest.raises(Exception, match="API Error"):
            async for _ in provider.generate_response("Q", "C", []):
                pass
