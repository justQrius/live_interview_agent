# STORY-049: Query Reformulator

**Phase**: 3C (Conversational Intelligence)
**Priority**: P2 - Should Have
**Effort**: 1 day
**Dependencies**: STORY-036

## Description

Implement the QueryReformulator to expand follow-up questions into standalone queries. Uses conversation history to resolve pronouns and references.

## Acceptance Criteria

- [ ] Create `QueryReformulator` class in `sidecar/src/classification/query_reformulator.py`
- [ ] Detect follow-up indicators ("What about...", "Can you elaborate?", etc.)
- [ ] Extract topic from previous conversation turn
- [ ] Expand follow-ups into complete questions
- [ ] Return original question if not a follow-up
- [ ] Unit tests for all expansion patterns

## Technical Details

### File Location
```
sidecar/src/classification/
├── __init__.py
├── question_detector.py
└── query_reformulator.py
```

### Interface

```python
class QueryReformulator:
    def __init__(self, context_turns: int = 5):
        self.context_turns = context_turns
    
    def reformulate_if_needed(
        self, 
        current_question: str,
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[str, bool]:
        """
        Expand follow-up questions into standalone questions.
        
        Args:
            current_question: The question to potentially reformulate
            conversation_history: List of previous exchanges
            
        Returns:
            Tuple of (reformulated_question, was_reformulated)
        """
```

### Follow-up Patterns

```python
FOLLOW_UP_INDICATORS = [
    r"^(what about|how about)\s+",
    r"^(and|also)\s+(what|how|why|when)",
    r"^(can you|could you)\s+(elaborate|expand|explain more|tell me more)",
    r"^(tell me more|go on|continue)",
    r"^(what were|what are)\s+the\s+(results?|outcomes?)\??$",
    r"\b(that|this|it|those|these)\s*\??$",  # Ends with pronoun
]

EXPANSION_TEMPLATES = {
    r"^what about\s+(.+)\??$": 
        "What is your experience with {match} in relation to {prev_topic}?",
    r"^how about\s+(.+)\??$": 
        "How do you handle {match} based on your experience with {prev_topic}?",
    r"^can you elaborate\??$": 
        "Can you elaborate on {prev_topic}?",
    r"^tell me more\??$": 
        "Tell me more about {prev_topic}.",
    r"^(what were|what are) the results?\??$": 
        "What were the results of {prev_topic}?",
}
```

### Topic Extraction

```python
def _extract_topic(self, last_exchange: Dict[str, str]) -> str:
    """
    Extract the main topic from the previous Q&A exchange.
    
    Uses simple heuristics:
    1. Look for nouns/noun phrases in the question
    2. Look for key phrases in the answer
    3. Fallback to "your previous response"
    """
    question = last_exchange.get("question", "")
    
    # Try to extract noun phrase after "about"
    match = re.search(r"about\s+(.+?)(?:\?|$)", question, re.I)
    if match:
        return match.group(1).strip()
    
    # Try to extract subject
    match = re.search(r"^(?:tell me about|describe|explain)\s+(.+?)(?:\?|$)", question, re.I)
    if match:
        return match.group(1).strip()
    
    return "your previous response"
```

## Test Cases

1. **"What about Python?"**: Expands to "What is your experience with Python..."
2. **"Can you elaborate?"**: Expands to include previous topic
3. **"And the results?"**: Expands to "What were the results of..."
4. **Non-follow-up**: "Tell me about yourself" returns unchanged
5. **No history**: Question returns unchanged
6. **Multiple history turns**: Uses most recent relevant exchange

## Definition of Done

- [ ] QueryReformulator implemented
- [ ] All expansion patterns working
- [ ] Topic extraction working
- [ ] Unit tests passing
- [ ] Integration ready
