"""
Tests for Story Recall Engine (STORY-066).

Tests matching of behavioral questions to STAR stories using embeddings.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.coaching.story_recaller import StoryRecaller, StoryMatch
from src.memory.models import STARStory

@pytest.fixture
def mock_memory_store():
    store = MagicMock()
    # Setup some dummy stories
    store.get_all_stories.return_value = [
        STARStory(
            id="s1",
            title="Migration Project",
            situation="Legacy DB was slow",
            task="Migrate to Postgres",
            action="Wrote migration scripts",
            result="10x faster",
            metrics=["10x speedup"],
            tags=["technical", "migration"],
            opening_line="I led a migration project..."
        ),
        STARStory(
            id="s2",
            title="Conflict Resolution",
            situation="Team member conflict",
            task="Resolve it",
            action="Had 1:1s",
            result="Team aligned",
            tags=["behavioral", "conflict"],
            opening_line="I handled a conflict..."
        )
    ]
    # Allow getting by ID
    def get_story(sid):
        for s in store.get_all_stories.return_value:
            if s.id == sid:
                return s
        return None
    store.get_story.side_effect = get_story
    return store

@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    # Mock embed_query to return simple vectors we can control
    # [1, 0, 0] orthogonal to [0, 1, 0]
    def embed(text):
        if "Migration" in text or "technical" in text or "Postgres" in text:
            return [1.0, 0.0, 0.0]
        if "Conflict" in text or "behavioral" in text or "aligned" in text:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0] # Unrelated
    
    # Mock batch embedding (used by warm_up)
    def embed_batch(texts):
        return [embed(t) for t in texts]
    
    store.embed_query.side_effect = embed
    store.embed_queries.side_effect = embed_batch
    return store

@pytest.mark.asyncio
async def test_warm_up(mock_memory_store, mock_vector_store):
    """Test that warm_up generates embeddings for all stories."""
    recaller = StoryRecaller(mock_memory_store, mock_vector_store)
    
    await recaller.warm_up()
    
    assert len(recaller.story_embeddings) == 2
    assert "s1" in recaller.story_embeddings
    assert "s2" in recaller.story_embeddings
    assert recaller._is_warmed_up

@pytest.mark.asyncio
async def test_find_relevant_story_match(mock_memory_store, mock_vector_store):
    """Test matching a question to a relevant story."""
    recaller = StoryRecaller(mock_memory_store, mock_vector_store)
    await recaller.warm_up()
    
    # Question matching "Migration" story
    question = "Tell me about a technical migration."
    match = await recaller.find_relevant_story(question, "behavioral")
    
    assert match is not None
    assert match.story.id == "s1"
    assert match.relevance_score > 0.9 # Should be perfect match [1,0,0] vs [1,0,0]

@pytest.mark.asyncio
async def test_find_relevant_story_no_match(mock_memory_store, mock_vector_store):
    """Test that unrelated question yields no match (below threshold)."""
    recaller = StoryRecaller(mock_memory_store, mock_vector_store)
    await recaller.warm_up()
    
    # Question matching neither (returns [0,0,1])
    question = "What is your favorite color?"
    match = await recaller.find_relevant_story(question, "behavioral")
    
    # [0,0,1] vs [1,0,0] and [0,1,0] -> similarity 0
    assert match is None

@pytest.mark.asyncio
async def test_skip_non_behavioral(mock_memory_store, mock_vector_store):
    """Test that non-behavioral questions are skipped."""
    recaller = StoryRecaller(mock_memory_store, mock_vector_store)
    
    # Even if text matches perfectly
    question = "Tell me about a technical migration."
    match = await recaller.find_relevant_story(question, "technical") # Wrong type
    
    assert match is None
