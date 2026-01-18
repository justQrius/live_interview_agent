import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import LLMProvider
from providers.llm.openai import OpenAILLMProvider, OpenAILLMProviderError


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

    def test_init_with_custom_model(self, mock_openai_class):
        """Test initialization with a custom model."""
        provider = OpenAILLMProvider("test-key", model="gpt-5.2")
        assert provider.model == "gpt-5.2"

    def test_init_with_thinking_budget(self, mock_openai_class):
        """Test initialization with thinking budget."""
        provider = OpenAILLMProvider("test-key", thinking_budget=2048)
        assert provider._thinking_budget == 2048
        assert provider._reasoning_effort == "medium"

    def test_init_with_reasoning_effort(self, mock_openai_class):
        """Test initialization with explicit reasoning effort."""
        provider = OpenAILLMProvider("test-key", reasoning_effort="high")
        assert provider._reasoning_effort == "high"

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

        with pytest.raises(OpenAILLMProviderError, match="Generation failed"):
            async for _ in provider.generate_response("prompt", "context", []):
                pass


class TestReasoningModelDetection:
    """Tests for reasoning model detection and parameter handling."""

    @pytest.fixture
    def mock_openai_class(self):
        with patch("providers.llm.openai.AsyncOpenAI") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield mock

    def test_is_reasoning_model_o1_series(self, mock_openai_class):
        """Test detection of o1 series reasoning models."""
        provider = OpenAILLMProvider("test-key")
        
        # O1 series
        assert provider._is_reasoning_model("o1") is True
        assert provider._is_reasoning_model("o1-mini") is True
        assert provider._is_reasoning_model("o1-preview") is True
        assert provider._is_reasoning_model("o1-2024-12-17") is True  # Versioned

    def test_is_reasoning_model_o3_series(self, mock_openai_class):
        """Test detection of o3 series reasoning models."""
        provider = OpenAILLMProvider("test-key")
        
        # O3 series
        assert provider._is_reasoning_model("o3") is True
        assert provider._is_reasoning_model("o3-mini") is True
        assert provider._is_reasoning_model("o3-mini-2025-01-31") is True  # Versioned

    def test_is_reasoning_model_o4_series(self, mock_openai_class):
        """Test detection of o4 series reasoning models."""
        provider = OpenAILLMProvider("test-key")
        
        # O4 series
        assert provider._is_reasoning_model("o4-mini") is True

    def test_is_reasoning_model_gpt5_series(self, mock_openai_class):
        """Test detection of GPT-5 reasoning models."""
        provider = OpenAILLMProvider("test-key")
        
        # GPT-5 series (reasoning models)
        assert provider._is_reasoning_model("gpt-5.1") is True
        assert provider._is_reasoning_model("gpt-5.2") is True
        assert provider._is_reasoning_model("gpt-5-mini") is True
        assert provider._is_reasoning_model("gpt-5-nano") is True

    def test_is_reasoning_model_standard_models(self, mock_openai_class):
        """Test that standard models are NOT detected as reasoning models."""
        provider = OpenAILLMProvider("test-key")
        
        # Standard models (NOT reasoning)
        assert provider._is_reasoning_model("gpt-4o") is False
        assert provider._is_reasoning_model("gpt-4o-mini") is False
        assert provider._is_reasoning_model("gpt-4-turbo") is False
        assert provider._is_reasoning_model("gpt-3.5-turbo") is False

    def test_supports_reasoning_effort_o_series(self, mock_openai_class):
        """Test reasoning_effort support detection for o-series models."""
        provider = OpenAILLMProvider("test-key")
        
        # O-series supports reasoning_effort
        assert provider._supports_reasoning_effort("o1") is True
        assert provider._supports_reasoning_effort("o1-mini") is True
        assert provider._supports_reasoning_effort("o3-mini") is True
        assert provider._supports_reasoning_effort("o4-mini") is True

    def test_supports_reasoning_effort_gpt_models(self, mock_openai_class):
        """Test that GPT models don't support reasoning_effort."""
        provider = OpenAILLMProvider("test-key")
        
        # GPT models do NOT support reasoning_effort
        assert provider._supports_reasoning_effort("gpt-4o") is False
        assert provider._supports_reasoning_effort("gpt-5.2") is False
        assert provider._supports_reasoning_effort("gpt-5-mini") is False

    def test_infer_reasoning_effort_from_budget(self, mock_openai_class):
        """Test inference of reasoning effort from thinking budget."""
        provider = OpenAILLMProvider("test-key")
        
        assert provider._infer_reasoning_effort(None) is None
        assert provider._infer_reasoning_effort(256) == "low"
        assert provider._infer_reasoning_effort(512) == "low"
        assert provider._infer_reasoning_effort(1024) == "medium"
        assert provider._infer_reasoning_effort(2048) == "medium"
        assert provider._infer_reasoning_effort(4096) == "high"


