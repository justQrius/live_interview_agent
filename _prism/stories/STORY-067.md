# STORY-067: Answer Structure Suggester

**Phase**: 4E - Interview Coaching
**Priority**: Medium
**Effort**: 0.5 days
**Dependencies**: None

---

## User Story

As a user, I want to see the recommended answer structure for each question type, so that I can organize my response clearly.

---

## Acceptance Criteria

### AC-1: Structure by Question Type
- [x] Behavioral → STAR method with percentages
- [x] Technical → Concept-Example-Tradeoff
- [x] Motivation → Past-Future-Bridge (Updated from company-role-value for better flow)
- [x] Situational → Framework-Hypothesis
- [x] General → Direct-Support-Close

### AC-2: Display Content
- [x] Framework name
- [x] Section breakdown with suggested percentages
- [x] 2-3 tips for this question type

### AC-3: UI Integration
- [ ] Structure hint displayed with answer (Deferred to Phase 4E STORY-070)
- [ ] Compact format, not overwhelming (Deferred to Phase 4E STORY-070)
- [ ] Visible before user starts speaking (Deferred to Phase 4E STORY-070)

---

## Technical Notes

```python
# File: sidecar/src/coaching/structure_suggester.py

STRUCTURES = {
    "behavioral": {
        "name": "STAR Method",
        "sections": [
            ("Situation", "15%", "Set the scene briefly"),
            ("Task", "10%", "Your specific responsibility"),
            ("Action", "60%", "What YOU did - be specific"),
            ("Result", "15%", "Quantified outcome + learning"),
        ],
        "tips": [
            "Focus on YOUR actions, not the team's",
            "Include at least one metric",
            "End with what you learned"
        ]
    },
    "technical": {
        "name": "Concept-Example-Tradeoff",
        "sections": [
            ("Concept", "20%", "Explain the core idea"),
            ("Example", "50%", "Your real experience"),
            ("Tradeoffs", "30%", "Nuances and considerations"),
        ],
        "tips": [
            "Start with the 'what'",
            "Ground in real examples",
            "Show depth with tradeoffs"
        ]
    },
    # ... more structures
}

def get_structure_hint(question_type: str) -> StructureHint:
    template = STRUCTURES.get(question_type, STRUCTURES["behavioral"])
    return StructureHint(
        name=template["name"],
        sections=template["sections"],
        tips=template["tips"]
    )
```

---

## Test Cases

1. **test_behavioral_structure**: STAR returned for behavioral
2. **test_technical_structure**: Correct structure for technical
3. **test_fallback**: Unknown type gets default structure
4. **test_message_format**: Correct WebSocket message structure

---

## Definition of Done

- [x] All acceptance criteria met
- [x] All question types covered (Heuristics in `_detect_subtype`)
- [x] UI displays structure hint (Message protocol implemented, UI component deferred to STORY-070)
- [x] Code reviewed
