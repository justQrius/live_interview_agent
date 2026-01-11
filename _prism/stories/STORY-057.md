# STORY-057: Candidate Profile Generator

**Phase**: 4A - Persistent Memory
**Priority**: High
**Effort**: 0.5 days
**Dependencies**: STORY-054, STORY-055 (Summarizer, Fact Extractor)

---

## User Story

As a system, I need to generate a compact "Candidate Profile" that can be injected into every LLM prompt, so that the LLM maintains consistent understanding of who the user is.

---

## Acceptance Criteria

### AC-1: Profile Content
- [ ] Profile includes current role and total experience
- [ ] Profile includes top 5-8 skills with proficiency
- [ ] Profile includes 3-5 career highlights with metrics
- [ ] Profile includes target role context (from JD)
- [ ] Profile includes key strengths summary

### AC-2: Size Constraints
- [ ] Profile is ~1000 tokens (approximately 750-1000 words)
- [ ] Profile fits comfortably in LLM context window
- [ ] Critical information prioritized if truncation needed

### AC-3: Template Format
- [ ] Markdown format for readability
- [ ] Consistent structure across regenerations
- [ ] Easily parseable by LLM

### AC-4: Regeneration
- [ ] Profile regenerated when new documents uploaded
- [ ] Profile regenerated when facts are edited
- [ ] Old profile archived before replacement

### AC-5: Injection
- [ ] `get_profile_for_prompt() -> str` returns ready-to-inject text
- [ ] Profile injected at start of system prompt
- [ ] Works with all LLM providers

---

## Technical Notes

```python
# File: sidecar/src/extraction/profile_generator.py

PROFILE_TEMPLATE = """## Candidate Profile

**Current Role**: {current_role}
**Total Experience**: {total_years} years
**Industries**: {industries}

### Core Competencies
{skills_section}

### Career Trajectory
{career_section}

### Key Achievements
{achievements_section}

### Target Role
{target_role_section}

### Positioning
{positioning_statement}
"""

class ProfileGenerator:
    MAX_TOKENS = 1000
    
    def generate(self, facts: ExtractedFacts, summaries: List[DocumentSummary]) -> CandidateProfile:
        # Prioritize most important information
        skills = self._top_skills(facts.skills, limit=8)
        achievements = self._top_achievements(facts.achievements, limit=5)
        # ... format into template
```

---

## Test Cases

1. **test_profile_generation**: Profile generated from facts
2. **test_token_limit**: Profile stays under 1000 tokens
3. **test_prioritization**: Most important info included when truncating
4. **test_template_format**: Markdown renders correctly
5. **test_regeneration**: New documents trigger new profile
6. **test_injection**: Profile works in LLM system prompt

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Profile token count verified
- [ ] Integration test with LLM call using profile
- [ ] Code reviewed
