import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.llm.anthropic import AnthropicLLMProvider


@pytest.mark.asyncio
async def test_anthropic_initialization():
    with patch("providers.llm.anthropic.AsyncAnthropic") as MockClient:
        provider = AnthropicLLMProvider(api_key="test-key")

        MockClient.assert_called_once_with(api_key="test-key")
        assert provider.model == "claude-3-5-sonnet-20240620"
        assert provider.is_available() is True


@pytest.mark.asyncio
async def test_generate_response_streaming():
    with (
        patch("providers.llm.anthropic.AsyncAnthropic") as MockClient,
        patch("providers.llm.anthropic.build_system_prompt") as mock_build_system_prompt,
        patch("providers.llm.anthropic.format_context_for_prompt") as mock_format_context,
    ):
        mock_build_system_prompt.return_value = ("SYS", "general")
        mock_format_context.return_value = "CTX"

        mock_client_instance = MockClient.return_value

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
            {"role": "assistant", "content": "Previous answer"},
        ]

        chunks = []
        async for chunk in provider.generate_response(
            prompt="Current question",
            context="Some context",
            history=history,
        ):
            chunks.append(chunk)

        assert chunks == ["Hello", " world", "!"]

        mock_client_instance.messages.stream.assert_called_once()
        call_kwargs = mock_client_instance.messages.stream.call_args.kwargs

        assert call_kwargs["model"] == "claude-3-5-sonnet-20240620"
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["system"] == "SYS"

        expected_messages = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
            {"role": "user", "content": "CTX\n\nQuestion:\nCurrent question"},
        ]
        assert call_kwargs["messages"] == expected_messages


@pytest.mark.asyncio
async def test_generate_response_empty_history():
    with (
        patch("providers.llm.anthropic.AsyncAnthropic") as MockClient,
        patch("providers.llm.anthropic.build_system_prompt") as mock_build_system_prompt,
        patch("providers.llm.anthropic.format_context_for_prompt") as mock_format_context,
    ):
        mock_build_system_prompt.return_value = ("SYS", "general")
        mock_format_context.return_value = "CTX"

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

        expected_messages = [{"role": "user", "content": "CTX\n\nQuestion:\nQuestion"}]
        assert call_kwargs["messages"] == expected_messages


@pytest.mark.asyncio
async def test_generate_response_error_handling():
    with patch("providers.llm.anthropic.AsyncAnthropic") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.messages.stream.side_effect = Exception("API Error")

        provider = AnthropicLLMProvider(api_key="test-key")

        with pytest.raises(Exception, match="API Error"):
            async for _ in provider.generate_response("Q", "C", []):
                pass
