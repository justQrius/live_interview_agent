# STORY-055: Fact Extractor

**Phase**: 4A - Persistent Memory
**Priority**: High
**Effort**: 1 day
**Dependencies**: STORY-053 (Memory Store)

---

## User Story

As a system, I need to extract structured factual data from uploaded documents, so that the LLM has accurate, queryable information about the candidate.

---

## Acceptance Criteria

### AC-1: Skills Extraction
- [ ] Extract skills with years of experience where stated
- [ ] Categorize proficiency (expert, proficient, familiar)
- [ ] Identify last used context (which company/role)
- [ ] Handle both explicit ("5 years Python") and implicit mentions

### AC-2: Career Timeline
- [ ] Extract company, role, dates for each position
- [ ] Parse date formats (2020-2022, Jan 2020 - Present, etc.)
- [ ] Calculate total experience years
- [ ] Extract 2-3 highlights per role
- [ ] Extract metrics per role where available

### AC-3: Achievements
- [ ] Identify achievement statements (led, built, reduced, increased)
- [ ] Extract associated metrics ("40% reduction", "$2M saved")
- [ ] Tag achievements (leadership, technical, scale, cost, quality)
- [ ] Link to source company/role

### AC-4: Education & Certifications
- [ ] Extract institution, degree, field, year
- [ ] Extract certifications with dates if available

### AC-5: Merge from Multiple Documents
- [ ] Facts from resume + JD combined intelligently
- [ ] JD requirements marked as "required" vs "nice-to-have"
- [ ] No duplicate entries

---

## Technical Notes

```python
# File: sidecar/src/extraction/fact_extractor.py

@dataclass
class SkillEntry:
    name: str
    years: Optional[int] = None
    proficiency: str = "proficient"  # expert, proficient, familiar
    last_used: Optional[str] = None
    source: str = "resume"

@dataclass  
class CareerEntry:
    company: str
    role: str
    start_date: str
    end_date: Optional[str] = None  # None = "Present"
    highlights: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)

FACT_EXTRACTION_PROMPT = """Extract structured facts from this resume.

Resume:
{resume_text}

Return JSON:
{{
  "skills": [
    {{"name": "Python", "years": 5, "proficiency": "expert", "last_used": "Current role"}},
    ...
  ],
  "career": [
    {{"company": "Acme Corp", "role": "Senior Engineer", "start_date": "2020", "end_date": "2023", "highlights": ["Led migration..."], "metrics": ["40% improvement"]}},
    ...
  ],
  "achievements": [...],
  "education": [...],
  "certifications": [...],
  "total_experience_years": 7,
  "current_role": "Senior Software Engineer"
}}
"""
```

---

## Test Cases

1. **test_skill_extraction**: Various skill formats correctly parsed
2. **test_career_timeline**: Dates parsed, gaps identified
3. **test_achievement_metrics**: Metrics extracted with tags
4. **test_education_parsing**: Various education formats work
5. **test_merge_documents**: Resume + JD merged without duplicates
6. **test_regex_fallback**: When LLM unavailable, regex extraction works

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests with varied resume formats
- [ ] Integration test with real LLM
- [ ] Golden tests with sample resumes
- [ ] Code reviewed
