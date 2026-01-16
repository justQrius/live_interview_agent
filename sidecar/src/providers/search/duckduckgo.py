"""
DuckDuckGo Search Provider.

Implements SearchProvider interface using the duckduckgo-search package.
Provides privacy-focused web search without API keys.
"""

import logging
from typing import List, Optional

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

from ..base import SearchProvider, GroundedResponse, GroundingSource

logger = logging.getLogger(__name__)

class DuckDuckGoSearchProvider(SearchProvider):
    """
    Search provider using DuckDuckGo.
    
    Features:
    - Free (no API key required)
    - Privacy-focused
    - Fast results
    """
    
    def __init__(self):
        """Initialize DuckDuckGo search provider."""
        if DDGS is None:
            raise ImportError(
                "duckduckgo-search package is not installed. "
                "Please install it with: pip install duckduckgo-search"
            )
        self._ddgs = DDGS()

    async def search(self, query: str, limit: int = 5) -> List[GroundingSource]:
        """
        Perform a basic web search.
        """
        try:
            # DDGS.text() is synchronous, so we should run it in an executor if possible,
            # but for simplicity/low-overhead we might call it directly or via asyncio.to_thread
            import asyncio
            
            def _run_search():
                results = []
                # ddgs.text returns an iterator/generator
                for r in self._ddgs.text(query, max_results=limit):
                    results.append(GroundingSource(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", "")
                    ))
                return results

            return await asyncio.to_thread(_run_search)
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    async def research(self, topic: str) -> GroundedResponse:
        """
        Perform research on a topic.
        
        Since DuckDuckGo is just a search engine (not an LLM), 
        this returns a structured response with the search results 
        but without a synthesized summary.
        """
        sources = await self.search(topic, limit=10)
        
        # Create a simple aggregation of snippets as the "text"
        # This ensures the UI displays something useful even without LLM synthesis
        summary_lines = [f"### Research Results for '{topic}'\n"]
        for i, source in enumerate(sources, 1):
            summary_lines.append(f"**{i}. {source.title}**")
            summary_lines.append(f"{source.snippet}")
            summary_lines.append(f"Source: {source.url}\n")
            
        text = "\n".join(summary_lines)
        
        return GroundedResponse(
            text=text,
            search_queries=[topic],
            sources=sources
        )
