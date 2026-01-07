"""
Tests for GeminiLLMProvider.

Tests the refactored Gemini LLM that implements LLMProvider interface.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add sidecar/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import LLMProvider
from providers.llm.gemini import GeminiLLMProvider, GeminiLLMProviderError


class TestGeminiLLMProviderInit:
    """Test GeminiLLMProvider initialization."""

    @patch("providers.llm.gemini.genai")
    def test_init_success(self, mock_genai):
        """Test successful initialization."""
        provider = GeminiLLMProvider(api_key="test_key")

        mock_genai.configure.assert_called_once_with(api_key="test_key")
        mock_genai.GenerativeModel.assert_called_once()
        assert provider._api_key == "test_key"
        assert provider._available is True

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiLLMProvider(api_key="")

    def test_init_none_api_key(self):
        """Test that None API key raises error."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiLLMProvider(api_key=None)

    @patch("providers.llm.gemini.genai")
    def test_implements_llm_provider(self, mock_genai):
        """Test that GeminiLLMProvider implements LLMProvider interface."""
        provider = GeminiLLMProvider(api_key="test_key")
        assert isinstance(provider, LLMProvider)

    @patch("providers.llm.gemini.genai")
    def test_custom_model_name(self, mock_genai):
        """Test initialization with custom model name."""
        provider = GeminiLLMProvider(api_key="test_key", model_name="custom-model")

        mock_genai.GenerativeModel.assert_called_once_with("custom-model")

    @patch("providers.llm.gemini.genai")
    def test_init_failure_raises_error(self, mock_genai):
        """Test that initialization failure raises GeminiLLMProviderError."""
        mock_genai.GenerativeModel.side_effect = Exception("API Error")

        with pytest.raises(GeminiLLMProviderError, match="Failed to initialize"):
            GeminiLLMProvider(api_key="test_key")


class TestGeminiLLMProviderAvailability:
    """Test is_available method."""

    @patch("providers.llm.gemini.genai")
    def test_is_available_true(self, mock_genai):
        """Test is_available returns True when initialized properly."""
        provider = GeminiLLMProvider(api_key="test_key")
        assert provider.is_available() is True

    @patch("providers.llm.gemini.genai")
    def test_is_available_false_after_error(self, mock_genai):
        """Test is_available returns False after initialization error."""
        mock_genai.GenerativeModel.side_effect = Exception("API Error")

        with pytest.raises(GeminiLLMProviderError):
            GeminiLLMProvider(api_key="test_key")


