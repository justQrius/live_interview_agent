"""
DuckDuckGo Search Provider.

Implements SearchProvider interface using the duckduckgo-search package.
Provides privacy-focused web search without API keys.
"""

import logging
from typing import List, Optional, Any

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
    - Optional LLM synthesis for grounded answers
    """
    
    def __init__(self, llm_provider: Optional[Any] = None):
        """
        Initialize DuckDuckGo search provider.
        
        Args:
            llm_provider: Optional LLM provider to synthesize search results.
        """
        if DDGS is None:
            raise ImportError(
                "duckduckgo-search package is not installed. "
                "Please install it with: pip install duckduckgo-search"
            )
        self._ddgs = DDGS()
        self.llm_provider = llm_provider

    def set_llm_provider(self, provider: Any) -> None:
        """Set the LLM provider for synthesis."""
        self.llm_provider = provider

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
                try:
                    for r in self._ddgs.text(query, max_results=limit):
                        results.append(GroundingSource(
                            title=r.get("title", ""),
                            url=r.get("href", ""),
                            snippet=r.get("body", "")
                        ))
                except Exception as e:
                    logger.error(f"DDGS internal error: {e}")
                return results

            return await asyncio.to_thread(_run_search)
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    async def research(self, topic: str) -> GroundedResponse:
        """
        Perform research on a topic.
        
        If an LLM provider is available, it synthesizes the search results
        into a coherent summary. Otherwise, it returns a list of snippets.
        """
        sources = await self.search(topic, limit=10)
        
        if not sources:
            return GroundedResponse(
                text=f"I couldn't find any information about '{topic}' using DuckDuckGo.",
                search_queries=[topic],
                sources=[]
            )

        # If we have an LLM, synthesize the answer
        if self.llm_provider:
            try:
                summary = await self._synthesize_results(topic, sources)
                return GroundedResponse(
                    text=summary,
                    search_queries=[topic],
                    sources=sources
                )
            except Exception as e:
                logger.error(f"LLM synthesis failed: {e}. Falling back to raw snippets.")
                # Fall through to snippet aggregation
        
        # Fallback: Create a simple aggregation of snippets
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

    async def _synthesize_results(self, topic: str, sources: List[GroundingSource]) -> str:
        """Synthesize search results into a concise summary using the LLM."""
        
        # Format sources for the prompt
        source_text = "\n\n".join(
            [f"Source {i+1}:\nTitle: {s.title}\nURL: {s.url}\nContent: {s.snippet}" 
             for i, s in enumerate(sources)]
        )
        
        prompt = f"""
You are a research assistant. Based ONLY on the following search results, provide a concise, factual summary about "{topic}".
Do not invent information. If the results are insufficient, state that clearly.
Cite sources using [Source X] format where appropriate.

SEARCH RESULTS:
{source_text}

SUMMARY:
"""
        
        # We need to collect the streaming response
        full_response = []
        async for chunk in self.llm_provider.generate_response(prompt, "", []):
            full_response.append(chunk)
            
        return "".join(full_response)
