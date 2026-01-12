"""
Speculative Retrieval - Pre-fetch context during speech.

Handles speculative RAG retrieval based on interim transcripts or partial audio.
Triggers retrieval when a complete clause is detected or sufficient time has passed,
caching results to reduce latency when the final query is received.

Part of Phase 4D: Continuous-Feel Transcription (STORY-064)
"""

import asyncio
import logging
import re
import numpy as np
from typing import Optional, List, Dict, Any, Tuple

from .engine import RAGEngine
from .retrieval import RetrievalResult

logger = logging.getLogger(__name__)


class SpeculativeRetriever:
    """
    Manages speculative retrieval for ongoing speech segments.
    """
    
    # Config parameters
    CLAUSE_MIN_WORDS = 5
    QUERY_SIMILARITY_THRESHOLD = 0.85
    MIN_DURATION_SECONDS = 2.0
    
    def __init__(self, rag_engine: RAGEngine):
        """
        Initialize the speculative retriever.
        
        Args:
            rag_engine: RAG engine for retrieval
        """
        self.rag = rag_engine
        self.vector_store = rag_engine.vector_store
        
        # State
        self._pending_query: Optional[str] = None
        self._pending_embedding: Optional[List[float]] = None
        self._pending_task: Optional[asyncio.Task] = None
        self._cached_results: Optional[List[RetrievalResult]] = None
        self._last_trigger_text_len = 0
        
    def reset(self) -> None:
        """Reset state for new segment."""
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
            
        self._pending_query = None
        self._pending_embedding = None
        self._pending_task = None
        self._cached_results = None
        self._last_trigger_text_len = 0
        
    async def on_interim_transcript(self, text: str) -> None:
        """
        Process interim transcript text.
        
        Triggers speculative retrieval if conditions are met:
        1. Text contains a complete clause
        2. Sufficient length
        3. Significantly different from last trigger
        """
        if not text:
            return
            
        text = text.strip()
        words = text.split()
        
        # Check basic constraints
        if len(words) < self.CLAUSE_MIN_WORDS:
            return
            
        # Check if we already triggered on a similar prefix
        # Only trigger again if we added significant content (e.g. +5 words)
        if len(text) - self._last_trigger_text_len < 20:  # approx 4-5 words
            return
            
        # Check for clause boundaries
        if self._has_clause_end(text):
            logger.info(f"Speculative trigger: '{text[-30:]}...'")
            await self._trigger_retrieval(text)
            self._last_trigger_text_len = len(text)
            
    async def on_segment_complete(self, final_text: str) -> List[RetrievalResult]:
        """
        Called when segment is finalized. Returns context.
        
        Uses cached results if valid, otherwise triggers fresh retrieval.
        """
        # If we have a pending task, wait for it
        if self._pending_task:
            try:
                await self._pending_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning(f"Speculative task failed: {e}")
                self._cached_results = None
        
        # If no cache or no embedding to compare, plain fetch
        if not self._cached_results or not self._pending_embedding:
            logger.info("No speculative cache, performing fresh retrieval")
            return self.rag.retrieve(final_text, limit=5)
            
        # Validate cache using embedding similarity
        try:
            final_embedding = await self._embed_async(final_text)
            if not final_embedding:
                return self.rag.retrieve(final_text, limit=5)
                
            similarity = self._cosine_similarity(self._pending_embedding, final_embedding)
            
            if similarity >= self.QUERY_SIMILARITY_THRESHOLD:
                logger.info(f"Speculative cache HIT (similarity={similarity:.2f})")
                return self._cached_results
            else:
                logger.info(f"Speculative cache MISS (similarity={similarity:.2f})")
                return self.rag.retrieve(final_text, limit=5)
                
        except Exception as e:
            logger.error(f"Error validating speculative cache: {e}")
            return self.rag.retrieve(final_text, limit=5)
            
    async def _trigger_retrieval(self, query: str) -> None:
        """Start async retrieval task."""
        # Cancel existing task if running
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
            
        self._pending_query = query
        
        # Calculate embedding first (needed for later validation)
        self._pending_embedding = await self._embed_async(query)
        
        # Launch retrieval task
        self._pending_task = asyncio.create_task(self._retrieve_and_cache(query))
        
    async def _retrieve_and_cache(self, query: str) -> None:
        """Execute retrieval and store results."""
        try:
            # We use synchronous RAG retrieve in a thread/executor usually,
            # but RAGEngine.retrieve is synchronous.
            # We should run it in executor to avoid blocking loop.
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: self.rag.retrieve(query, limit=5)
            )
            self._cached_results = results
            # logger.debug(f"Speculative retrieval cached {len(results)} results")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Speculative retrieval failed: {e}")
            self._cached_results = None

    async def _embed_async(self, text: str) -> List[float]:
        """Embed text asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.vector_store.embed_query(text)
        )

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if vec1 is None or vec2 is None:
            return 0.0
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0
        
        a = np.array(vec1)
        b = np.array(vec2)
        
        if a.shape != b.shape:
            return 0.0
            
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return np.dot(a, b) / (norm_a * norm_b)

    def _has_clause_end(self, text: str) -> bool:
        """Check for clause-ending patterns."""
        # Punctuation
        if any(p in text[-5:] for p in ['.', ',', '?', '!', ';']):
            return True
            
        # Conjunctions (simple check)
        text_lower = text.lower()
        conjunctions = [' and ', ' but ', ' so ', ' because ', ' when ', ' if ']
        # Check if ends with a conjunction (unlikely) or just contains one recently?
        # Actually we want to detect if we *just finished* a clause.
        # "I was working on the project," -> Trigger
        # "I was working on the project and" -> Trigger? Maybe.
        
        # For now, rely mainly on punctuation or length if we assume interim results
        # from STT might imply pause/punctuation.
        # But raw STT often lacks punctuation until final.
        
        # Length-based fallback: Trigger every ~10 words?
        words = text.split()
        return len(words) >= 5  # Just basic length check + logic in on_interim_transcript
