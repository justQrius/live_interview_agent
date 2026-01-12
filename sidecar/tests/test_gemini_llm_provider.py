"""Tests for GeminiLLMProvider."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import LLMProvider
from providers.llm.gemini import GeminiLLMProvider, GeminiLLMProviderError


def _chunk(text: str | None) -> MagicMock:
    chunk = MagicMock()
    chunk.text = text
    return chunk


class TestGeminiLLMProviderInit:
    @patch("providers.llm.gemini.GeminiClient")
    def test_init_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key="test_key")

        mock_client_cls.assert_called_once_with(api_key="test_key")
        assert provider._api_key == "test_key"
        assert provider._available is True
        assert provider._client is mock_client

    def test_init_requires_api_key(self):
        with pytest.raises(ValueError, match="API key is required"):
            GeminiLLMProvider(api_key="")

    def test_init_none_api_key(self):
        with pytest.raises(ValueError, match="API key is required"):
            GeminiLLMProvider(api_key=None)

    @patch("providers.llm.gemini.GeminiClient")
    def test_implements_llm_provider(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        provider = GeminiLLMProvider(api_key="test_key")
        assert isinstance(provider, LLMProvider)

    @patch("providers.llm.gemini.GeminiClient")
    def test_custom_model_name(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        provider = GeminiLLMProvider(api_key="test_key", model_name="custom-model")
        assert provider._model_name == "custom-model"

    @patch("providers.llm.gemini.GeminiClient")
    def test_init_failure_raises_error(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("API Error")

        with pytest.raises(GeminiLLMProviderError, match="Failed to initialize"):
            GeminiLLMProvider(api_key="test_key")


class TestGeminiLLMProviderAvailability:
    @patch("providers.llm.gemini.GeminiClient")
    def test_is_available_true(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        provider = GeminiLLMProvider(api_key="test_key")
        assert provider.is_available() is True

    @patch("providers.llm.gemini.GeminiClient")
    def test_is_available_false_after_error(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("API Error")

        with pytest.raises(GeminiLLMProviderError):
            GeminiLLMProvider(api_key="test_key")


class TestGeminiLLMProviderGenerateResponse:
    @pytest.fixture
    def provider(self):
        with patch("providers.llm.gemini.GeminiClient") as mock_client_cls:
            client = MagicMock()
            mock_client_cls.return_value = client
            provider = GeminiLLMProvider(api_key="test_key")
            provider._client = client
            return provider

    @pytest.mark.asyncio
    async def test_generate_response_success(self, provider):
        provider._client.generate_content.return_value = [_chunk("Hello "), _chunk("world")]

        chunks: list[str] = []
        async for chunk in provider.generate_response(
            prompt="Tell me a story",
            context="Once upon a time",
            history=[],
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello world"
        provider._client.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_with_history(self, provider):
        provider._client.generate_content.return_value = [_chunk("Response")]

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        chunks: list[str] = []
        async for chunk in provider.generate_response(
            prompt="How are you?",
            context="Some context",
            history=history,
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        provider._client.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_empty_context(self, provider):
        provider._client.generate_content.return_value = [_chunk("I don't have context")]

        chunks: list[str] = []
        async for chunk in provider.generate_response(
            prompt="Question",
            context="",
            history=[],
        ):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_response_error(self, provider):
        provider._client.generate_content.side_effect = Exception("API Error")

        with pytest.raises(GeminiLLMProviderError, match="Generation failed"):
            async for _ in provider.generate_response(
                prompt="Question",
                context="Context",
                history=[],
            ):
                pass

    @pytest.mark.asyncio
    async def test_generate_response_empty_chunk(self, provider):
        provider._client.generate_content.return_value = [
            _chunk("Hello"),
            _chunk(None),
            _chunk(" world"),
        ]

        chunks: list[str] = []
        async for chunk in provider.generate_response(
            prompt="Question",
            context="Context",
            history=[],
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello world"


class TestGeminiLLMProviderGenerateAnswer:
    @pytest.fixture
    def provider(self):
        with patch("providers.llm.gemini.GeminiClient") as mock_client_cls:
            client = MagicMock()
            mock_client_cls.return_value = client
            provider = GeminiLLMProvider(api_key="test_key")
            provider._client = client
            return provider

    @pytest.mark.asyncio
    async def test_generate_answer_success(self, provider):
        provider._client.generate_content.return_value = [_chunk("The answer is "), _chunk("42")]

        chunks: list[str] = []
        async for chunk in provider.generate_answer(
            question="What is the meaning of life?",
            context_chunks=["Some context", "More context"],
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "The answer is 42"

    @pytest.mark.asyncio
    async def test_generate_answer_empty_context(self, provider):
        provider._client.generate_content.return_value = [_chunk("No context available")]

        chunks: list[str] = []
        async for chunk in provider.generate_answer(
            question="Question",
            context_chunks=[],
        ):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_answer_error(self, provider):
        provider._client.generate_content.side_effect = Exception("API Error")

        with pytest.raises(GeminiLLMProviderError, match="Generation failed"):
            async for _ in provider.generate_answer(
                question="Question",
                context_chunks=["Context"],
            ):
                pass


class TestGeminiLLMProviderPromptBuilding:
    @pytest.fixture
    def provider(self):
        with patch("providers.llm.gemini.GeminiClient") as mock_client_cls:
            client = MagicMock()
            mock_client_cls.return_value = client
            provider = GeminiLLMProvider(api_key="test_key")
            provider._client = client
            return provider

    @pytest.mark.asyncio
    async def test_prompt_includes_context(self, provider):
        provider._client.generate_content.return_value = [_chunk("Response")]

        async for _ in provider.generate_response(
            prompt="Question",
            context="Important context here",
            history=[],
        ):
            pass

        call_args = provider._client.generate_content.call_args
        contents = call_args.kwargs.get("contents", "")
        assert "Important context here" in str(contents)

    @pytest.mark.asyncio
    async def test_prompt_includes_question(self, provider):
        provider._client.generate_content.return_value = [_chunk("Response")]

        async for _ in provider.generate_response(
            prompt="What is Python?",
            context="Context",
            history=[],
        ):
            pass

        call_args = provider._client.generate_content.call_args
        contents = call_args.kwargs.get("contents", "")
        assert "What is Python?" in str(contents)


class TestGeminiLLMProviderBackwardsCompatibility:
    @pytest.fixture
    def provider(self):
        with patch("providers.llm.gemini.GeminiClient") as mock_client_cls:
            client = MagicMock()
            mock_client_cls.return_value = client
            provider = GeminiLLMProvider(api_key="test_key")
            provider._client = client
            return provider

    @pytest.mark.asyncio
    async def test_has_generate_answer_method(self, provider):
        assert hasattr(provider, "generate_answer")
        assert callable(provider.generate_answer)

    @pytest.mark.asyncio
    async def test_generate_answer_signature_compatible(self, provider):
        import inspect

        sig = inspect.signature(provider.generate_answer)
        params = list(sig.parameters.keys())

        assert "question" in params
        assert "context_chunks" in params
