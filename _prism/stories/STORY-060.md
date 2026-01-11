# STORY-060: Playbook Answer Drafter

**Phase**: 4A - Interview Playbook
**Priority**: High
**Effort**: 1 day
**Dependencies**: STORY-059, STORY-056 (Question Generator, Story Extractor)

---

## User Story

As a job seeker, I want each generated question to have a suggested answer based on my resume, so that I have a starting point for my preparation.

---

## Acceptance Criteria

### AC-1: Answer Generation
- [x] Each question has a complete suggested answer
- [x] Answers grounded in user's resume/experience
- [x] Answers use appropriate framework (STAR for behavioral, etc.)
- [x] Answers are 100-200 words (45-90 seconds spoken)

### AC-2: Story Linking
- [x] Behavioral questions linked to relevant STAR stories
- [x] Story ID referenced in answer metadata
- [x] Story opening line included in answer

### AC-3: Key Points
- [x] Each answer has 3-5 bullet point key points
- [x] Key points include metrics where available
- [x] Key points easy to remember during interview

### AC-4: Quality
- [x] Answers sound natural, not robotic
- [x] No invented facts - only from provided context
- [x] Answers avoid cliches and buzzwords
- [x] Generation time < 20 seconds for all answers

---

## Technical Notes

```python
# File: sidecar/src/playbook/answer_drafter.py

ANSWER_PROMPT = """Generate a suggested answer for this interview question.

Question: {question}
Category: {category}
Framework: {framework}

Candidate's Background:
{relevant_context}

Relevant STAR Story (if behavioral):
{star_story}

Requirements:
1. Answer in first person ("I")
2. 100-200 words (45-90 seconds spoken)
3. Use {framework} framework
4. Only use facts from the provided context
5. Include specific metrics if available
6. Sound natural and conversational

Return:
{{
  "suggested_answer": "...",
  "key_points": ["point 1", "point 2", ...],
  "story_used": "story_id or null",
  "opening_line": "suggested first sentence"
}}
"""

class AnswerDrafter:
    def draft_answer(
        self,
        question: PlaybookQuestion,
        profile: CandidateProfile,
        stories: List[STARStory]
    ) -> DraftedAnswer:
        # Find relevant story for behavioral questions
        relevant_story = None
        if question.category == "behavioral":
            relevant_story = self._find_best_story(question, stories)
        
        # Get relevant context via RAG
        context = self._get_relevant_context(question.text)
        
        # Generate answer
        # ...
```

---

## Test Cases

1. **test_answer_grounding**: Answer only contains resume facts
2. **test_story_linking**: Behavioral answers use appropriate story
3. **test_framework_usage**: STAR framework correctly applied
4. **test_answer_length**: 100-200 words
5. **test_key_points**: 3-5 actionable key points
6. **test_no_hallucination**: No invented details

---

## Definition of Done

- [x] All acceptance criteria met
- [x] Unit tests with mocked data
- [x] Integration test with real LLM
- [x] Answers validated against source resume
- [x] Code reviewed
