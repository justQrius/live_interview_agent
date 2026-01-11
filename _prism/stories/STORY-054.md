# STORY-054: Document Summarizer

**Phase**: 4A - Persistent Memory
**Priority**: High
**Effort**: 1 day
**Dependencies**: STORY-053 (Memory Store)

---

## User Story

As a system, I need to generate hierarchical summaries of uploaded documents, so that the LLM has a compressed understanding of the user's complete background.

---

## Acceptance Criteria

### AC-1: Document-Level Summary
- [ ] Generate ~200 word summary for entire document
- [ ] Summary captures key themes and highlights
- [ ] Works for all document types (resume, JD, company info)

### AC-2: Section-Level Summaries
- [ ] Detect sections within document (experience, education, requirements, etc.)
- [ ] Generate ~50 word summary per section
- [ ] Section detection uses existing patterns from `enhanced_manager.py`

### AC-3: Key Points Extraction
- [ ] Extract 5-10 bullet points from each document
- [ ] Points are factual, not interpretive
- [ ] Points include metrics where available

### AC-4: LLM Integration
- [ ] Use existing LLM provider infrastructure
- [ ] Single LLM call with structured output prompt
- [ ] Fallback to basic extraction if LLM unavailable
- [ ] Latency < 10 seconds per document

### AC-5: Storage Integration
- [ ] Summaries saved to Memory Store on generation
- [ ] Summaries cached - regenerate only on document re-upload
- [ ] `get_all_summaries()` returns all document summaries

---

## Technical Notes

```python
# File: sidecar/src/extraction/summarizer.py

SUMMARIZER_PROMPT = """Analyze this {document_type} document and provide:

1. DOCUMENT_SUMMARY: A 200-word summary capturing the key themes
2. SECTIONS: For each detected section, provide a 50-word summary
3. KEY_POINTS: 5-10 factual bullet points with metrics where available

Document:
{document_text}

Respond in JSON format:
{{
  "document_summary": "...",
  "sections": {{"section_name": "summary", ...}},
  "key_points": ["point 1", "point 2", ...]
}}
"""

class DocumentSummarizer:
    def __init__(self, llm_provider: LLMProvider, memory_store: MemoryStore):
        self.llm = llm_provider
        self.store = memory_store
    
    async def summarize(self, doc_id: str, text: str, doc_type: DocumentType) -> DocumentSummary:
        prompt = SUMMARIZER_PROMPT.format(
            document_type=doc_type.value,
            document_text=text[:15000]  # Limit to ~4k tokens
        )
        # ... LLM call and parsing
```

---

## Test Cases

1. **test_resume_summary**: Summarize resume, verify experience/skills captured
2. **test_jd_summary**: Summarize JD, verify requirements extracted
3. **test_section_detection**: Verify correct sections identified
4. **test_key_points_extraction**: Verify 5-10 points with metrics
5. **test_caching**: Second call returns cached, no LLM call
6. **test_fallback**: When LLM unavailable, basic extraction works

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests with mocked LLM provider
- [ ] Integration test with real LLM call
- [ ] Latency benchmark < 10s
- [ ] Code reviewed
