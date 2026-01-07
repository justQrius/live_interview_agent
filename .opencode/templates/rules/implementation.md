---
paths: src/**/*.{ts,js,tsx,jsx,py,go,rs}
---
# Implementation Rules

## TDD Required

Follow Test-Driven Development:
1. Write failing test first
2. Implement minimum code to pass
3. Refactor for quality
4. Verify all tests pass

## Integration Checkpoints

- Integrate after each user story (not at the end)
- Run integration tests before marking complete
- Test on all target platforms if cross-platform

## Defensive Programming

- Validate inputs at boundaries
- Use context managers for cleanup
- Timeouts on ALL external calls
- Retry only idempotent operations
- Never block async event loops

## Code Review Checklist

- [ ] Tests updated and passing
- [ ] Error handling + logging added
- [ ] Resource cleanup verified
- [ ] Platform compatibility checked
- [ ] Security review (authz, input validation, secrets)
- [ ] Performance impact considered

## AI-Generated Code

- Always run tests (AI can hallucinate APIs)
- Review carefully before committing
- Document what was AI-generated
- Never paste secrets into AI tools

## Gate Checklist

Before proceeding to Verification:
- [ ] CI pipeline green
- [ ] Tests added for new code
- [ ] Code review completed
- [ ] Risk items addressed

## Reference

See `docs/SDLC_BEST_PRACTICES.md` for complete guidelines.
