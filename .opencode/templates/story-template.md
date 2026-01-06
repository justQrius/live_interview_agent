# Story: [Story Title]

> **ID**: [beads-id or story-id]
> **Status**: Draft | Ready | In Progress | Done | Blocked
> **Priority**: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
> **Estimate**: [Points or time]

---

## User Story

**As a** [type of user]
**I want** [goal/desire]
**So that** [benefit/value]

---

## Context

[Brief background on why this story exists and how it fits into the larger feature]

**Parent Epic**: [Epic name/link]
**Architecture Reference**: [Link to architecture doc]

---

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC-1 | [Given/When/Then or testable statement] | ⬜ |
| AC-2 | [Given/When/Then or testable statement] | ⬜ |
| AC-3 | [Given/When/Then or testable statement] | ⬜ |
| AC-4 | [Given/When/Then or testable statement] | ⬜ |

> Status: ⬜ Not Started | 🔄 In Progress | ✅ Done | ❌ Blocked

---

## Tasks

- [ ] **[Task 1]**: [Description]
- [ ] **[Task 2]**: [Description]
- [ ] **[Task 3]**: [Description]
- [ ] **[Task 4]**: [Description]
- [ ] **Write tests**: [Test description]
- [ ] **Self-review**: Check CLAUDE.md compliance
- [ ] **Update beads**: Mark story complete

---

## Technical Notes

### Approach
[How this will be implemented]

### Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `path/to/file.ts` | Create/Modify | [What changes] |

### Dependencies
- [Other stories/tasks this depends on]

### Edge Cases
- [Edge case 1 and how to handle]
- [Edge case 2 and how to handle]

---

## Testing Requirements

### Unit Tests
- [ ] [Test case 1]
- [ ] [Test case 2]

### Integration Tests
- [ ] [Test case 1]

### Manual Verification
- [ ] [Check 1]
- [ ] [Check 2]

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Code reviewed (self + agent)
- [ ] No regressions
- [ ] Beads status updated

---

## Notes

[Additional context, decisions made during implementation, blockers encountered]

---

## Beads Reference

```bash
# Update status
bd update [id] --status in_progress

# Add progress notes
bd update [id] --notes "COMPLETED: [what]. IN PROGRESS: [what]"

# Close when done
bd close [id] --reason "Implemented: [summary]"
```