class TestReasoningModelParameters:
    """Tests for parameter handling with reasoning vs standard models."""

    @pytest.fixture
    def mock_openai_class(self):
        with patch("providers.llm.openai.AsyncOpenAI") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield mock

    @pytest.mark.asyncio
    async def test_standard_model_uses_sampling_params(self, mock_openai_class):
        """Test that standard models use sampling parameters."""
        with (
            patch("providers.llm.openai.build_system_prompt") as mock_build_system_prompt,
            patch("providers.llm.openai.format_context_for_prompt") as mock_format_context,
        ):
            mock_build_system_prompt.return_value = ("SYS", "general")
            mock_format_context.return_value = "CTX"

            mock_client = mock_openai_class.return_value
            provider = OpenAILLMProvider("test-key", model="gpt-4o")

            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]

            async def async_gen():
                yield mock_chunk

            mock_client.chat.completions.create.return_value = async_gen()

            chunks = []
            async for chunk in provider.generate_response("test", "ctx", []):
                chunks.append(chunk)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            
            # Standard model SHOULD have sampling parameters
            assert "temperature" in call_kwargs
            assert "frequency_penalty" in call_kwargs
            assert "presence_penalty" in call_kwargs
            assert "top_p" in call_kwargs
            
            # Standard model should NOT have max_completion_tokens
            assert "max_completion_tokens" not in call_kwargs

    @pytest.mark.asyncio
    async def test_reasoning_model_skips_sampling_params(self, mock_openai_class):
        """Test that reasoning models skip unsupported sampling parameters."""
        with (
            patch("providers.llm.openai.build_system_prompt") as mock_build_system_prompt,
            patch("providers.llm.openai.format_context_for_prompt") as mock_format_context,
        ):
            mock_build_system_prompt.return_value = ("SYS", "general")
            mock_format_context.return_value = "CTX"

            mock_client = mock_openai_class.return_value
            provider = OpenAILLMProvider("test-key", model="o3-mini")

            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]

            async def async_gen():
                yield mock_chunk

            mock_client.chat.completions.create.return_value = async_gen()

            chunks = []
            async for chunk in provider.generate_response("test", "ctx", []):
                chunks.append(chunk)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            
            # Reasoning model should NOT have sampling parameters
            assert "temperature" not in call_kwargs
            assert "frequency_penalty" not in call_kwargs
            assert "presence_penalty" not in call_kwargs
            assert "top_p" not in call_kwargs
            
            # Reasoning model SHOULD have max_completion_tokens
            assert "max_completion_tokens" in call_kwargs
            assert call_kwargs["max_completion_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_reasoning_model_uses_developer_role(self, mock_openai_class):
        """Test that reasoning models use 'developer' role instead of 'system'."""
        with (
            patch("providers.llm.openai.build_system_prompt") as mock_build_system_prompt,
            patch("providers.llm.openai.format_context_for_prompt") as mock_format_context,
        ):
            mock_build_system_prompt.return_value = ("SYS", "general")
            mock_format_context.return_value = "CTX"

            mock_client = mock_openai_class.return_value
            provider = OpenAILLMProvider("test-key", model="o1-mini")

            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]

            async def async_gen():
                yield mock_chunk

            mock_client.chat.completions.create.return_value = async_gen()

            chunks = []
            async for chunk in provider.generate_response("test", "ctx", []):
                chunks.append(chunk)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            messages = call_kwargs["messages"]
            
            # First message should have 'developer' role for reasoning models
            assert messages[0]["role"] == "developer"

    @pytest.mark.asyncio
    async def test_reasoning_model_with_reasoning_effort(self, mock_openai_class):
        """Test that o-series models get reasoning_effort parameter."""
        with (
            patch("providers.llm.openai.build_system_prompt") as mock_build_system_prompt,
            patch("providers.llm.openai.format_context_for_prompt") as mock_format_context,
        ):
            mock_build_system_prompt.return_value = ("SYS", "general")
            mock_format_context.return_value = "CTX"

            mock_client = mock_openai_class.return_value
            provider = OpenAILLMProvider("test-key", model="o3-mini", reasoning_effort="high")

            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]

            async def async_gen():
                yield mock_chunk

            mock_client.chat.completions.create.return_value = async_gen()

            chunks = []
            async for chunk in provider.generate_response("test", "ctx", []):
                chunks.append(chunk)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            
            # O-series should have reasoning_effort
            assert "reasoning_effort" in call_kwargs
            assert call_kwargs["reasoning_effort"] == "high"


