# STORY-038: Session Store - Server Integration

**Phase**: 3A (Foundation)
**Priority**: P1 - Must Have
**Effort**: 0.5 days
**Dependencies**: STORY-037

## Description

Integrate the SessionHistoryStore into the main server. Sessions are automatically created on START_SESSION and ended on STOP_SESSION. Transcriptions and answers are recorded in real-time.

## Acceptance Criteria

- [ ] Initialize `SessionHistoryStore` in `SidecarServer.__init__()`
- [ ] Create session on START_SESSION, store session_id in state
- [ ] End session on STOP_SESSION
- [ ] Record transcriptions as they're processed
- [ ] Record answers as they're generated
- [ ] Include latency metrics in answer records
- [ ] Handle storage errors gracefully (don't break main flow)

## Technical Details

### Server Modifications

```python
# sidecar/src/server.py

from storage.session_store import SessionHistoryStore

class SidecarServer:
    def __init__(self, ...):
        # ... existing init
        self.session_store = SessionHistoryStore()
    
    async def _handle_start_session(self, ...):
        # ... existing logic
        
        # NEW: Create persistent session
        context_files = [f["name"] for f in data.get("files", [])]
        self.session_state.persistent_session_id = self.session_store.create_session(
            context_files=context_files
        )
        logger.info(f"Created persistent session: {self.session_state.persistent_session_id}")
    
    async def _handle_stop_session(self, ...):
        # ... existing logic
        
        # NEW: End persistent session
        if self.session_state.persistent_session_id:
            self.session_store.end_session(self.session_state.persistent_session_id)
            logger.info(f"Ended persistent session: {self.session_state.persistent_session_id}")
```

### Recording Transcriptions

```python
async def _process_speech_segment(self, segment) -> None:
    # ... existing transcription logic
    
    # NEW: Record to persistent storage
    if self.session_state.persistent_session_id:
        try:
            self.session_store.add_transcription(
                session_id=self.session_state.persistent_session_id,
                speaker=speaker.value,
                text=text,
                timestamp=segment.start_time,
                confidence=segment.confidence
            )
        except Exception as e:
            logger.warning(f"Failed to persist transcription: {e}")
```

### Recording Answers

```python
async def _generate_answer_for_question(self, question: str, start_time: float) -> None:
    # ... existing generation logic
    
    latency = time.time() - start_time
    
    # NEW: Record to persistent storage
    if self.session_state.persistent_session_id:
        try:
            self.session_store.add_answer(
                session_id=self.session_state.persistent_session_id,
                question=question,
                answer=full_answer,
                confidence=rag_confidence.value,
                rag_chunks=[r.text[:100] for r in retrieval_results[:3]],
                latency_ms=int(latency * 1000)
            )
        except Exception as e:
            logger.warning(f"Failed to persist answer: {e}")
```

### State Extension

```python
@dataclass
class SessionState:
    # ... existing fields
    persistent_session_id: Optional[str] = None
```

## Test Cases

1. **Session lifecycle**: Start → record data → stop → verify in DB
2. **Transcription persistence**: Verify all transcriptions saved with correct speaker
3. **Answer persistence**: Verify answer with latency and confidence saved
4. **Error resilience**: Simulate storage error, verify main flow continues
5. **Multiple sessions**: Start/stop multiple sessions, verify isolation

## Definition of Done

- [ ] Server integration complete
- [ ] Graceful error handling (storage failures don't break app)
- [ ] Logging for observability
- [ ] Integration tests passing
- [ ] Session ID passed in status messages to frontend
