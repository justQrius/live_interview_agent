# STORY-064: Speculative Retrieval Pipeline

**Phase**: 4D - Continuous-Feel Transcription
**Priority**: Medium
**Effort**: 1 day
**Dependencies**: STORY-063 (Tier 3 Detection)

---

## User Story

As a system, I need to begin RAG retrieval before the transcription segment is finalized, so that answers appear faster after the interviewer stops speaking.

---

## Acceptance Criteria

### AC-1: Clause Detection
- [ ] Detect when first complete clause is transcribed
- [ ] Trigger speculative query formation at ~2 seconds into speech
- [ ] Handle partial/incomplete transcripts gracefully

### AC-2: Speculative Retrieval
- [ ] Form query from partial transcript
- [ ] Begin RAG retrieval before segment ends
- [ ] Cache speculative results

### AC-3: Result Validation
- [ ] When segment finalizes, check if query is still valid
- [ ] Use cached results if query didn't change significantly
- [ ] Re-fetch if query changed substantially

### AC-4: Performance
- [ ] Reduce perceived latency by ~500-1000ms
- [ ] No wasted API calls (speculative results used >80% of time)

---

## Technical Notes

```python
# File: sidecar/src/audio/speculative.py

class SpeculativeProcessor:
    CLAUSE_MIN_WORDS = 5
    QUERY_SIMILARITY_THRESHOLD = 0.8
    
    def __init__(self, rag_engine: RAGEngine, embedder):
        self.rag = rag_engine
        self.embedder = embedder
        self.pending_query: Optional[str] = None
        self.pending_task: Optional[asyncio.Task] = None
        self.pending_embedding: Optional[List[float]] = None
    
    async def on_interim_transcript(self, text: str):
        """Called with interim transcript updates"""
        words = text.split()
        
        # Check for complete clause
        if len(words) >= self.CLAUSE_MIN_WORDS and self._has_clause_end(text):
            # Form speculative query
            self.pending_query = self._form_query(text)
            self.pending_embedding = await self.embedder.embed_async(self.pending_query)
            
            # Start retrieval
            self.pending_task = asyncio.create_task(
                self.rag.retrieve(self.pending_query, limit=5)
            )
    
    async def on_segment_complete(self, final_text: str) -> List[RetrievalResult]:
        """Called when segment is finalized"""
        if not self.pending_task:
            # No speculation, fetch now
            return await self.rag.retrieve(final_text, limit=5)
        
        # Check if final query is similar to speculative
        final_embedding = await self.embedder.embed_async(final_text)
        similarity = self._cosine_similarity(self.pending_embedding, final_embedding)
        
        if similarity >= self.QUERY_SIMILARITY_THRESHOLD:
            # Use cached results
            return await self.pending_task
        else:
            # Query changed, cancel and re-fetch
            self.pending_task.cancel()
            return await self.rag.retrieve(final_text, limit=5)
    
    def _has_clause_end(self, text: str) -> bool:
        """Check for clause-ending patterns"""
        return any(p in text for p in [',', '.', '?', ' and ', ' but ', ' so '])
```

---

## Test Cases

1. **test_clause_detection**: Triggers at appropriate points
2. **test_speculative_start**: Retrieval starts early
3. **test_result_reuse**: Valid results reused
4. **test_result_refetch**: Changed queries fetch fresh
5. **test_latency_improvement**: Measure actual time savings
6. **test_no_wasted_calls**: >80% speculation hit rate

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Latency improvement measured
- [ ] Hit rate tracked
- [ ] Integration with audio pipeline
- [ ] Code reviewed
