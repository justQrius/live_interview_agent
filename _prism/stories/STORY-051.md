# STORY-051: Pipeline Integration

**Phase**: 3C (Conversational Intelligence)
**Priority**: P1 - Must Have
**Effort**: 1 day
**Dependencies**: STORY-049, STORY-050

## Description

Integrate all Phase 3 components into the main server pipeline. The complete flow: Speech → Question Detection → Query Reformulation → Question Splitting → Enhanced RAG → LLM → Persistence.

## Acceptance Criteria

- [ ] Integrate QuestionDetector into speech processing
- [ ] Integrate QueryReformulator for follow-up handling
- [ ] Integrate QuestionSplitter for compound questions
- [ ] Integrate EnhancedRAGEngine for intelligent retrieval
- [ ] Integrate SessionHistoryStore for persistence
- [ ] End-to-end flow working correctly
- [ ] Logging for debugging each stage

## Technical Details

### Complete Pipeline Flow

```python
async def _process_speech_segment(self, segment) -> None:
    """Enhanced speech processing with Phase 3 components."""
    import time
    pipeline_start = time.time()
    
    # 1. Speech-to-text (existing)
    audio_for_stt = self._apply_noise_reduction(segment.audio)
    speaker = self._identify_speaker(segment.audio)
    text = await self.stt.transcribe(audio_for_stt)
    
    if not text:
        return
    
    # 2. Broadcast transcription (existing)
    await self._broadcast_transcription(speaker, text, segment)
    
    # 3. Record to persistent storage (NEW)
    if self.session_state.persistent_session_id:
        self.session_store.add_transcription(
            self.session_state.persistent_session_id,
            speaker.value, text, segment.start_time
        )
    
    # 4. Question detection (NEW)
    if speaker == Speaker.INTERVIEWER:
        is_question, confidence, q_type = self.question_detector.is_actionable_question(
            text, self.session_state.conversation_history
        )
        
        logger.info(f"Detection: {q_type} ({confidence:.2f})")
        
        if not is_question or confidence < self.config.question_confidence_threshold:
            logger.info(f"Skipping non-question: {text[:50]}...")
            return
        
        # 5. Query reformulation (NEW)
        reformulated, was_reformulated = self.query_reformulator.reformulate_if_needed(
            text, self.session_state.conversation_history
        )
        if was_reformulated:
            logger.info(f"Reformulated: '{text}' → '{reformulated}'")
        
        # 6. Question splitting (NEW)
        sub_questions = self.question_splitter.split_questions(reformulated)
        if len(sub_questions) > 1:
            logger.info(f"Split into {len(sub_questions)} sub-questions")
        
        # 7. Enhanced RAG retrieval (NEW)
        context_chunks = self.enhanced_rag.retrieve_for_question(
            reformulated, q_type, sub_questions
        )
        
        # 8. Generate answer (existing, with enhancements)
        await self._generate_answer_with_persistence(
            original_question=text,
            reformulated_question=reformulated,
            context_chunks=context_chunks,
            pipeline_start=pipeline_start
        )

async def _generate_answer_with_persistence(self, **kwargs) -> None:
    """Generate answer and persist to session store."""
    # ... existing LLM generation
    
    # Record answer to persistent storage (NEW)
    if self.session_state.persistent_session_id:
        self.session_store.add_answer(
            session_id=self.session_state.persistent_session_id,
            question=kwargs['original_question'],
            answer=full_answer,
            confidence=rag_confidence.value,
            latency_ms=int(latency * 1000)
        )
```

### Initialization

```python
class SidecarServer:
    def __init__(self, ...):
        # ... existing init
        
        # Phase 3 components
        self.question_detector = QuestionDetector()
        self.query_reformulator = QueryReformulator()
        self.question_splitter = QuestionSplitter()
        self.enhanced_context_manager = EnhancedContextManager()
        self.session_store = SessionHistoryStore()
        
        # Enhanced RAG (initialized on session start)
        self.enhanced_rag = None
```

## Test Cases

1. **Full flow - question**: Question detected → reformulated → answered → persisted
2. **Full flow - statement**: Statement detected → skipped → only transcription persisted
3. **Follow-up handling**: Follow-up reformulated and answered correctly
4. **Compound question**: Split and all parts addressed in answer
5. **Session persistence**: All data retrievable after session ends
6. **Error resilience**: Pipeline continues if one component fails

## Definition of Done

- [ ] All components integrated
- [ ] End-to-end flow working
- [ ] Comprehensive logging
- [ ] Error handling robust
- [ ] Integration tests passing
- [ ] Manual testing complete
