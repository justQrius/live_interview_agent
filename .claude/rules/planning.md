---
paths:
  - "_prism/planning/**"
  - "_prism/discovery/**"
---

# Planning Phase Rules

When working on files in the planning directory:

## Requirements Gathering
- Focus on WHAT, not HOW
- Capture user goals and success criteria
- Identify constraints and NFRs
- Document personas and use cases

## PRD Quality Checks
- All user stories have acceptance criteria
- NFRs are measurable (e.g., "<5s latency" not "fast")
- Dependencies are identified
- Scope is clearly bounded

## Phase Gate
- PRD must be approved before moving to Solutioning
- Use `/prism-solution` only after planning complete
- Update `_prism/status.yaml` when planning completes
