# STORY-050: Question Splitter

**Phase**: 3C (Conversational Intelligence)
**Priority**: P2 - Should Have
**Effort**: 0.5 days
**Dependencies**: STORY-036

## Description

Implement the QuestionSplitter to detect and split compound questions into individual answerable units. Ensures all parts of multi-part questions are addressed.

## Acceptance Criteria

- [ ] Create `QuestionSplitter` class in `sidecar/src/classification/question_splitter.py`
- [ ] Detect compound question patterns
- [ ] Split on conjunctions preceding question words
- [ ] Ensure each split question is well-formed
- [ ] Return original as single-item list if not compound
- [ ] Unit tests for splitting logic

## Technical Details

### File Location
```
sidecar/src/classification/
├── __init__.py
├── question_detector.py
├── query_reformulator.py
└── question_splitter.py
```

### Interface

```python
class QuestionSplitter:
    def split_questions(self, text: str) -> List[str]:
        """
        Split compound questions into individual questions.
        
        Args:
            text: The potentially compound question
            
        Returns:
            List of individual questions (single item if not compound)
        """
    
    def _is_compound(self, text: str) -> bool:
        """Detect if text contains multiple questions."""
    
    def _split_by_conjunctions(self, text: str) -> List[str]:
        """Split on conjunctions that precede question words."""
    
    def _ensure_question_form(self, text: str) -> str:
        """Ensure split text is a complete question."""
```

### Compound Detection

```python
COMPOUND_INDICATORS = [
    r"\band\b.*(what|how|why|when|where|tell|describe|explain)",
    r"\?.*\?",  # Multiple question marks
    r"(first|second|also|additionally).*(what|how|tell)",
    r"(one|another|other)\s+(thing|question)",
    r",\s*(and|also)\s+(what|how|can|could)",
]
```

### Splitting Logic

```python
def _split_by_conjunctions(self, text: str) -> List[str]:
    """Split on conjunctions that precede question words."""
    # Pattern: conjunction followed by question word
    pattern = r"\s+(and|also|additionally|plus)\s+(?=(what|how|why|when|where|can|could|tell|describe))"
    
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    
    # Filter out the conjunctions themselves
    questions = [p.strip() for p in parts if p and p.lower() not in ('and', 'also', 'additionally', 'plus')]
    
    return questions if questions else [text]
```

### Question Form Normalization

```python
def _ensure_question_form(self, text: str) -> str:
    """Ensure text is a proper question."""
    text = text.strip()
    
    # Remove leading conjunctions
    text = re.sub(r"^(and|also|additionally|plus)\s+", "", text, flags=re.I)
    
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]
    
    # Add question mark if missing
    if not text.endswith('?') and self._looks_like_question(text):
        text += '?'
    
    return text
```

## Test Cases

1. **Simple compound**: "What's X and how do you Y?" → ["What's X?", "How do you Y?"]
2. **Three-part**: "Tell me A, B, and C" → ["Tell me A", "Tell me B", "Tell me C"]
3. **Not compound**: "Tell me about your experience" → ["Tell me about your experience"]
4. **Multiple question marks**: "What? How?" → ["What?", "How?"]
5. **Also pattern**: "What's X? Also, how do you Y?" → ["What's X?", "How do you Y?"]
6. **Edge case - "and" in content**: "Tell me about research and development" → unchanged

## Definition of Done

- [ ] QuestionSplitter implemented
- [ ] Compound detection working
- [ ] Splitting logic correct
- [ ] Edge cases handled
- [ ] Unit tests passing
