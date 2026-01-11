"""
Tests for Speculative Retrieval (STORY-064).

Tests clause detection, caching logic, and similarity validation.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.rag.speculative import SpeculativeRetriever
from src.rag.retrieval import RetrievalResult, ConfidenceLevel

@pytest.fixture
def mock_rag_engine():
    rag = MagicMock()
    rag.vector_store = MagicMock()
    # Mock retrieve to return a list
    rag.retrieve.return_value = [
        RetrievalResult(text="Chunk 1", distance=0.1, confidence=ConfidenceLevel.HIGH, metadata={})
    ]
    # Mock embed_query
    rag.vector_store.embed_query.return_value = [0.1, 0.2, 0.3]
    return rag

@pytest.mark.asyncio
async def test_clause_detection_trigger(mock_rag_engine):
    """Test that complete clauses trigger retrieval."""
    retriever = SpeculativeRetriever(mock_rag_engine)
    
    # Too short - no trigger
    await retriever.on_interim_transcript("Hello world")
    assert retriever._pending_task is None
    
    # Long enough + clause end - trigger
    await retriever.on_interim_transcript("When I was working at Google,")
    assert retriever._pending_task is not None
    
    # Wait for task to ensure it called retrieve
    await retriever._pending_task
    mock_rag_engine.retrieve.assert_called_with("When I was working at Google,", limit=5)

@pytest.mark.asyncio
async def test_cache_hit(mock_rag_engine):
    """Test that similar final query uses cached results."""
    retriever = SpeculativeRetriever(mock_rag_engine)
    
    # Trigger speculative
    query = "Tell me about your experience with Python,"
    await retriever.on_interim_transcript(query)
    await retriever._pending_task
    
    # Reset mock to verify we don't call it again
    mock_rag_engine.retrieve.reset_mock()
    
    # Mock embedding to be identical (simulating similarity)
    mock_rag_engine.vector_store.embed_query.return_value = [0.1, 0.2, 0.3]
    
    # Finalize with slightly different text but same embedding (mocked)
    final_query = "Tell me about your experience with Python."
    results = await retriever.on_segment_complete(final_query)
    
    # Should use cache, so retrieve NOT called again
    mock_rag_engine.retrieve.assert_not_called()
    assert len(results) == 1
    assert results[0].text == "Chunk 1"

@pytest.mark.asyncio
async def test_cache_miss_refetch(mock_rag_engine):
    """Test that different final query triggers fresh retrieval."""
    retriever = SpeculativeRetriever(mock_rag_engine)
    
    # Trigger speculative
    await retriever.on_interim_transcript("When I worked at Google,")
    await retriever._pending_task
    
    mock_rag_engine.retrieve.reset_mock()
    
    # Mock embedding to be different (orthogonal vector)
    # Original was [0.1, 0.2, 0.3]
    # New one [0.5, -0.5, 0.0] -> dot product small
    def side_effect(text):
        if "Google" in text:
            return [0.1, 0.2, 0.3]
        return [0.9, -0.9, 0.0]
    
    mock_rag_engine.vector_store.embed_query.side_effect = side_effect
    
    # Finalize with totally different text
    final_query = "What is your weakness?"
    await retriever.on_segment_complete(final_query)
    
    # Should call retrieve again
    mock_rag_engine.retrieve.assert_called_with(final_query, limit=5)

@pytest.mark.asyncio
async def test_reset_clears_state(mock_rag_engine):
    """Test that reset clears pending tasks and cache."""
    retriever = SpeculativeRetriever(mock_rag_engine)
    
    await retriever.on_interim_transcript("This is a long enough clause,")
    assert retriever._pending_task is not None
    
    retriever.reset()
    assert retriever._pending_task is None
    assert retriever._cached_results is None
