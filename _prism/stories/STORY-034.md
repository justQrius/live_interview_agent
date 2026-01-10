# STORY-034: Question Detector - Rule-Based Tier

**Phase**: 3A (Foundation)
**Priority**: P0 - Must Have
**Effort**: 1 day
**Dependencies**: None

## Description

Implement the first tier of the cascaded question detection system using rule-based pattern matching. This tier must achieve <2ms latency and catch 65-75% of obvious questions and statements.

## Acceptance Criteria

- [ ] Create `QuestionDetector` class in `sidecar/src/classification/question_detector.py`
- [ ] Implement `is_actionable_question(text, conversation_history)` method
- [ ] Return tuple: `(is_question: bool, confidence: float, classification_type: str)`
- [ ] Classification types: `interview_question`, `follow_up`, `clarification`, `small_talk`, `statement`, `acknowledgment`
- [ ] Pattern matching latency <2ms P99
- [ ] Test coverage >90% for pattern matching logic
- [ ] Unit tests for all defined patterns

## Technical Details

### File Location
```
sidecar/src/classification/
├── __init__.py
└── question_detector.py
```

### Pattern Categories

```python
INTERVIEW_QUESTION_PATTERNS = [
    r"^tell me about",
    r"^describe (a |your )",
    r"^explain (how|what|why)",
    r"^what (is|are|was|were|do|did|would|have)",
    r"^how (do|did|would|have|can|could)",
    r"^why (do|did|would|have)",
    r"^can you (tell|describe|explain|walk)",
    r"^walk me through",
    r"^give me an example",
    r"^have you (ever|had)",
]

STATEMENT_PATTERNS = [
    r"^(okay|ok|alright|sure|great|perfect|excellent|good|nice)",
    r"^(thank you|thanks)",
    r"^(i see|i understand|got it|makes sense)",
    r"^(let me|let's|we'll|we will)",
    r"^(that's|that is) (good|great|interesting|helpful)",
    r"^(moving on|next|now)",
    r"^(so basically|in other words)",
]
```

### Interface

```python
from typing import List, Dict, Tuple

class QuestionDetector:
    def __init__(self):
        self._compile_patterns()
    
    def is_actionable_question(
        self, 
        text: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> Tuple[bool, float, str]:
        """
        Determine if text is an actionable question.
        
        Returns:
            Tuple of (is_question, confidence, classification_type)
        """
        # Tier 1: Rule-based
        result = self._rule_based_classification(text)
        if result[1] >= 0.8:  # High confidence
            return result
        
        # For now, return rule-based result
        # Tier 2 will be added in STORY-035
        return result
```

## Test Cases

1. **Obvious questions with question mark**: "What is your experience with Python?" → (True, 0.95, "interview_question")
2. **WH-word questions**: "How do you handle deadlines?" → (True, 0.90, "interview_question")
3. **Behavioral starters**: "Tell me about a time..." → (True, 0.90, "interview_question")
4. **Acknowledgments**: "Okay, that makes sense." → (False, 0.95, "acknowledgment")
5. **Statements**: "Let me tell you about the role." → (False, 0.90, "statement")
6. **Small talk**: "Thanks for coming in today." → (False, 0.85, "small_talk")
7. **Ambiguous**: "Interesting background." → (False, 0.6, "statement") - low confidence

## Definition of Done

- [ ] Code implemented with type hints
- [ ] Unit tests passing with >90% coverage
- [ ] Latency benchmark <2ms
- [ ] Code reviewed
- [ ] Documentation in docstrings
