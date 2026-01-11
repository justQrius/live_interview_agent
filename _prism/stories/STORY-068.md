# STORY-068: Consistency Tracker

**Phase**: 4E - Interview Coaching
**Priority**: Medium
**Effort**: 1 day
**Dependencies**: STORY-053 (Memory Store)

---

## User Story

As a user, I want the system to track factual claims I make during the interview, so that I don't accidentally contradict myself.

---

## Acceptance Criteria

### AC-1: Claim Extraction
- [ ] Extract factual claims from generated answers
- [ ] Track: years of experience, metrics cited, team sizes, etc.
- [ ] Claims stored with session ID and timestamp

### AC-2: Consistency Checking
- [ ] Compare new claims against previous ones
- [ ] Detect contradictions (e.g., "5 years" vs "7 years")
- [ ] Flag potential issues

### AC-3: User Notification
- [ ] Warning message when contradiction detected
- [ ] Show both claims (old and new)
- [ ] Non-intrusive - doesn't block answer

### AC-4: UI Display
- [ ] "Claims made" panel showing tracked claims
- [ ] Contradictions highlighted
- [ ] Collapsible/dismissable

---

## Technical Notes

```python
# File: sidecar/src/coaching/consistency_tracker.py

class ConsistencyTracker:
    CLAIM_PATTERNS = [
        (r"(\d+)\s*(?:years?|yrs?)(?:\s+of)?\s+experience", "experience_years"),
        (r"led\s+(?:a\s+)?team\s+of\s+(\d+)", "team_size"),
        (r"(\d+)%\s+(?:improvement|reduction|increase)", "metric_percent"),
        (r"\$(\d+(?:,\d+)?(?:\.\d+)?[KMB]?)", "metric_money"),
        (r"(\d+)\s+(?:engineers?|developers?|people|members)", "team_size"),
    ]
    
    def __init__(self, memory_store: MemoryStore):
        self.store = memory_store
        self.session_id: Optional[str] = None
    
    def start_session(self, session_id: str):
        self.session_id = session_id
    
    def extract_and_check(self, answer_text: str) -> ConsistencyResult:
        """Extract claims and check for contradictions"""
        new_claims = self._extract_claims(answer_text)
        existing_claims = self.store.get_session_claims(self.session_id)
        
        contradictions = []
        for new_claim in new_claims:
            for existing in existing_claims:
                if existing.claim_type == new_claim.claim_type:
                    if not self._values_match(existing.value, new_claim.value):
                        contradictions.append(Contradiction(
                            claim_type=new_claim.claim_type,
                            existing_value=existing.value,
                            new_value=new_claim.value,
                            message=f"Previously said {existing.value}, now saying {new_claim.value}"
                        ))
        
        # Store new claims
        for claim in new_claims:
            self.store.add_claim(self.session_id, claim.text, claim.claim_type)
        
        return ConsistencyResult(
            new_claims=new_claims,
            contradictions=contradictions
        )
```

```typescript
// Message type
{ 
  type: "CONSISTENCY_WARNING", 
  data: { 
    claim_type: "experience_years",
    existing: "5 years",
    new: "7 years",
    message: "Previously said 5 years, now saying 7 years"
  } 
}
```

---

## Test Cases

1. **test_claim_extraction**: All pattern types extracted
2. **test_contradiction_detection**: Conflicting claims flagged
3. **test_no_false_positives**: Similar but valid claims not flagged
4. **test_session_isolation**: Claims tracked per session
5. **test_claim_persistence**: Claims saved to store

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Claims accurately extracted
- [ ] Contradictions correctly detected
- [ ] UI shows claims and warnings
- [ ] Code reviewed
