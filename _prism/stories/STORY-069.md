# STORY-069: Profile Injection in LLM Prompts

**Phase**: 4B - Persistent Memory Integration
**Priority**: High
**Effort**: 0.5 days
**Dependencies**: STORY-057 (Profile Generator)

---

## User Story

As a system, I need to inject the Candidate Profile into every LLM call, so that the LLM maintains consistent understanding of who the user is.

---

## Acceptance Criteria

### AC-1: Profile Injection
- [ ] Candidate Profile included in system prompt for all LLM calls
- [ ] Profile appears at start of system prompt
- [ ] Profile updated when documents change

### AC-2: All LLM Entry Points
- [ ] Answer generation includes profile
- [ ] Preparation generation includes profile
- [ ] Manual question handling includes profile

### AC-3: Token Management
- [ ] Profile stays within ~1000 tokens
- [ ] Total prompt stays within provider limits
- [ ] Profile truncated gracefully if too long

### AC-4: Fallback
- [ ] System works without profile (graceful degradation)
- [ ] Warning logged if profile unavailable

---

## Technical Notes

```python
# File: sidecar/src/providers/llm/base.py (modified)

class LLMProvider(ABC):
    def __init__(self):
        self.candidate_profile: Optional[str] = None
    
    def set_candidate_profile(self, profile: str):
        """Set the candidate profile for prompt injection"""
        self.candidate_profile = profile
    
    def _build_system_prompt(self, base_prompt: str) -> str:
        """Build system prompt with profile injection"""
        if self.candidate_profile:
            return f"{self.candidate_profile}\n\n---\n\n{base_prompt}"
        return base_prompt

# In server.py - on session start after extraction
if profile := memory_store.get_profile():
    self.llm.set_candidate_profile(profile.profile_text)
```

---

## Test Cases

1. **test_profile_in_answer**: Profile included in answer generation
2. **test_profile_in_preparation**: Profile included in preparation
3. **test_no_profile_fallback**: Works without profile
4. **test_profile_update**: Changed profile reflected in next call
5. **test_token_limit**: Total prompt within limits

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All LLM entry points verified
- [ ] Token counting validated
- [ ] Integration tests passing
- [ ] Code reviewed
