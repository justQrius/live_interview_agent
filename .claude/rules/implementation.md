---
paths:
  - "src/**"
  - "src-tauri/**"
  - "sidecar/**"
---

# Implementation Phase Rules

When implementing code:

## TDD Workflow
1. Write failing test first
2. Implement minimum code to pass
3. Refactor while tests stay green
4. Commit with story reference

## Code Quality
- All functions have type hints (Python) or types (TypeScript/Rust)
- No TODO comments without linked story
- Error handling at all boundaries
- Logging at appropriate levels

## Project-Specific Conventions

### TypeScript/React
- Functional components with hooks
- Zustand for state management (NOT Redux)
- Tailwind CSS only (NO CSS modules)
- Named exports for components

### Rust (Tauri)
- Commands in `src-tauri/src/commands/`
- Use keyring crate for secrets
- Handle errors with `Result<T, String>`

### Python (Sidecar)
- Async/await for all I/O
- One module per concern
- pytest for testing
- Type hints required

## Security Requirements
- Never log transcripts or answers
- WebSocket on localhost only (127.0.0.1)
- API keys via OS keychain only

## Before Completing Story
- All tests pass
- Code reviewed (or self-reviewed for solo work)
- Update `_prism/tasks.md` with completion status
