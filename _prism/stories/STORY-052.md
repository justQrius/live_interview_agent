# STORY-052: End-to-End Testing

**Phase**: 3C (Conversational Intelligence)
**Priority**: P1 - Must Have
**Effort**: 1 day
**Dependencies**: STORY-051

## Description

Create comprehensive end-to-end tests for all Phase 3 functionality. Tests should verify the complete flow from audio input through answer generation and persistence.

## Acceptance Criteria

- [ ] E2E tests for question detection accuracy
- [ ] E2E tests for follow-up question handling
- [ ] E2E tests for compound question splitting
- [ ] E2E tests for multi-document context retrieval
- [ ] E2E tests for session persistence and retrieval
- [ ] Performance benchmarks for latency
- [ ] Test coverage >80% for Phase 3 code

## Technical Details

### Test File Location
```
sidecar/tests/
├── test_phase3_e2e.py          # New
├── test_question_detector.py    # New
├── test_query_reformulator.py   # New
├── test_question_splitter.py    # New
├── test_session_store.py        # New
└── test_enhanced_rag.py         # New
```

### E2E Test Scenarios

```python
# sidecar/tests/test_phase3_e2e.py

class TestPhase3EndToEnd:
    """End-to-end tests for Phase 3 functionality."""
    
    @pytest.fixture
    async def server_with_context(self):
        """Server with resume and JD uploaded."""
        server = SidecarServer()
        # Upload test documents
        await server.context_manager.process_file(
            "resume.pdf", SAMPLE_RESUME_B64, DocumentType.RESUME
        )
        await server.context_manager.process_file(
            "job.txt", SAMPLE_JD_B64, DocumentType.JOB_DESCRIPTION
        )
        return server
    
    async def test_question_triggers_answer(self, server_with_context):
        """Question detection correctly triggers answer generation."""
        # Simulate interviewer question
        segment = SpeechSegment(
            audio=MOCK_AUDIO,
            text="Tell me about your experience with Python."
        )
        
        await server_with_context._process_speech_segment(segment)
        
        # Verify answer was generated
        assert len(server_with_context.broadcast_messages) > 0
        assert any(m.type == MessageType.ANSWER_CHUNK for m in messages)
    
    async def test_statement_skipped(self, server_with_context):
        """Statements don't trigger answer generation."""
        segment = SpeechSegment(
            audio=MOCK_AUDIO,
            text="That's very interesting, thank you."
        )
        
        await server_with_context._process_speech_segment(segment)
        
        # Verify no answer chunks
        assert not any(m.type == MessageType.ANSWER_CHUNK for m in messages)
    
    async def test_followup_reformulated(self, server_with_context):
        """Follow-up questions are reformulated correctly."""
        # First question
        await process("Tell me about your Python experience")
        
        # Follow-up
        await process("What about testing?")
        
        # Verify context was used
        rag_calls = server_with_context.enhanced_rag.retrieve_calls
        assert "Python" in rag_calls[-1] or "testing" in rag_calls[-1]
    
    async def test_compound_question_split(self, server_with_context):
        """Compound questions are split and all parts addressed."""
        await process("What's your Python experience and how do you handle testing?")
        
        # Verify both topics in retrieved context
        retrieved = server_with_context.enhanced_rag.last_retrieved
        assert any("Python" in chunk for chunk in retrieved)
        # Answer should address both
    
    async def test_session_persisted(self, server_with_context):
        """Session data is correctly persisted."""
        # Start session
        await server_with_context._handle_start_session(...)
        session_id = server_with_context.session_state.persistent_session_id
        
        # Process some questions
        await process("Tell me about yourself")
        await process("What's your greatest strength?")
        
        # End session
        await server_with_context._handle_stop_session(...)
        
        # Verify persisted
        session = server_with_context.session_store.get_session(session_id)
        assert session is not None
        assert len(session.transcriptions) >= 2
        assert len(session.answers) >= 2
```

### Performance Benchmarks

```python
class TestPhase3Performance:
    """Performance benchmarks for Phase 3 components."""
    
    async def test_question_detection_latency(self):
        """Question detection < 10ms P95."""
        detector = QuestionDetector()
        
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            detector.is_actionable_question("Tell me about yourself", [])
            latencies.append((time.perf_counter() - start) * 1000)
        
        p95 = np.percentile(latencies, 95)
        assert p95 < 10, f"P95 latency {p95:.2f}ms exceeds 10ms target"
    
    async def test_full_pipeline_latency(self, server_with_context):
        """Full pipeline < 2s P95 (excluding LLM)."""
        # Mock LLM to remove external dependency
        with mock.patch.object(server, 'llm'):
            # Measure pipeline latency
            pass
```

## Definition of Done

- [ ] All E2E test scenarios implemented
- [ ] Performance benchmarks passing
- [ ] Test coverage >80%
- [ ] CI integration configured
- [ ] Test documentation complete
