"""
Tests for GeminiSearchProvider with web search grounding.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.providers.llm.gemini_search import (
    GeminiSearchProvider,
    GeminiSearchProviderError,
    GroundedResponse,
    GroundingSource,
)


class TestGeminiSearchProviderInit:
    """Tests for GeminiSearchProvider initialization."""
    
    def test_requires_api_key(self):
        """Should raise ValueError if API key is empty."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiSearchProvider(api_key="")
    
    def test_requires_api_key_none(self):
        """Should raise ValueError if API key is None."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiSearchProvider(api_key=None)
    
    @patch("google.genai.Client")
    def test_initializes_with_valid_key(self, mock_client):
        """Should initialize successfully with valid API key."""
        provider = GeminiSearchProvider(api_key="test-key")
        
        assert provider.is_available()
        assert provider._model_name == "gemini-2.5-flash"
    
    @patch("google.genai.Client")
    def test_custom_model_name(self, mock_client):
        """Should use custom model name if provided."""
        provider = GeminiSearchProvider(
            api_key="test-key",
            model_name="gemini-2.5-pro"
        )
        
        assert provider._model_name == "gemini-2.5-pro"


class TestGroundedResponseDataclass:
    """Tests for GroundedResponse dataclass."""
    
    def test_grounded_response_creation(self):
        """Should create GroundedResponse with all fields."""
        sources = [
            GroundingSource(title="Source 1", url="https://example.com/1"),
            GroundingSource(title="Source 2", url="https://example.com/2"),
        ]
        
        response = GroundedResponse(
            text="This is the response text",
            search_queries=["query 1", "query 2"],
            sources=sources
        )
        
        assert response.text == "This is the response text"
        assert len(response.search_queries) == 2
        assert len(response.sources) == 2
        assert response.sources[0].title == "Source 1"
    
    def test_grounding_source_creation(self):
        """Should create GroundingSource with title and url."""
        source = GroundingSource(
            title="Example Article",
            url="https://example.com/article"
        )
        
        assert source.title == "Example Article"
        assert source.url == "https://example.com/article"


class TestGeminiSearchProviderMethods:
    """Tests for GeminiSearchProvider methods."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a provider with mocked client."""
        with patch("google.genai.Client") as mock_client:
            provider = GeminiSearchProvider(api_key="test-key")
            provider._client = mock_client.return_value
            return provider
    
    def test_build_prompt_basic(self, mock_provider):
        """Should build prompt with just the query."""
        prompt = mock_provider._build_prompt(
            prompt="What is the weather?",
            context="",
            history=[]
        )
        
        assert "What is the weather?" in prompt
        assert "research assistant" in prompt.lower()
    
    def test_build_prompt_with_context(self, mock_provider):
        """Should include context in prompt."""
        prompt = mock_provider._build_prompt(
            prompt="Tell me more",
            context="Company XYZ is a tech startup",
            history=[]
        )
        
        assert "Company XYZ is a tech startup" in prompt
        assert "Additional Context" in prompt
    
    def test_build_prompt_with_history(self, mock_provider):
        """Should include conversation history."""
        prompt = mock_provider._build_prompt(
            prompt="Follow up question",
            context="",
            history=[
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "First response"},
            ]
        )
        
        assert "First message" in prompt
        assert "First response" in prompt
        assert "Conversation History" in prompt


class TestGeminiSearchProviderGenerate:
    """Tests for generate methods (require mocking async)."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a provider with mocked client."""
        with patch("google.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            provider = GeminiSearchProvider(api_key="test-key")
            return provider, mock_client
    
    @pytest.mark.asyncio
    async def test_generate_response_returns_text(self, mock_provider):
        """Should yield response text."""
        provider, mock_client = mock_provider
        
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Generated response with grounding"
        mock_response.candidates = []
        
        mock_client.models.generate_content.return_value = mock_response
        
        chunks = []
        async for chunk in provider.generate_response(
            prompt="Test query",
            context="",
            history=[]
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 1
        assert "Generated response" in chunks[0]
    
    @pytest.mark.asyncio
    async def test_generate_grounded_response(self, mock_provider):
        """Should return GroundedResponse with metadata."""
        provider, mock_client = mock_provider
        
        # Mock grounding metadata
        mock_chunk = MagicMock()
        mock_chunk.web.title = "Example Source"
        mock_chunk.web.uri = "https://example.com"
        
        mock_metadata = MagicMock()
        mock_metadata.web_search_queries = ["test query"]
        mock_metadata.grounding_chunks = [mock_chunk]
        
        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = mock_metadata
        
        mock_response = MagicMock()
        mock_response.text = "Grounded response text"
        mock_response.candidates = [mock_candidate]
        
        mock_client.models.generate_content.return_value = mock_response
        
        result = await provider.generate_grounded_response("Test query")
        
        assert isinstance(result, GroundedResponse)
        assert result.text == "Grounded response text"
        assert "test query" in result.search_queries
        assert len(result.sources) == 1
        assert result.sources[0].title == "Example Source"
    
    @pytest.mark.asyncio
    async def test_research_company(self, mock_provider):
        """Should format company research query correctly."""
        provider, mock_client = mock_provider
        
        mock_response = MagicMock()
        mock_response.text = "Company research results"
        mock_response.candidates = []
        
        mock_client.models.generate_content.return_value = mock_response
        
        result = await provider.research_company("TechCorp Inc")
        
        assert isinstance(result, GroundedResponse)
        # Verify the query included company name
        call_args = mock_client.models.generate_content.call_args
        assert "TechCorp Inc" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_research_interviewer(self, mock_provider):
        """Should format interviewer research query correctly."""
        provider, mock_client = mock_provider
        
        mock_response = MagicMock()
        mock_response.text = "Interviewer research results"
        mock_response.candidates = []
        
        mock_client.models.generate_content.return_value = mock_response
        
        result = await provider.research_interviewer(
            name="John Smith",
            company="TechCorp",
            role="VP of Engineering"
        )
        
        assert isinstance(result, GroundedResponse)
        call_args = mock_client.models.generate_content.call_args
        assert "John Smith" in str(call_args)
        assert "TechCorp" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_research_industry_trends(self, mock_provider):
        """Should format industry trends query correctly."""
        provider, mock_client = mock_provider
        
        mock_response = MagicMock()
        mock_response.text = "Industry trends results"
        mock_response.candidates = []
        
        mock_client.models.generate_content.return_value = mock_response
        
        result = await provider.research_industry_trends("AI/ML")
        
        assert isinstance(result, GroundedResponse)
        call_args = mock_client.models.generate_content.call_args
        assert "AI/ML" in str(call_args)


class TestGeminiSearchProviderErrors:
    """Tests for error handling."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a provider with mocked client."""
        with patch("google.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            provider = GeminiSearchProvider(api_key="test-key")
            return provider, mock_client
    
    @pytest.mark.asyncio
    async def test_handles_client_not_initialized(self):
        """Should raise error if client is not initialized."""
        with patch("google.genai.Client") as mock_client_class:
            provider = GeminiSearchProvider(api_key="test-key")
            provider._client = None
            
            with pytest.raises(GeminiSearchProviderError, match="not initialized"):
                async for _ in provider.generate_response("test", "", []):
                    pass
    
    @pytest.mark.asyncio
    async def test_handles_generation_error(self, mock_provider):
        """Should wrap generation errors in GeminiSearchProviderError."""
        provider, mock_client = mock_provider
        
        mock_client.models.generate_content.side_effect = Exception("API error")
        
        with pytest.raises(GeminiSearchProviderError, match="Generation failed"):
            async for _ in provider.generate_response("test", "", []):
                pass
