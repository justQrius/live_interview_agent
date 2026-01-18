import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from providers.base import SearchProvider, GroundingSource
from providers.llm.openai import OpenAILLMProvider

class MockSearchProvider(SearchProvider):
    async def search(self, query: str, limit: int = 5):
        return [
            GroundingSource(
                title="Test Source",
                url="http://test.com",
                snippet="This is a test snippet about the query."
            )
        ]
        
    async def research(self, topic: str):
        pass

class TestOpenAISearchGrounding:
    @pytest.fixture
    def mock_openai_class(self):
        with patch("providers.llm.openai.AsyncOpenAI") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield mock
            
    @pytest.fixture
    def mock_prompts(self):
        with (
            patch("providers.llm.openai.build_system_prompt") as mock_build,
            patch("providers.llm.openai.format_context_for_prompt") as mock_fmt
        ):
            mock_build.return_value = ("System Prompt", "general")
            # Mock formatting to just return the context string directly
            mock_fmt.side_effect = lambda c, q: c
            yield mock_build, mock_fmt

    @pytest.mark.asyncio
    async def test_search_triggering(self, mock_openai_class, mock_prompts):
        """Test that search is triggered for relevant queries."""
        mock_search = AsyncMock()
        mock_search.search.return_value = [
            GroundingSource(title="News", url="url", snippet="Recent news content")
        ]
        
        provider = OpenAILLMProvider(
            api_key="test",
            search_provider=mock_search,
            search_enabled=True
        )
        
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = AsyncMock()
        mock_client.chat.completions.create.return_value.__aiter__.return_value = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Response"))])
        ]
        
        # Query containing trigger word "latest"
        prompt = "What are the latest industry trends?"
        
        chunks = []
        async for chunk in provider.generate_response(prompt, "ctx", []):
            chunks.append(chunk)
            
        # Verify search was called
        mock_search.search.assert_called_once()
        args = mock_search.search.call_args
        assert "latest industry trends" in args[0] or prompt in args[0]

    @pytest.mark.asyncio
    async def test_search_injection(self, mock_openai_class, mock_prompts):
        """Test that search results are injected into context."""
        mock_search = AsyncMock()
        mock_search.search.return_value = [
            GroundingSource(title="News", url="url", snippet="Recent news content")
        ]
        
        provider = OpenAILLMProvider(
            api_key="test",
            search_provider=mock_search,
            search_enabled=True
        )
        
        mock_client = mock_openai_class.return_value
        
        # Setup async iterator for response
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content="Response"))]
        async def async_gen():
            yield mock_chunk
        mock_client.chat.completions.create.return_value = async_gen()
        
        prompt = "Tell me about recent competitors."
        
        async for _ in provider.generate_response(prompt, "Original Context", []):
            pass
            
        # Verify context injection in OpenAI call
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        last_message = messages[-1]["content"]
        
        # Should contain original context AND search results
        assert "Original Context" in last_message
        assert "REAL-TIME SEARCH RESULTS" in last_message
        assert "Recent news content" in last_message

    @pytest.mark.asyncio
    async def test_no_search_if_disabled(self, mock_openai_class, mock_prompts):
        """Test that search is NOT triggered if disabled."""
        mock_search = AsyncMock()
        
        provider = OpenAILLMProvider(
            api_key="test",
            search_provider=mock_search,
            search_enabled=False # Disabled
        )
        
        mock_client = mock_openai_class.return_value
        async def async_gen():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Response"))])
        mock_client.chat.completions.create.return_value = async_gen()
        
        prompt = "What are the latest trends?"
        
        async for _ in provider.generate_response(prompt, "ctx", []):
            pass
            
        mock_search.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_search_if_no_trigger(self, mock_openai_class, mock_prompts):
        """Test that search is NOT triggered for irrelevant queries."""
        mock_search = AsyncMock()
        
        provider = OpenAILLMProvider(
            api_key="test",
            search_provider=mock_search,
            search_enabled=True
        )
        
        mock_client = mock_openai_class.return_value
        async def async_gen():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Response"))])
        mock_client.chat.completions.create.return_value = async_gen()
        
        prompt = "Tell me about a time you failed." # Behavioral question, no search needed
        
        async for _ in provider.generate_response(prompt, "ctx", []):
            pass
            
        mock_search.search.assert_not_called()
