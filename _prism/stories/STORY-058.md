# STORY-058: Extraction Pipeline Integration

**Phase**: 4A - Persistent Memory
**Priority**: High
**Effort**: 0.5 days
**Dependencies**: STORY-053 through STORY-057

---

## User Story

As a user, when I upload documents, I want the system to automatically extract and store all relevant information, so that I'm ready for interview preparation.

---

## Acceptance Criteria

### AC-1: Automatic Extraction on Upload
- [ ] Document upload triggers extraction pipeline
- [ ] Pipeline runs: Parse → Summarize → Extract Facts → Extract Stories → Generate Profile
- [ ] User sees progress indicator during extraction
- [ ] Extraction completes within 30 seconds for typical document

### AC-2: Incremental Updates
- [ ] New document adds to existing facts (doesn't replace)
- [ ] Duplicate documents detected and skipped
- [ ] Profile regenerated after new extraction

### AC-3: Error Handling
- [ ] Partial extraction saved if pipeline fails midway
- [ ] User notified of extraction errors
- [ ] Graceful degradation - existing chunks still work

### AC-4: UI Feedback
- [ ] New message type: `EXTRACTION_PROGRESS` with step and percentage
- [ ] New message type: `EXTRACTION_COMPLETE` with summary
- [ ] UI shows extraction status

### AC-5: WebSocket Integration
- [ ] `_handle_upload_context` calls extraction pipeline
- [ ] Non-blocking - upload acknowledged before extraction complete
- [ ] Extraction runs in background task

---

## Technical Notes

```python
# File: sidecar/src/extraction/__init__.py

class ExtractionPipeline:
    def __init__(self, llm: LLMProvider, memory: MemoryStore):
        self.summarizer = DocumentSummarizer(llm, memory)
        self.fact_extractor = FactExtractor(llm, memory)
        self.story_extractor = StoryExtractor(llm, memory)
        self.profile_generator = ProfileGenerator(memory)
    
    async def process_document(
        self, 
        doc_id: str, 
        text: str, 
        doc_type: DocumentType,
        progress_callback: Callable[[str, float], None]
    ):
        progress_callback("summarizing", 0.2)
        summary = await self.summarizer.summarize(doc_id, text, doc_type)
        
        progress_callback("extracting_facts", 0.4)
        facts = await self.fact_extractor.extract(doc_id, text, doc_type)
        
        if doc_type == DocumentType.RESUME:
            progress_callback("extracting_stories", 0.6)
            stories = await self.story_extractor.extract(facts.achievements)
        
        progress_callback("generating_profile", 0.8)
        profile = self.profile_generator.generate(facts, [summary])
        
        progress_callback("complete", 1.0)
        return ExtractionResult(summary, facts, stories, profile)
```

---

## Test Cases

1. **test_full_pipeline**: Resume processes through all stages
2. **test_incremental**: Second document merges correctly
3. **test_progress_callbacks**: All stages report progress
4. **test_error_recovery**: Failure in one stage doesn't lose others
5. **test_websocket_integration**: Upload triggers extraction

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] End-to-end test with real document
- [ ] Progress shown in UI
- [ ] Latency < 30s for typical resume
- [ ] Code reviewed
