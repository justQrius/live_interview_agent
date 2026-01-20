"""
Story Recall Engine - Matches behavioral questions to STAR stories.

Matches detected questions to relevant STAR stories from the candidate's resume
using embedding similarity.

Part of Phase 4E: Interview Coaching (STORY-066)
"""

import logging
import asyncio
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.memory.store import MemoryStore
from src.memory.models import STARStory
from src.rag.store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class StoryMatch:
    """Represents a matched story with relevance context."""
    story: STARStory
    relevance_score: float
    suggested_opening: str
    key_metrics: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "storyId": self.story.id,
            "title": self.story.title,
            "situation": self.story.situation,
            "relevanceScore": self.relevance_score,
            "suggestedOpening": self.suggested_opening,
            "keyMetrics": self.key_metrics,
            "tags": self.story.tags
        }


class StoryRecaller:
    """
    Recalls relevant stories for behavioral questions.
    """
    
    SIMILARITY_THRESHOLD = 0.65
    
    def __init__(self, memory_store: MemoryStore, vector_store: VectorStore):
        """
        Initialize the StoryRecaller.
        
        Args:
            memory_store: Store containing STAR stories
            vector_store: Store for generating embeddings
        """
        self.memory_store = memory_store
        self.vector_store = vector_store
        self.story_embeddings: Dict[str, List[float]] = {}
        self._is_warmed_up = False
        
    async def warm_up(self) -> None:
        """
        Pre-compute embeddings for all stories at session start.
        """
        if self._is_warmed_up:
            return
            
        stories = self.memory_store.get_all_stories()
        if not stories:
            logger.info("No stories found to warm up")
            self._is_warmed_up = True
            return
            
        logger.info(f"Warming up embeddings for {len(stories)} stories")
        
        # Collect all texts for batch embedding
        story_texts = []
        story_ids = []
        
        for story in stories:
            # Create rich representation for embedding
            # Combine title, situation, tags, and action for semantic matching
            text = f"{story.title}. {story.situation}. {story.action}. Tags: {', '.join(story.tags)}"
            story_texts.append(text)
            story_ids.append(story.id)
            
        # Run batch embedding in executor to avoid blocking
        loop = asyncio.get_running_loop()
        
        try:
            # Batch size of 100 is reasonable for most embedding APIs
            BATCH_SIZE = 100
            total_embeddings = []
            
            for i in range(0, len(story_texts), BATCH_SIZE):
                batch_texts = story_texts[i:i + BATCH_SIZE]
                batch_embeddings = await loop.run_in_executor(
                    None, 
                    lambda t=batch_texts: self.vector_store.embed_queries(t)
                )
                total_embeddings.extend(batch_embeddings)
                
                # Small yield to let other tasks run during heavy processing
                await asyncio.sleep(0.01)
            
            # Map embeddings back to IDs
            for i, embedding in enumerate(total_embeddings):
                if embedding and len(embedding) > 0:
                    self.story_embeddings[story_ids[i]] = embedding
                    
        except Exception as e:
            logger.error(f"Failed to batch embed stories: {e}")
                
        self._is_warmed_up = True
        logger.info(f"Warmed up {len(self.story_embeddings)} story embeddings")
        
    async def find_relevant_story(
        self,
        question: str,
        question_type: str = "behavioral"
    ) -> Optional[StoryMatch]:
        """
        Find the most relevant story for a given question.
        
        Args:
            question: The interview question
            question_type: Classification of the question
            
        Returns:
            Best StoryMatch or None if no match meets threshold
        """
        # Only relevant for behavioral questions (or general ones that might be behavioral)
        if question_type not in ("behavioral", "interview_question"):
            return None
            
        if not self._is_warmed_up:
            await self.warm_up()
            
        if not self.story_embeddings:
            return None
            
        # Embed question
        loop = asyncio.get_running_loop()
        try:
            question_embedding = await loop.run_in_executor(
                None,
                lambda: self.vector_store.embed_query(question)
            )
        except Exception as e:
            logger.error(f"Failed to embed question for story recall: {e}")
            return None
            
        if question_embedding is None or len(question_embedding) == 0:
            return None
            
        # Find best match
        best_story_id = None
        best_score = -1.0
        
        for story_id, story_emb in self.story_embeddings.items():
            score = self._cosine_similarity(question_embedding, story_emb)
            if score > best_score:
                best_score = score
                best_story_id = story_id
                
        if best_story_id and best_score >= self.SIMILARITY_THRESHOLD:
            story = self.memory_store.get_story(best_story_id)
            if story:
                logger.info(f"Found relevant story: {story.title} (score={best_score:.2f})")
                return StoryMatch(
                    story=story,
                    relevance_score=best_score,
                    suggested_opening=story.opening_line or self._generate_fallback_opening(story),
                    key_metrics=story.metrics[:3]
                )
                
        return None
        
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity."""
        if vec1 is None or vec2 is None:
            return 0.0
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0
            
        a = np.array(vec1)
        b = np.array(vec2)
        
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return np.dot(a, b) / (norm_a * norm_b)
        
    def _generate_fallback_opening(self, story: STARStory) -> str:
        """Generate a generic opening line if none exists."""
        if story.source_company:
            return f"When I was at {story.source_company}, I encountered a situation..."
        return "I have a relevant experience where..."
