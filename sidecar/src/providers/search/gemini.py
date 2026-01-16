"""
Gemini Search Provider.

Implements SearchProvider interface using Google Gemini with Grounding.
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..base import SearchProvider, GroundedResponse, GroundingSource
from ..config import GeminiModels

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 90  # Longer timeout for web search

class GeminiSearchProviderError(Exception):
    """Exception raised when Gemini Search provider operations fail."""
    pass


class GeminiSearchProvider(SearchProvider):
    """
    Search provider using Google Gemini with web search grounding.
    """

    DEFAULT_MODEL = "gemini-3-flash-preview"  # Centralized in config.py as GeminiModels.DEFAULT_SEARCH
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        Initialize Gemini Search provider.
        """
        super().__init__()
        
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._model_name = model_name or self.DEFAULT_MODEL
        self._available = False
        self._client = None
        self._genai = None
        self._types = None

        try:
            # Import the new SDK
            from google import genai
            from google.genai import types
            
            self._genai = genai
            self._types = types
            
            # Initialize client with API key
            self._client = genai.Client(api_key=api_key)
            self._available = True
            logger.info(f"GeminiSearchProvider initialized with model {self._model_name}")
            
        except ImportError as e:
            logger.warning(f"google-genai SDK not installed: {e}")
            raise GeminiSearchProviderError(
                "google-genai package required. Install with: pip install google-genai"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Search client: {e}")
            raise GeminiSearchProviderError(f"Failed to initialize client: {e}")

    def is_available(self) -> bool:
        """Check if the provider is available."""
        return self._available

    async def search(self, query: str, limit: int = 5) -> List[GroundingSource]:
        """
        Perform a basic web search (via Grounding).
        
        Gemini doesn't provide a raw "search link" API directly in the same way as DDG,
        but we can ask it to "find sources about X" and parse the grounding metadata.
        """
        if not self._client:
            raise GeminiSearchProviderError("Client not initialized")
            
        try:
            # We use the research method but only extract sources
            response = await self.research(query)
            return response.sources[:limit]
            
        except Exception as e:
            logger.error(f"Gemini search error: {e}")
            return []

    async def research(self, topic: str) -> GroundedResponse:
        """
        Generate a response with full grounding metadata.
        """
        if not self._client:
            raise GeminiSearchProviderError("Client not initialized")
            
        try:
            types = self._types
            
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,  # Lower temp for factual research
                top_p=0.9,
            )
            
            # Helper to run in thread
            def _generate():
                return self._client.models.generate_content(
                    model=self._model_name,
                    contents=topic,
                    config=config,
                )
            
            response = await asyncio.wait_for(
                asyncio.to_thread(_generate),
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            
            text = response.text or ""
            search_queries: List[str] = []
            sources: List[GroundingSource] = []
            
            # Extract grounding metadata
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    metadata = candidate.grounding_metadata
                    
                    # Get search queries
                    if hasattr(metadata, 'web_search_queries'):
                        search_queries = list(metadata.web_search_queries or [])
                    
                    # Get grounding chunks (sources)
                    if hasattr(metadata, 'grounding_chunks'):
                        for chunk in (metadata.grounding_chunks or []):
                            if hasattr(chunk, 'web') and chunk.web:
                                sources.append(GroundingSource(
                                    title=getattr(chunk.web, 'title', 'Unknown'),
                                    url=getattr(chunk.web, 'uri', ''),
                                    snippet=None # Gemini doesn't always provide snippet in chunks
                                ))
            
            return GroundedResponse(
                text=text,
                search_queries=search_queries,
                sources=sources
            )
            
        except asyncio.TimeoutError:
            raise GeminiSearchProviderError(f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s")
        except Exception as e:
            logger.error(f"Gemini Search error: {e}")
            raise GeminiSearchProviderError(f"Generation failed: {e}")
