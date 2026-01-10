# STORY-035: Question Detector - Context-Aware Tier

**Phase**: 3A (Foundation)
**Priority**: P0 - Must Have
**Effort**: 0.5 days
**Dependencies**: STORY-034

## Description

Add Tier 2 context-aware heuristics to the question detector. This tier uses conversation history to improve classification accuracy for ambiguous cases.

## Acceptance Criteria

- [ ] Extend `QuestionDetector` with `_context_aware_classification()` method
- [ ] Use last 3-5 conversation turns for context
- [ ] Detect follow-up patterns based on previous Q&A
- [ ] Improve classification accuracy to 80-85%
- [ ] Latency <10ms for context-aware tier
- [ ] Unit tests for context-based scenarios

## Technical Details

### Context-Aware Signals

```python
def _context_aware_classification(
    self, 
    text: str, 
    history: List[Dict[str, str]]
) -> Tuple[bool, float, str]:
    """
    Analyze text in context of conversation history.
    
    Signals used:
    1. Was the previous turn an answer? (likely follow-up)
    2. Does text reference previous topic? (pronouns, "that", etc.)
    3. Is this a topic transition? ("Moving on", "Next question")
    4. Time since last question (rapid-fire vs. discussion)
    """
```

### Context Patterns

```python
FOLLOW_UP_INDICATORS = [
    r"^(what about|how about|and what|and how)",
    r"^(can you|could you) (elaborate|expand|explain)",
    r"(that|this|it)\??$",  # Ends with pronoun
]

TOPIC_TRANSITION_PATTERNS = [
    r"^(moving on|let's move|next)",
    r"^(changing topics|different question)",
    r"^(now|so).*(tell me|what about)",
]
```

## Test Cases

1. **Follow-up after answer**: 
   - History: [Q: "Tell me about React", A: "I've used React for 3 years..."]
   - Input: "What about testing?"
   - Expected: (True, 0.85, "follow_up")

2. **Elaboration request**:
   - History: [Q: "Describe a challenge", A: "We had a deadline issue..."]
   - Input: "Can you elaborate on that?"
   - Expected: (True, 0.90, "follow_up")

3. **Topic transition**:
   - History: [Previous Q&A about experience]
   - Input: "Moving on, let's talk about your technical skills"
   - Expected: (True, 0.80, "interview_question")

4. **Statement in context**:
   - History: [Q: "Any questions?", A: "Yes, about the team..."]
   - Input: "That's a great question"
   - Expected: (False, 0.85, "acknowledgment")

## Definition of Done

- [ ] Context-aware tier implemented
- [ ] Cascading logic: rule-based → context-aware
- [ ] Unit tests for context scenarios
- [ ] Latency verified <10ms
- [ ] Integration with Tier 1