class TestModelFallback:
    """Tests for model fallback chain."""

    @pytest.fixture
    def mock_openai_class(self):
        with patch("providers.llm.openai.AsyncOpenAI") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield mock

    def test_build_fallback_chain_standard_model(self, mock_openai_class):
        """Test fallback chain for standard models."""
        provider = OpenAILLMProvider("test-key", model="gpt-4o")
        chain = provider._build_fallback_chain()
        
        assert chain[0] == "gpt-4o"
        assert len(chain) >= 2
        # Should have fallbacks
        assert "gpt-5-mini" in chain

    def test_build_fallback_chain_reasoning_model(self, mock_openai_class):
        """Test fallback chain for reasoning models."""
        provider = OpenAILLMProvider("test-key", model="o1")
        chain = provider._build_fallback_chain()
        
        assert chain[0] == "o1"
        assert len(chain) >= 2
        # Should have other reasoning models as fallback first
        assert "o3-mini" in chain
        # Ultimate fallback to standard model
        assert "gpt-4o" in chain

    @pytest.mark.asyncio
    async def test_fallback_on_parameter_error(self, mock_openai_class):
        """Test that parameter errors trigger model fallback."""
        with (
            patch("providers.llm.openai.build_system_prompt") as mock_build_system_prompt,
            patch("providers.llm.openai.format_context_for_prompt") as mock_format_context,
        ):
            mock_build_system_prompt.return_value = ("SYS", "general")
            mock_format_context.return_value = "CTX"

            mock_client = mock_openai_class.return_value
            provider = OpenAILLMProvider("test-key", model="o3-mini")

            call_count = 0

            # First call fails with parameter error, second succeeds
            async def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count == 1:
                    raise Exception("Unsupported parameter: 'presence_penalty' is not supported")
                
                # Second call succeeds
                mock_chunk = MagicMock()
                mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]

                async def async_gen():
                    yield mock_chunk

                return async_gen()

            mock_client.chat.completions.create.side_effect = side_effect

            chunks = []
            async for chunk in provider.generate_response("test", "ctx", []):
                chunks.append(chunk)

            # Should have succeeded with fallback
            assert chunks == ["Hello"]
            # Should have called API twice (first failed, second succeeded)
            assert call_count == 2
