# STORY-061: Playbook Competency Mapper

**Phase**: 4A - Interview Playbook
**Priority**: High
**Effort**: 0.5 days
**Dependencies**: STORY-055 (Fact Extractor)

---

## User Story

As a job seeker, I want to see how my experience maps to each job requirement, so that I know what to emphasize in my answers.

---

## Acceptance Criteria

### AC-1: Requirement Extraction
- [ ] Extract all requirements from JD (must-have + nice-to-have)
- [ ] Categorize as: technical skill, soft skill, experience, education
- [ ] Identify required vs preferred

### AC-2: Evidence Mapping
- [ ] For each requirement, find matching evidence in resume
- [ ] Evidence includes specific examples with metrics
- [ ] Identify gaps (requirements without evidence)

### AC-3: Output Format
- [ ] Table format: Requirement → Evidence → Metrics → Emphasis
- [ ] Gaps highlighted with mitigation suggestions
- [ ] Strong matches highlighted

### AC-4: Gap Analysis
- [ ] List requirements with weak/no evidence
- [ ] Suggest mitigation approaches for each gap
- [ ] Prioritize gaps by importance (must-have vs nice-to-have)

---

## Technical Notes

```python
# File: sidecar/src/playbook/competency_mapper.py

@dataclass
class CompetencyMapping:
    requirement: str
    requirement_type: str  # technical, soft_skill, experience, education
    is_required: bool  # vs nice-to-have
    evidence: Optional[str]
    metrics: List[str]
    emphasis_points: List[str]
    match_strength: str  # strong, moderate, weak, gap
    mitigation: Optional[str]  # For gaps

MAPPING_PROMPT = """Map these job requirements to the candidate's experience.

Job Requirements:
{jd_requirements}

Candidate Experience:
{candidate_facts}

For each requirement:
1. Find specific evidence from resume
2. Extract metrics that support the match
3. Note what to emphasize when discussing
4. Rate match strength (strong/moderate/weak/gap)
5. For gaps, suggest mitigation approach

Return JSON array of mappings.
"""
```

---

## Test Cases

1. **test_requirement_extraction**: All JD requirements identified
2. **test_evidence_matching**: Correct resume sections linked
3. **test_gap_identification**: Missing requirements flagged
4. **test_mitigation_suggestions**: Gaps have actionable mitigations
5. **test_strength_rating**: Match strengths accurate

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests
- [ ] Visual output matches expected table format
- [ ] Code reviewed
