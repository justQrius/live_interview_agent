"""
Tests for GeminiSearchProvider (SearchProvider implementation).
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.providers.search.gemini import (
    GeminiSearchProvider,
    GeminiSearchProviderError,
)
from src.providers.base import GroundedResponse, GroundingSource

class TestGeminiSearchProviderInit:
    """Tests for GeminiSearchProvider initialization."""
    
    def test_requires_api_key(self):
        """Should raise ValueError if API key is empty."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiSearchProvider(api_key="")
    
    @patch("google.genai.Client")
    def test_initializes_with_valid_key(self, mock_client):
        """Should initialize successfully with valid API key."""
        provider = GeminiSearchProvider(api_key="test-key")
        
        assert provider.is_available()
        assert provider._model_name == "gemini-3-flash-preview"
    
    @patch("google.genai.Client")
    def test_custom_model_name(self, mock_client):
        """Should use custom model name if provided."""
        provider = GeminiSearchProvider(
            api_key="test-key",
            model_name="gemini-2.5-pro"
        )
        
        assert provider._model_name == "gemini-2.5-pro"

class TestGeminiSearchProviderMethods:
    """Tests for GeminiSearchProvider methods."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a provider with mocked client."""
        with patch("google.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            provider = GeminiSearchProvider(api_key="test-key")
            provider._client = mock_client
            return provider, mock_client
            
    @pytest.mark.asyncio
    async def test_research_success(self, mock_provider):
        """Should return GroundedResponse with sources."""
        provider, mock_client = mock_provider
        
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Research result"
        
        # Mock metadata
        mock_chunk = MagicMock()
        mock_chunk.web.title = "Source 1"
        mock_chunk.web.uri = "http://example.com"
        
        mock_metadata = MagicMock()
        mock_metadata.web_search_queries = ["query"]
        mock_metadata.grounding_chunks = [mock_chunk]
        
        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = mock_metadata
        mock_response.candidates = [mock_candidate]
        
        mock_client.models.generate_content.return_value = mock_response
        
        result = await provider.research("topic")
        
        assert isinstance(result, GroundedResponse)
        assert result.text == "Research result"
        assert result.sources[0].title == "Source 1"
        
    @pytest.mark.asyncio
    async def test_search_success(self, mock_provider):
        """Should return list of GroundingSource."""
        provider, mock_client = mock_provider
        
        # Mock response (reuse logic from research since search calls research)
        mock_response = MagicMock()
        mock_response.text = "ignored"
        
        mock_chunk = MagicMock()
        mock_chunk.web.title = "Source 1"
        mock_chunk.web.uri = "http://example.com"
        
        mock_metadata = MagicMock()
        mock_metadata.grounding_chunks = [mock_chunk]
        
        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = mock_metadata
        mock_response.candidates = [mock_candidate]
        
        mock_client.models.generate_content.return_value = mock_response
        
        results = await provider.search("query", limit=5)
        
        assert len(results) == 1
        assert isinstance(results[0], GroundingSource)
        assert results[0].title == "Source 1"

    @pytest.mark.asyncio
    async def test_handles_client_not_initialized(self):
        """Should raise error if client is not initialized."""
        with patch("google.genai.Client"):
            provider = GeminiSearchProvider(api_key="test-key")
            provider._client = None
            
            with pytest.raises(GeminiSearchProviderError, match="not initialized"):
                await provider.research("test")
