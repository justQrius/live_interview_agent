# STORY-066: Story Recall Engine

**Phase**: 4E - Interview Coaching
**Priority**: High
**Effort**: 1 day
**Dependencies**: STORY-056 (Story Extractor)

---

## User Story

As a user, when a behavioral question is detected, I want to immediately see the most relevant STAR story from my resume, so that I can use it in my answer.

---

## Acceptance Criteria

### AC-1: Story Matching
- [ ] Match detected question to relevant STAR story
- [ ] Use embedding similarity for matching
- [ ] Threshold for minimum relevance (0.6)
- [ ] Return best match with relevance score

### AC-2: Display Content
- [ ] Story title
- [ ] Situation summary (2-3 sentences)
- [ ] Key metrics from the story
- [ ] Suggested opening line

### AC-3: Performance
- [ ] Story surfaced within 1 second of question detection
- [ ] Pre-compute story embeddings at session start
- [ ] Low latency similarity search

### AC-4: UI Integration
- [ ] New "Suggested Story" panel in answer display
- [ ] Prominently visible alongside generated answer
- [ ] Collapsible for more detail

---

## Technical Notes

```python
# File: sidecar/src/coaching/story_recaller.py

class StoryRecaller:
    def __init__(self, memory_store: MemoryStore, embedder):
        self.store = memory_store
        self.embedder = embedder
        self.story_embeddings: Dict[str, List[float]] = {}
    
    async def warm_up(self):
        """Pre-compute story embeddings at session start"""
        stories = self.store.get_all_stories()
        for story in stories:
            embedding_text = f"{story.title} {story.situation} {' '.join(story.tags)}"
            self.story_embeddings[story.id] = await self.embedder.embed_async(embedding_text)
    
    async def find_relevant_story(
        self,
        question: str,
        question_type: str
    ) -> Optional[StoryMatch]:
        """Find best matching story for behavioral question"""
        
        if question_type != "behavioral":
            return None
        
        question_embedding = await self.embedder.embed_async(question)
        
        best_story = None
        best_score = 0.0
        
        for story_id, story_embedding in self.story_embeddings.items():
            score = self._cosine_similarity(question_embedding, story_embedding)
            if score > best_score:
                best_score = score
                best_story = self.store.get_story(story_id)
        
        if best_story and best_score >= 0.6:
            return StoryMatch(
                story=best_story,
                relevance_score=best_score,
                suggested_opening=best_story.opening_line,
                key_metrics=best_story.metrics[:3]
            )
        
        return None
```

```typescript
// Message type
{ 
  type: "STORY_SUGGESTION", 
  data: { 
    title: "The Migration Crisis",
    situation: "At Acme Corp in Q3 2022...",
    metrics: ["40% latency reduction", "zero downtime"],
    opening_line: "At my previous role, I led an 8-person team...",
    relevance: 0.85
  } 
}
```

---

## Test Cases

1. **test_behavioral_matching**: Behavioral Q gets story match
2. **test_non_behavioral_skip**: Technical Q returns no story
3. **test_relevance_threshold**: Low-relevance stories not returned
4. **test_latency**: < 1 second from question to suggestion
5. **test_warm_up**: Pre-computation works at session start
6. **test_empty_story_bank**: Graceful handling with no stories

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Latency benchmark passing
- [ ] UI panel implemented
- [ ] Integration with question detection pipeline
- [ ] Code reviewed
