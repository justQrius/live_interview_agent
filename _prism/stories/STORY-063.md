# STORY-063: Tier 3 LLM Question Detection

**Phase**: 4C - Enhanced Detection
**Priority**: Medium
**Effort**: 1 day
**Dependencies**: None (enhances existing detector)

---

## User Story

As a system, I need to use an LLM to classify ambiguous utterances, so that we catch questions that rule-based patterns miss.

---

## Acceptance Criteria

### AC-1: Trigger Conditions
- [ ] Tier 3 triggers when Tier 1+2 confidence < 0.7
- [ ] Only triggers if text looks potentially interrogative
- [ ] Does NOT trigger for obvious non-questions (< 5 words, no question signals)

### AC-2: LLM Classification
- [ ] Simple YES/NO prompt for speed
- [ ] Uses fastest available model (gpt-4o-mini, claude-haiku, gemini-flash)
- [ ] Includes last 3 conversation turns for context
- [ ] Returns confidence score

### AC-3: Performance
- [ ] Latency < 150ms P95
- [ ] Runs in parallel with speculative retrieval
- [ ] Does not block hot path

### AC-4: Logging & Metrics
- [ ] Log all Tier 3 invocations
- [ ] Track accuracy vs eventual user behavior
- [ ] Enable threshold tuning based on data

---

## Technical Notes

```python
# File: sidecar/src/classification/tier3_detector.py

TIER3_PROMPT = """Determine if this is an interview question requiring a response.

Utterance: "{text}"

Recent conversation:
{context}

Reply ONLY with:
- QUESTION - if this requires a substantive answer
- NOT_QUESTION - if this is a statement, acknowledgment, or small talk

Your classification:"""

class Tier3Detector:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.logger = logging.getLogger(__name__)
    
    async def classify(
        self,
        text: str,
        history: List[Dict[str, str]]
    ) -> Tuple[bool, float]:
        # Build context
        context_lines = [
            f"{h['role']}: {h['content'][:100]}"
            for h in history[-3:]
        ]
        
        prompt = TIER3_PROMPT.format(
            text=text,
            context="\n".join(context_lines)
        )
        
        start = time.time()
        response = await self.llm.complete(prompt, max_tokens=10)
        latency = time.time() - start
        
        is_question = "QUESTION" in response.upper() and "NOT" not in response.upper()
        confidence = 0.85 if is_question else 0.80
        
        self.logger.info(f"Tier3: {is_question} ({latency:.3f}s) - {text[:50]}")
        
        return is_question, confidence
```

---

## Test Cases

1. **test_triggers_on_low_confidence**: Tier 3 called when confidence < 0.7
2. **test_skips_obvious_non_questions**: Short acknowledgments skip Tier 3
3. **test_latency**: < 150ms P95 across 100 calls
4. **test_parallel_execution**: Runs alongside speculative RAG
5. **test_context_usage**: Recent history improves accuracy
6. **test_ambiguous_cases**: Correctly classifies edge cases

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Latency benchmarks passing
- [ ] Logging implemented
- [ ] Integration with existing detector
- [ ] Code reviewed
