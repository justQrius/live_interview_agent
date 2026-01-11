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
- [x] Title and date
- [x] Executive summary with positioning statements (20s/60s/2min)
- [x] Competency mapping table
- [x] Question bank by category (20+ questions with answers)
- [x] STAR story bank with tags
- [x] Gap analysis with mitigations
- [x] Questions to ask interviewer (5-10)
- [x] One-page cheat sheet

### AC-2: Cheat Sheet
- [x] Fits on one printed page
- [x] Key talking points only
- [x] Top 3 stories with one-liner
- [x] Top 3 metrics to remember
- [x] Key questions to ask

### AC-3: Export Formats
- [x] Markdown export (primary)
- [x] PDF export via markdown-to-PDF (HTML export for PDF generation)
- [x] JSON export for programmatic access

### AC-4: UI Integration
- [ ] "Generate Playbook" button in preparation UI (Deferred to Phase 4E STORY-070)
- [ ] Progress indicator during generation (Deferred to Phase 4E STORY-070)
- [ ] Download buttons for each format (Deferred to Phase 4E STORY-070)
- [ ] Preview in-app before download (Deferred to Phase 4E STORY-070)

### AC-5: Performance
- [x] Full playbook generation < 30 seconds (template mode is instant, LLM mode depends on provider)
- [ ] Progressive display as sections complete (Deferred to Phase 4E STORY-070)

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

- [x] All acceptance criteria met (backend complete, UI deferred to STORY-070)
- [x] E2E test from documents to playbook (24 tests passing)
- [x] PDF verified readable (HTML export with print styles)
- [ ] UI buttons working (Deferred to Phase 4E STORY-070)
- [x] Code reviewed
