"""
Tests for recent provider upgrades including Search Abstraction and Factory updates.

Note: OpenAI STT tests were removed in Phase 3 STT Simplification.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.providers.base import GroundedResponse, GroundingSource, SearchProvider
from src.providers.search.duckduckgo import DuckDuckGoSearchProvider
from src.providers.search.gemini import GeminiSearchProvider
from src.providers.llm.openai import OpenAILLMProvider
from src.providers.llm.anthropic import AnthropicLLMProvider
from src.providers.factory import ProviderFactory, ProviderConfig, ProviderType

# --- Search Provider Tests ---

class TestDuckDuckGoSearchProvider:
    @patch("src.providers.search.duckduckgo.DDGS")
    def test_init(self, mock_ddgs):
        """Should initialize DDG provider."""
        provider = DuckDuckGoSearchProvider()
        assert provider._ddgs is not None

    @patch("src.providers.search.duckduckgo.DDGS")
    @pytest.mark.asyncio
    async def test_search(self, mock_ddgs_cls):
        """Should return search results."""
        mock_ddgs_inst = MagicMock()
        mock_ddgs_cls.return_value = mock_ddgs_inst
        
        # Mock text search results (iterator)
        mock_ddgs_inst.text.return_value = [
            {"title": "Result 1", "href": "http://1.com", "body": "Snippet 1"},
            {"title": "Result 2", "href": "http://2.com", "body": "Snippet 2"},
        ]
        
        provider = DuckDuckGoSearchProvider()
        results = await provider.search("query")
        
        assert len(results) == 2
        assert isinstance(results[0], GroundingSource)
        assert results[0].title == "Result 1"
        assert results[0].url == "http://1.com"

# --- LLM Thinking Budget Tests ---

class TestOpenAIThinking:
    @patch("src.providers.llm.openai.AsyncOpenAI")
    def test_thinking_budget_init(self, mock_openai):
        """Should store thinking budget."""
        provider = OpenAILLMProvider(api_key="sk-test", thinking_budget=2000)
        assert provider._thinking_budget == 2000
    
    @patch("src.providers.llm.openai.AsyncOpenAI")
    def test_construct_messages_with_thinking(self, mock_openai):
        """Should inject thinking instructions if budget set."""
        provider = OpenAILLMProvider(api_key="sk-test", thinking_budget=2000)
        messages = provider._construct_messages("Question", "", [])
        
        system_msg = messages[0]["content"]
        assert "<thinking>" in system_msg
        assert "Thinking Process" in system_msg

class TestAnthropicThinking:
    @patch("src.providers.llm.anthropic.AsyncAnthropic")
    def test_thinking_budget_init(self, mock_anthropic):
        """Should store thinking budget."""
        provider = AnthropicLLMProvider(api_key="sk-test", thinking_budget=2000)
        assert provider._thinking_budget == 2000

# --- Factory Tests ---

class TestProviderFactoryUpgrades:
    def test_get_search_provider_default(self):
        """Should default to DDG when no Gemini key, Gemini+DDG when key present."""
        # Without Gemini key, only DDG is in fallback order
        config = ProviderConfig()  # No keys
        factory = ProviderFactory(config)
        
        order = factory.get_search_fallback_order()
        assert order == [ProviderType.DUCKDUCKGO]
        
        # With Gemini key, Gemini comes first then DDG
        config_with_key = ProviderConfig(gemini_api_key="gemini-key")
        factory_with_key = ProviderFactory(config_with_key)
        
        order_with_key = factory_with_key.get_search_fallback_order()
        assert order_with_key == [ProviderType.GEMINI, ProviderType.DUCKDUCKGO]
        
    @patch("src.providers.search.duckduckgo.DuckDuckGoSearchProvider")
    def test_get_search_provider_ddg_fallback(self, mock_ddg_cls):
        """Should fallback to DDG if Gemini key missing."""
        config = ProviderConfig() # No API keys
        factory = ProviderFactory(config)
        
        # Should return DDG because it's "free" and in fallback list
        provider = factory.get_search_provider()
        
        # Since we mocked the class, the factory returns the mock instance
        # Verify init was called
        mock_ddg_cls.assert_called()

    @patch("src.providers.search.gemini.GeminiSearchProvider")
    def test_get_search_provider_gemini_primary(self, mock_gemini_cls):
        """Should use Gemini if key present."""
        config = ProviderConfig(gemini_api_key="gemini-key")
        factory = ProviderFactory(config)
        
        provider = factory.get_search_provider()
        mock_gemini_cls.assert_called_with("gemini-key")


# --- STT Factory Tests (Phase 3 Simplified) ---

class TestProviderFactorySTTSimplified:
    """Tests for the simplified STT provider configuration after Phase 3."""
    
    def test_stt_fallback_order_simplified(self):
        """Should only include LOCAL_WHISPER and GEMINI in fallback order."""
        config = ProviderConfig(gemini_api_key="gemini-key")
        factory = ProviderFactory(config)
        
        order = factory.get_stt_fallback_order()
        
        # Only LOCAL_WHISPER and GEMINI should be in the order
        assert ProviderType.LOCAL_WHISPER in order
        assert ProviderType.GEMINI in order
        # Removed providers should NOT be in order
        assert ProviderType.GROQ not in order
        assert ProviderType.DEEPGRAM not in order
        assert ProviderType.OPENAI not in order
    
    def test_available_stt_providers_simplified(self):
        """Should only list LOCAL_WHISPER and GEMINI as available."""
        config = ProviderConfig(
            gemini_api_key="gemini-key",
            groq_api_key="groq-key",  # Should be ignored for STT
            openai_api_key="openai-key",  # Should be ignored for STT
        )
        factory = ProviderFactory(config)
        
        available = factory.get_available_stt_providers()
        
        assert ProviderType.LOCAL_WHISPER in available
        assert ProviderType.GEMINI in available
        # GROQ and OPENAI should NOT be listed even with keys
        assert ProviderType.GROQ not in available
        assert ProviderType.OPENAI not in available
    
    def test_available_streaming_providers_only_deepgram(self):
        """Should only list Deepgram streaming modes."""
        config = ProviderConfig(
            deepgram_api_key="deepgram-key",
            openai_api_key="openai-key",  # Should be ignored for streaming
        )
        factory = ProviderFactory(config)
        
        from src.providers.config import StreamingMode
        available = factory.get_available_streaming_providers()
        
        assert StreamingMode.AUTO in available
        assert StreamingMode.DEEPGRAM in available
        assert StreamingMode.DEEPGRAM_FLUX in available
        # Removed streaming modes should NOT be available
        # Note: These enums are removed from config.py, so we can't even reference them
