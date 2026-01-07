---
paths:
  - "tests/**"
  - "sidecar/tests/**"
  - "src/**/*.test.*"
  - "src/**/*.spec.*"
---

# Verification Phase Rules

When working on tests and verification:

## Test Categories
- **Unit Tests**: Isolated component testing
- **Integration Tests**: Component interaction testing
- **E2E Tests**: Full pipeline testing

## Coverage Targets
| Layer | Target |
|-------|--------|
| Python core modules | >80% |
| TypeScript components | >70% |
| Rust commands | Unit tests required |

## Test Quality
- Tests should be deterministic
- Mock external dependencies (Gemini API, audio devices)
- Test edge cases and error conditions
- Use fixtures for common test data

## NFR Verification
- Latency: <5 seconds P95
- RAM: <500MB
- CPU idle: <10%
- Session stability: 2 hours, zero crashes

## Before Marking Complete
- All automated tests pass
- Manual testing checklist completed
- Performance benchmarks meet NFRs
- Update `_prism/status.yaml` to reflect verification status
