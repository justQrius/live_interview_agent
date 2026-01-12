import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import LLMProvider
from providers.llm.openai import OpenAILLMProvider


class TestOpenAILLMProvider:
    @pytest.fixture
    def mock_openai_class(self):
        with patch("providers.llm.openai.AsyncOpenAI") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield mock

    def test_init_success(self, mock_openai_class):
        provider = OpenAILLMProvider("test-api-key")
        assert isinstance(provider, LLMProvider)
        assert provider.is_available() is True
        mock_openai_class.assert_called_once()

    def test_init_raises_error_without_api_key(self):
        with pytest.raises(ValueError):
            OpenAILLMProvider("")
        with pytest.raises(ValueError):
            OpenAILLMProvider(None)

    @pytest.mark.asyncio
    async def test_generate_response_success(self, mock_openai_class):
        with (
            patch("providers.llm.openai.build_system_prompt") as mock_build_system_prompt,
            patch("providers.llm.openai.format_context_for_prompt") as mock_format_context,
        ):
            mock_build_system_prompt.return_value = ("SYS", "general")
            mock_format_context.return_value = "CTX"

            mock_client = mock_openai_class.return_value
            provider = OpenAILLMProvider("test-key")

            mock_chunk1 = MagicMock()
            mock_chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]

            mock_chunk2 = MagicMock()
            mock_chunk2.choices = [MagicMock(delta=MagicMock(content=" World"))]

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

            call_args = mock_client.chat.completions.create.call_args
            kwargs = call_args.kwargs

            assert kwargs["model"] == "gpt-4o"
            assert kwargs["stream"] is True
            assert len(kwargs["messages"]) > 0

            system_msg = next(m for m in kwargs["messages"] if m["role"] == "system")
            assert system_msg["content"] == "SYS"

            user_msg = kwargs["messages"][-1]
            assert prompt in user_msg["content"]
            assert "CTX" in user_msg["content"]

    @pytest.mark.asyncio
    async def test_generate_response_error(self, mock_openai_class):
        mock_client = mock_openai_class.return_value
        provider = OpenAILLMProvider("test-key")

        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            async for _ in provider.generate_response("prompt", "context", []):
                pass
