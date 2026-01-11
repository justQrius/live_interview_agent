# STORY-056: STAR Story Extractor

**Phase**: 4A - Persistent Memory
**Priority**: High
**Effort**: 1 day
**Dependencies**: STORY-055 (Fact Extractor)

---

## User Story

As a system, I need to identify and structure STAR story candidates from the user's resume, so that behavioral questions can be matched to pre-prepared stories.

---

## Acceptance Criteria

### AC-1: Story Identification
- [ ] Identify 8-12 STAR story candidates from achievements
- [ ] Each story has clear Situation, Task, Action, Result
- [ ] Stories have associated metrics where available
- [ ] Incomplete stories marked with lower confidence

### AC-2: Story Structure
- [ ] `situation`: 2-3 sentences of context
- [ ] `task`: 1-2 sentences of responsibility
- [ ] `action`: 3-5 sentences of what was done
- [ ] `result`: 1-2 sentences with metrics
- [ ] `title`: Short memorable name ("The Migration Crisis")

### AC-3: Story Metadata
- [ ] `tags`: List of categories (leadership, conflict, scale, failure, innovation, etc.)
- [ ] `source_company`: Which company this story is from
- [ ] `metrics`: List of quantified results
- [ ] `confidence`: How complete/usable is this story (0.0-1.0)

### AC-4: Story Variants
- [ ] `opening_line`: Suggested first sentence for this story
- [ ] `twenty_second_version`: Compressed version for quick reference
- [ ] Stories usable for multiple question types

### AC-5: Story Bank Management
- [ ] Stories saved to Memory Store
- [ ] Stories retrievable by tag for matching
- [ ] Stories editable by user (future: UI)

---

## Technical Notes

```python
# File: sidecar/src/extraction/story_extractor.py

STORY_EXTRACTION_PROMPT = """Based on these career achievements, identify 8-12 STAR stories.

Career Achievements:
{achievements}

For each story, provide:
- title: A short memorable name
- situation: 2-3 sentences of context
- task: 1-2 sentences of your responsibility  
- action: 3-5 sentences of specific actions taken
- result: 1-2 sentences with quantified outcome
- metrics: List of numbers/percentages mentioned
- tags: Categories like [leadership, conflict, scale, failure, innovation, customer, technical]
- opening_line: A great first sentence to start telling this story
- twenty_second_version: The whole story in 2-3 sentences

Return JSON array of stories.
"""

STORY_TAGS = [
    "leadership", "conflict", "teamwork", "failure", "success",
    "scale", "innovation", "customer", "technical", "deadline",
    "learning", "mentoring", "cross_functional", "ambiguity"
]
```

---

## Test Cases

1. **test_story_identification**: 8-12 stories extracted from rich resume
2. **test_star_completeness**: Each component present and meaningful
3. **test_tag_assignment**: Tags match story content
4. **test_opening_line_quality**: Opening line is engaging and specific
5. **test_short_version**: 20-second version captures essence
6. **test_sparse_resume**: Fewer stories extracted, lower confidence

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests with sample resumes
- [ ] Golden tests with expected story output
- [ ] Stories match actual resume content
- [ ] Code reviewed
