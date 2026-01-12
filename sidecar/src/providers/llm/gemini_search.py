"""
Gemini LLM Provider with Google Search Grounding.

Uses the new google-genai SDK to enable web search grounding,
allowing the model to access real-time information from the web
and provide cited, factual responses.

Use cases for interview prep:
- Research company news and recent developments
- Look up interviewer backgrounds
- Find industry trends and statistics
- Get current information about technologies
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..base import LLMProvider

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 90  # Longer timeout for web search


@dataclass
class GroundingSource:
    """A source used for grounding the response."""
    title: str
    url: str
    
    
@dataclass  
class GroundedResponse:
    """Response with grounding metadata."""
    text: str
    search_queries: List[str]
    sources: List[GroundingSource]


class GeminiSearchProviderError(Exception):
    """Exception raised when Gemini Search provider operations fail."""
    pass


class GeminiSearchProvider(LLMProvider):
    """
    LLM provider using Google Gemini with web search grounding.
    
    This provider uses the new google-genai SDK to enable Google Search
    as a grounding tool, allowing the model to:
    - Access real-time web information
    - Provide cited sources for claims
    - Reduce hallucinations with factual grounding
    
    Best used for:
    - Company research ("What are the latest news about [company]?")
    - Interviewer research ("Find information about [person] at [company]")
    - Industry trends ("What are current trends in [field]?")
    - Technology updates ("What's new in [technology] in 2026?")
    
    Usage:
        provider = GeminiSearchProvider(api_key="...")
        async for chunk in provider.generate_response(prompt, context, history):
            print(chunk, end="")
            
        # Or get grounded response with sources:
        response = await provider.generate_grounded_response(query)
        print(response.text)
        print("Sources:", response.sources)
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        Initialize Gemini Search provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-2.5-flash)

        Raises:
            ValueError: If API key is empty
            GeminiSearchProviderError: If client initialization fails
        """
        super().__init__()
        
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._model_name = model_name or self.DEFAULT_MODEL
        self._available = False
        self._client = None

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

    async def generate_response(
        self,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response with web search grounding.

        Args:
            prompt: The user query
            context: Additional context (combined with web search results)
            history: Conversation history

        Yields:
            String chunks of the response

        Raises:
            GeminiSearchProviderError: If generation fails
        """
        if not self._client:
            raise GeminiSearchProviderError("Client not initialized")
            
        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, context, history)
        
        try:
            types = self._types
            
            # Create config with Google Search tool
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.4,
                top_p=0.9,
            )
            
            # Generate with streaming
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.models.generate_content,
                    model=self._model_name,
                    contents=full_prompt,
                    config=config,
                ),
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            
            # For non-streaming, yield the full text
            if response.text:
                yield response.text
                
            # Log grounding metadata if available
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, 'web_search_queries'):
                        logger.info(f"Search queries: {metadata.web_search_queries}")
                    
        except asyncio.TimeoutError:
            logger.error(f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s")
            raise GeminiSearchProviderError(f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s")
        except Exception as e:
            logger.error(f"Gemini Search error: {e}")
            raise GeminiSearchProviderError(f"Generation failed: {e}")

    async def generate_grounded_response(
        self,
        query: str,
        include_sources: bool = True
    ) -> GroundedResponse:
        """
        Generate a response with full grounding metadata.
        
        This method returns structured data including the search queries
        performed and the sources used for grounding.
        
        Args:
            query: The search/research query
            include_sources: Whether to extract source metadata
            
        Returns:
            GroundedResponse with text, search queries, and sources
            
        Raises:
            GeminiSearchProviderError: If generation fails
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
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.models.generate_content,
                    model=self._model_name,
                    contents=query,
                    config=config,
                ),
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            
            text = response.text or ""
            search_queries: List[str] = []
            sources: List[GroundingSource] = []
            
            # Extract grounding metadata
            if include_sources and hasattr(response, 'candidates') and response.candidates:
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
                                    url=getattr(chunk.web, 'uri', '')
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

    def _build_prompt(
        self,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> str:
        """Build the full prompt with context and history."""
        parts = []
        
        # System instruction
        parts.append(
            "You are a research assistant helping with interview preparation. "
            "Use Google Search to find accurate, up-to-date information. "
            "Always cite your sources when making factual claims."
        )
        
        if context:
            parts.append(f"\n## Additional Context:\n{context}")
        
        if history:
            parts.append("\n## Conversation History:")
            for msg in history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    parts.append(f"{role}: {content}")
        
        parts.append(f"\n## Query:\n{prompt}")
        
        return "\n".join(parts)

    async def research_company(self, company_name: str) -> GroundedResponse:
        """
        Research a company for interview preparation.
        
        Args:
            company_name: Name of the company to research
            
        Returns:
            GroundedResponse with company information and sources
        """
        query = f"""Research {company_name} for a job interview. Include:
1. Recent news and developments (last 6 months)
2. Company mission, values, and culture
3. Key products or services
4. Recent funding, acquisitions, or major announcements
5. Leadership team changes
6. Technology stack or engineering practices (if tech company)

Provide a concise summary with the most relevant information for interview preparation."""
        
        return await self.generate_grounded_response(query)

    async def research_interviewer(
        self, 
        name: str, 
        company: str,
        role: Optional[str] = None
    ) -> GroundedResponse:
        """
        Research an interviewer for interview preparation.
        
        Args:
            name: Interviewer's name
            company: Company they work at
            role: Their role/title (optional)
            
        Returns:
            GroundedResponse with interviewer information and sources
        """
        role_info = f" ({role})" if role else ""
        query = f"""Research {name}{role_info} at {company}. Find:
1. Professional background and career history
2. LinkedIn profile summary or bio
3. Areas of expertise or focus
4. Any public talks, articles, or interviews
5. Technical interests or specializations

Provide information that would help prepare for an interview with this person."""
        
        return await self.generate_grounded_response(query)

    async def research_industry_trends(self, topic: str) -> GroundedResponse:
        """
        Research industry trends related to a topic.
        
        Args:
            topic: The technology, industry, or topic to research
            
        Returns:
            GroundedResponse with trend information and sources
        """
        query = f"""Research current trends and developments in {topic} as of 2026. Include:
1. Major recent developments and breakthroughs
2. Industry adoption and growth trends
3. Key players and competitors
4. Challenges and opportunities
5. Future outlook and predictions

Provide concise, factual information with specific examples and statistics where available."""
        
        return await self.generate_grounded_response(query)
