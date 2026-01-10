# STORY-041: Session Export Utilities

**Phase**: 3A (Foundation)
**Priority**: P2 - Should Have
**Effort**: 0.5 days
**Dependencies**: STORY-037

## Description

Implement export utilities to convert session data into various formats: JSON, Markdown, and plain text. These are used by both the WebSocket export handler and potential future CLI tools.

## Acceptance Criteria

- [ ] Create `SessionExporter` class in `sidecar/src/storage/exporter.py`
- [ ] Support JSON export (complete data)
- [ ] Support Markdown export (human-readable format)
- [ ] Support plain text export (simple transcript)
- [ ] Include metadata in exports (date, duration, context files)
- [ ] Handle edge cases (empty sessions, missing data)

## Technical Details

### File Location
```
sidecar/src/storage/
├── __init__.py
├── session_store.py
└── exporter.py
```

### Interface

```python
from enum import Enum
from typing import Union

class ExportFormat(Enum):
    JSON = "json"
    MARKDOWN = "md"
    TEXT = "txt"

class SessionExporter:
    @staticmethod
    def export(session_data: SessionData, format: ExportFormat) -> str:
        """Export session data to specified format."""
        if format == ExportFormat.JSON:
            return SessionExporter._to_json(session_data)
        elif format == ExportFormat.MARKDOWN:
            return SessionExporter._to_markdown(session_data)
        elif format == ExportFormat.TEXT:
            return SessionExporter._to_text(session_data)
        else:
            raise ValueError(f"Unsupported format: {format}")
```

### Markdown Format

```markdown
# Interview Session

**Date**: January 9, 2026 2:30 PM
**Duration**: 45 minutes
**Context Files**: resume.pdf, job_description.txt

---

## Transcript

### [0:00] Interviewer
Tell me about yourself.

### [0:05] AI Response
I'm a software engineer with 5 years of experience...

**Confidence**: High | **Latency**: 1.2s

---

### [2:30] Interviewer
What's your experience with Python?

### [2:35] AI Response
I've been working with Python for over 4 years...

**Confidence**: High | **Latency**: 0.9s

---

## Summary

- **Total Questions**: 12
- **Average Latency**: 1.1s
- **High Confidence**: 10 (83%)
- **Medium Confidence**: 2 (17%)
```

### Plain Text Format

```
Interview Session - January 9, 2026

[0:00] Interviewer: Tell me about yourself.
[0:05] Response: I'm a software engineer with 5 years of experience...

[2:30] Interviewer: What's your experience with Python?
[2:35] Response: I've been working with Python for over 4 years...
```

## Test Cases

1. **JSON export**: Export session, verify valid JSON with all fields
2. **Markdown export**: Export session, verify proper markdown formatting
3. **Text export**: Export session, verify simple readable format
4. **Empty session**: Export empty session, verify graceful handling
5. **Special characters**: Session with quotes, newlines, unicode
6. **Large session**: Export 100+ transcription session

## Definition of Done

- [ ] All three formats implemented
- [ ] Unit tests for each format
- [ ] Edge case handling
- [ ] Documentation in docstrings