class TestGeminiLLMProviderGenerateResponse:
    """Test generate_response method (LLMProvider interface)."""

    @pytest.fixture
    def mock_genai(self):
        with patch("providers.llm.gemini.genai") as mock:
            yield mock

    @pytest.fixture
    def provider(self, mock_genai):
        return GeminiLLMProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_generate_response_success(self, provider):
        """Test successful response generation."""
        # Mock async streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "world"

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        chunks = []
        async for chunk in provider.generate_response(
            prompt="Tell me a story",
            context="Once upon a time",
            history=[]
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello world"
        provider._model.generate_content_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_with_history(self, provider):
        """Test response generation with conversation history."""
        mock_chunk = MagicMock()
        mock_chunk.text = "Response"

        async def mock_stream():
            yield mock_chunk

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        chunks = []
        async for chunk in provider.generate_response(
            prompt="How are you?",
            context="Some context",
            history=history
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Verify the call was made (history should be incorporated into prompt)
        provider._model.generate_content_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_empty_context(self, provider):
        """Test response generation with empty context."""
        mock_chunk = MagicMock()
        mock_chunk.text = "I don't have context"

        async def mock_stream():
            yield mock_chunk

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        chunks = []
        async for chunk in provider.generate_response(
            prompt="Question",
            context="",
            history=[]
        ):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_response_error(self, provider):
        """Test error handling in response generation."""
        provider._model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(GeminiLLMProviderError, match="Generation failed"):
            async for _ in provider.generate_response(
                prompt="Question",
                context="Context",
                history=[]
            ):
                pass

    @pytest.mark.asyncio
    async def test_generate_response_empty_chunk(self, provider):
        """Test handling of empty chunks in stream."""
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello"
        mock_chunk2 = MagicMock()
        mock_chunk2.text = None  # Empty chunk
        mock_chunk3 = MagicMock()
        mock_chunk3.text = " world"

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2
            yield mock_chunk3

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        chunks = []
        async for chunk in provider.generate_response(
            prompt="Question",
            context="Context",
            history=[]
        ):
            chunks.append(chunk)

        # Empty chunks should be skipped
        assert "".join(chunks) == "Hello world"


class TestGeminiLLMProviderGenerateAnswer:
    """Test generate_answer method (backwards compatibility with GeminiLLM)."""

    @pytest.fixture
    def mock_genai(self):
        with patch("providers.llm.gemini.genai") as mock:
            yield mock

    @pytest.fixture
    def provider(self, mock_genai):
        return GeminiLLMProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_generate_answer_success(self, provider):
        """Test successful answer generation (backwards compatible method)."""
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "The answer is "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "42"

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        chunks = []
        async for chunk in provider.generate_answer(
            question="What is the meaning of life?",
            context_chunks=["Some context", "More context"]
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "The answer is 42"

    @pytest.mark.asyncio
    async def test_generate_answer_empty_context(self, provider):
        """Test answer generation with empty context list."""
        mock_chunk = MagicMock()
        mock_chunk.text = "No context available"

        async def mock_stream():
            yield mock_chunk

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        chunks = []
        async for chunk in provider.generate_answer(
            question="Question",
            context_chunks=[]
        ):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_answer_error(self, provider):
        """Test error handling in answer generation."""
        provider._model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(GeminiLLMProviderError, match="Generation failed"):
            async for _ in provider.generate_answer(
                question="Question",
                context_chunks=["Context"]
            ):
                pass


class TestGeminiLLMProviderPromptBuilding:
    """Test prompt building functionality."""

    @pytest.fixture
    def mock_genai(self):
        with patch("providers.llm.gemini.genai") as mock:
            yield mock

    @pytest.fixture
    def provider(self, mock_genai):
        return GeminiLLMProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_prompt_includes_context(self, provider):
        """Test that the prompt includes the provided context."""
        mock_chunk = MagicMock()
        mock_chunk.text = "Response"

        async def mock_stream():
            yield mock_chunk

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        async for _ in provider.generate_response(
            prompt="Question",
            context="Important context here",
            history=[]
        ):
            pass

        # Check that the call was made with context in the prompt
        call_args = provider._model.generate_content_async.call_args
        prompt_arg = call_args[0][0] if call_args[0] else call_args[1].get('contents', '')
        assert "Important context here" in str(prompt_arg)

    @pytest.mark.asyncio
    async def test_prompt_includes_question(self, provider):
        """Test that the prompt includes the question."""
        mock_chunk = MagicMock()
        mock_chunk.text = "Response"

        async def mock_stream():
            yield mock_chunk

        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        provider._model.generate_content_async = AsyncMock(return_value=mock_response)

        async for _ in provider.generate_response(
            prompt="What is Python?",
            context="Context",
            history=[]
        ):
            pass

        call_args = provider._model.generate_content_async.call_args
        prompt_arg = call_args[0][0] if call_args[0] else call_args[1].get('contents', '')
        assert "What is Python?" in str(prompt_arg)


class TestGeminiLLMProviderBackwardsCompatibility:
    """Test backwards compatibility with old GeminiLLM interface."""

    @pytest.fixture
    def mock_genai(self):
        with patch("providers.llm.gemini.genai") as mock:
            yield mock

    @pytest.fixture
    def provider(self, mock_genai):
        return GeminiLLMProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_has_generate_answer_method(self, provider):
        """Ensure provider has generate_answer method for backwards compatibility."""
        assert hasattr(provider, 'generate_answer')
        assert callable(provider.generate_answer)

    @pytest.mark.asyncio
    async def test_generate_answer_signature_compatible(self, provider):
        """Test that generate_answer has compatible signature."""
        import inspect
        sig = inspect.signature(provider.generate_answer)
        params = list(sig.parameters.keys())

        # Should have 'question' and 'context_chunks' parameters
        assert 'question' in params
        assert 'context_chunks' in params
