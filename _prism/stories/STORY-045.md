# STORY-045: Enhanced RAG Engine

**Phase**: 3B (Enhanced Context)
**Priority**: P1 - Must Have
**Effort**: 1 day
**Dependencies**: STORY-044

## Description

Enhance the RAG engine to use question-type-aware retrieval and parent chunk expansion. Based on the question classification (behavioral, technical, motivation, etc.), prioritize different document types.

## Acceptance Criteria

- [ ] Create `EnhancedRAGEngine` with intelligent retrieval
- [ ] Map question types to document type priorities
- [ ] Retrieve child chunks, then expand to parent chunks
- [ ] Aggregate context from multiple sub-questions
- [ ] Maintain existing retrieval interface for compatibility
- [ ] Unit tests for all question type mappings

## Technical Details

### File Location
```
sidecar/src/rag/
├── engine.py          # Existing
├── enhanced_engine.py # New
├── store.py           # Existing (enhanced in STORY-044)
└── retrieval.py       # Existing
```

### Question Type to Document Priority

```python
DOC_PRIORITY_BY_QUESTION_TYPE = {
    "behavioral": [DocumentType.RESUME, DocumentType.SAMPLE_QA],
    "intro": [DocumentType.RESUME],
    "technical": [DocumentType.RESUME, DocumentType.JOB_DESCRIPTION],
    "motivation": [DocumentType.COMPANY_INFO, DocumentType.JOB_DESCRIPTION, DocumentType.INDUSTRY_RESEARCH],
    "weakness": [DocumentType.SAMPLE_QA, DocumentType.RESUME],
    "general": [DocumentType.RESUME, DocumentType.JOB_DESCRIPTION],
}
```

### Interface

```python
class EnhancedRAGEngine:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.parent_cache: Dict[str, str] = {}  # parent_id -> text
    
    def retrieve_for_question(
        self,
        question: str,
        question_type: str,
        sub_questions: List[str] = None,
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve context with question-type-aware filtering.
        
        1. Get document priorities for question type
        2. Query child chunks with type filter
        3. Expand to parent chunks for full context
        4. Aggregate across sub-questions if provided
        """
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE.get(
            question_type, 
            list(DocumentType)
        )
        
        all_results = []
        
        # Query each priority type
        for doc_type in priorities:
            results = self.vector_store.query_with_filter(
                question,
                n_results=limit // len(priorities),
                where={
                    "document_type": doc_type.value,
                    "level": "child"
                }
            )
            all_results.extend(results)
        
        # Expand to parent chunks
        expanded = self._expand_to_parents(all_results)
        
        # Re-rank by relevance
        return self._rerank(expanded, question)[:limit]
    
    def _expand_to_parents(
        self, 
        child_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Expand child chunks to their parent chunks."""
        parent_ids = set()
        for result in child_results:
            parent_id = result.metadata.get("parent_id")
            if parent_id:
                parent_ids.add(parent_id)
        
        # Fetch parent texts
        # Return parent chunks with aggregated child scores
```

## Test Cases

1. **Behavioral question**: "Tell me about a time..." → prioritizes resume
2. **Motivation question**: "Why this company?" → prioritizes company_info
3. **Technical question**: "How would you design..." → prioritizes resume + JD
4. **Parent expansion**: Child results expand to parent chunks
5. **Multi-question**: Multiple sub-questions aggregate context
6. **Missing type**: Unknown question type uses default priorities
7. **Empty results**: No matching chunks returns empty list

## Definition of Done

- [ ] EnhancedRAGEngine implemented
- [ ] All question type mappings working
- [ ] Parent expansion working
- [ ] Unit tests passing
- [ ] Integration with existing pipeline
