# STORY-036: Question Detector - Server Integration

**Phase**: 3A (Foundation)
**Priority**: P0 - Must Have
**Effort**: 0.5 days
**Dependencies**: STORY-035

## Description

Integrate the QuestionDetector into the main server pipeline. Modify the audio processing flow to filter out non-questions before triggering LLM generation.

## Acceptance Criteria

- [ ] Initialize `QuestionDetector` in `SidecarServer.__init__()`
- [ ] Modify `_process_speech_segment()` to use question detection
- [ ] Only trigger `_generate_answer_for_question()` for detected questions
- [ ] Log classification results for debugging
- [ ] Add configuration for confidence threshold (default: 0.7)
- [ ] Non-questions still broadcast as transcriptions
- [ ] Integration tests passing

## Technical Details

### Server Modification

```python
# sidecar/src/server.py

from classification.question_detector import QuestionDetector

class SidecarServer:
    def __init__(self, ...):
        # ... existing init
        self.question_detector = QuestionDetector()
        self.question_confidence_threshold = 0.7
    
    async def _process_speech_segment(self, segment) -> None:
        # ... existing STT logic
        
        # NEW: Question detection before answer generation
        if speaker == Speaker.INTERVIEWER:
            is_question, confidence, q_type = self.question_detector.is_actionable_question(
                text, 
                self.session_state.conversation_history
            )
            
            logger.info(f"Question detection: {q_type} (confidence={confidence:.2f})")
            
            if is_question and confidence >= self.question_confidence_threshold:
                await self._generate_answer_for_question(text, pipeline_start)
            else:
                logger.info(f"Skipping answer generation for non-question: {text[:50]}...")
```

### Configuration

```python
# Add to Phase3Config or server config
QUESTION_CONFIDENCE_THRESHOLD: float = 0.7
QUESTION_DETECTION_ENABLED: bool = True  # Feature flag for rollout
```

## Test Cases

1. **Question triggers answer**:
   - Input: "What is your experience with Python?"
   - Expected: Answer generation triggered

2. **Statement skips answer**:
   - Input: "That's very interesting."
   - Expected: Transcription broadcast, no answer generation

3. **Low confidence falls through**:
   - Input: "Python." (ambiguous)
   - Confidence: 0.5 (below threshold)
   - Expected: No answer generation

4. **Threshold configuration**:
   - Set threshold to 0.5
   - Input with confidence 0.6 should trigger answer

## Definition of Done

- [ ] Server integration complete
- [ ] Feature flag for gradual rollout
- [ ] Logging for observability
- [ ] Integration tests passing
- [ ] Manual testing confirms reduced false triggers
