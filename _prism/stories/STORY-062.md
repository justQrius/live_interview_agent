# STORY-062: Playbook Assembler & Exporter

**Phase**: 4A - Interview Playbook
**Priority**: High
**Effort**: 1 day
**Dependencies**: STORY-059, STORY-060, STORY-061

---

## User Story

As a job seeker, I want to receive a complete, downloadable Interview Playbook document, so that I can review it before my interview.

---

## Acceptance Criteria

### AC-1: Playbook Structure
- [ ] Title and date
- [ ] Executive summary with positioning statements (20s/60s/2min)
- [ ] Competency mapping table
- [ ] Question bank by category (20+ questions with answers)
- [ ] STAR story bank with tags
- [ ] Gap analysis with mitigations
- [ ] Questions to ask interviewer (5-10)
- [ ] One-page cheat sheet

### AC-2: Cheat Sheet
- [ ] Fits on one printed page
- [ ] Key talking points only
- [ ] Top 3 stories with one-liner
- [ ] Top 3 metrics to remember
- [ ] Key questions to ask

### AC-3: Export Formats
- [ ] Markdown export (primary)
- [ ] PDF export via markdown-to-PDF
- [ ] JSON export for programmatic access

### AC-4: UI Integration
- [ ] "Generate Playbook" button in preparation UI
- [ ] Progress indicator during generation
- [ ] Download buttons for each format
- [ ] Preview in-app before download

### AC-5: Performance
- [ ] Full playbook generation < 30 seconds
- [ ] Progressive display as sections complete

---

## Technical Notes

```python
# File: sidecar/src/playbook/assembler.py

PLAYBOOK_TEMPLATE = """# Interview Playbook: {role} at {company}
Generated: {date}

## Executive Summary

### Your Positioning

**20-Second Pitch:**
{pitch_20s}

**60-Second Pitch:**
{pitch_60s}

**2-Minute Pitch:**
{pitch_2min}

---

## Competency Mapping

{competency_table}

---

## Question Bank

{questions_by_category}

---

## STAR Story Bank

{story_bank_table}

---

## Gap Analysis

{gap_analysis}

---

## Questions to Ask

{questions_to_ask}

---

## One-Page Cheat Sheet

{cheat_sheet}
"""

class PlaybookAssembler:
    async def assemble(
        self,
        questions: List[PlaybookQuestion],
        answers: List[DraftedAnswer],
        competencies: List[CompetencyMapping],
        stories: List[STARStory],
        profile: CandidateProfile
    ) -> Playbook:
        # Assemble all sections
        # Generate positioning statements
        # Format as markdown
        # Return complete playbook
```

---

## Test Cases

1. **test_all_sections_present**: Every section included
2. **test_cheat_sheet_length**: Fits on one page
3. **test_markdown_valid**: Renders correctly
4. **test_pdf_generation**: PDF exports successfully
5. **test_json_structure**: JSON matches schema
6. **test_generation_time**: < 30 seconds total

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] E2E test from documents to playbook
- [ ] PDF verified readable
- [ ] UI buttons working
- [ ] Code reviewed
