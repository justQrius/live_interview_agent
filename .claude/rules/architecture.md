---
paths:
  - "_prism/architecture/**"
---

# Architecture Phase Rules

When working on architecture documents:

## Design Principles
- Prefer simplicity over cleverness
- Document trade-offs explicitly
- Consider all NFRs from PRD
- Design for testability

## Architecture Document Quality
- Component diagrams with clear boundaries
- Data flow diagrams for key operations
- API contracts between components
- Technology choices with rationale

## For This Project (Live Interview Agent)
- Maintain sidecar pattern (Tauri + Python)
- WebSocket IPC on localhost:8765 only
- Privacy-first: no persistent transcript storage
- Platform-specific audio handling (WASAPI/CoreAudio/PulseAudio)

## Phase Gate
- Architecture must be approved before Implementation
- Create story breakdown in `_prism/tasks.md`
- Update `_prism/status.yaml` when solutioning completes
