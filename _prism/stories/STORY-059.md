# STORY-059: Playbook Question Generator

**Phase**: 4A - Interview Playbook
**Priority**: High
**Effort**: 1.5 days
**Dependencies**: STORY-055, STORY-056 (Fact & Story Extractors)

---

## User Story

As a job seeker, I want the system to generate 20+ tailored interview questions based on my resume and the job description, so that I can prepare for the most likely questions.

---

## Acceptance Criteria

### AC-1: Question Categories
- [x] Generate 6-8 **behavioral** questions based on JD competencies
- [x] Generate 4-6 **technical** questions based on JD requirements + resume skills
- [x] Generate 3-4 **motivation** questions (why this company/role)
- [x] Generate 3-4 **situational** questions based on role level
- [x] Generate 2-3 **curveball** questions targeting weak spots

### AC-2: Question Tailoring
- [x] Questions reference specific JD requirements
- [x] Questions adapted to seniority level (junior/mid/senior/lead)
- [x] Questions consider company context if available
- [x] Questions consider interviewer background if available (via LLM prompt context)

### AC-3: Question Metadata
- [x] Each question has `why_likely` explanation
- [x] Each question mapped to JD requirement it tests
- [x] Each question has difficulty rating
- [x] Each question has suggested answer framework

### AC-4: Quality Assurance
- [x] No duplicate questions
- [x] Questions are specific, not generic
- [x] 20+ total questions minimum
- [x] Generation time < 15 seconds (tests pass in <1s)

---

## Technical Notes

```python
# File: sidecar/src/playbook/question_generator.py

QUESTION_TEMPLATES = {
    "behavioral": [
        "Tell me about a time when you {competency}",
        "Describe a situation where you had to {competency}",
        "Give me an example of how you {competency}",
    ],
    "technical": [
        "How would you approach {technical_problem}?",
        "Explain your experience with {technology}",
        "Walk me through how you would {technical_task}",
    ],
    # ... more templates
}

GENERATION_PROMPT = """Generate interview questions for this candidate and role.

Candidate Background:
{candidate_profile}

Job Requirements:
{jd_requirements}

Company Context:
{company_info}

Generate questions in these categories:
- 6-8 Behavioral (based on required competencies)
- 4-6 Technical (based on required skills)
- 3-4 Motivation (why this company/role)
- 3-4 Situational (based on role level: {role_level})
- 2-3 Curveball (targeting gaps: {identified_gaps})

For each question, provide:
- question_text
- category
- why_likely (why interviewer would ask this)
- jd_requirement (which requirement it tests)
- difficulty (standard/challenging/curveball)
- answer_framework (STAR/Concept-Example/etc.)
"""
```

---

## Test Cases

1. **test_question_count**: At least 20 questions generated
2. **test_category_distribution**: Correct count per category
3. **test_jd_grounding**: Questions reference actual JD requirements
4. **test_no_duplicates**: All questions unique
5. **test_seniority_adaptation**: Questions match role level
6. **test_gap_targeting**: Curveballs target identified weaknesses

---

## Definition of Done

- [x] All acceptance criteria met
- [x] Unit tests with mocked data
- [x] Integration test with real LLM
- [x] Golden test with sample JD
- [x] Code reviewed
