"""
Tests for recent provider upgrades including OpenAI STT, Search Abstraction, and Factory updates.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.providers.base import TranscriptionResult, GroundedResponse, GroundingSource, SearchProvider
from src.providers.stt.openai import OpenAISTTProvider
from src.providers.search.duckduckgo import DuckDuckGoSearchProvider
from src.providers.search.gemini import GeminiSearchProvider
from src.providers.llm.openai import OpenAILLMProvider
from src.providers.llm.anthropic import AnthropicLLMProvider
from src.providers.factory import ProviderFactory, ProviderConfig, ProviderType

# --- OpenAI STT Tests ---

class TestOpenAISTTProvider:
    @patch("src.providers.stt.openai.AsyncOpenAI")
    def test_init(self, mock_openai):
        """Should initialize with valid API key."""
        provider = OpenAISTTProvider(api_key="sk-test")
        assert provider.client is not None
        mock_openai.assert_called_once_with(api_key="sk-test")

    def test_init_missing_key(self):
        """Should raise ValueError if no API key."""
        with pytest.raises(ValueError, match="API key is required"):
            OpenAISTTProvider(api_key="")

    @patch("src.providers.stt.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_transcribe(self, mock_openai_cls):
        """Should return transcription result."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        # Mock transcription response
        mock_transcript = MagicMock()
        mock_transcript.text = "Hello world"
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)
        
        provider = OpenAISTTProvider(api_key="sk-test")
        result = await provider.transcribe(b"audio_bytes")
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.confidence == 1.0

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
        """Should default to Gemini then DDG."""
        config = ProviderConfig() # No keys
        factory = ProviderFactory(config)
        
        order = factory.get_search_fallback_order()
        assert order == [ProviderType.GEMINI, ProviderType.DUCKDUCKGO]
        
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
