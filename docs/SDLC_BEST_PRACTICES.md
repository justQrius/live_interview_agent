# SDLC Best Practices Constitution

This document defines the development standards for this project using the Prism SDLC framework.

## Core Principles

### 1. Phase Gates Are Mandatory
Progress through phases sequentially:
```
Planning → Solutioning → Implementation → Verification
```
Each phase has entry and exit criteria. Never skip phases without explicit approval.

### 2. Documentation Before Code
- Requirements documented in PRD before architecture
- Architecture approved before implementation begins
- No "code first, document later" approach

### 3. Test-Driven Development
```
1. Write failing test
2. Write minimum code to pass
3. Refactor while green
4. Repeat
```

### 4. Small, Focused Changes
- One story per PR/commit
- Stories should be completable in <1 day
- Break large features into smaller stories

## Phase Details

### Planning Phase
**Goal**: Define WHAT we're building

**Artifacts**:
- Product Requirements Document (PRD)
- User stories with acceptance criteria
- NFR targets (measurable)

**Exit Criteria**:
- PRD reviewed and approved
- All stories have acceptance criteria
- Scope is bounded

### Solutioning Phase
**Goal**: Define HOW we'll build it

**Artifacts**:
- Architecture document
- Component diagrams
- API contracts
- Technology decisions with rationale

**Exit Criteria**:
- Architecture reviewed and approved
- Trade-offs documented
- Stories created in task tracker

### Implementation Phase
**Goal**: Build the solution

**Process**:
1. Pick highest priority incomplete story
2. Write failing tests
3. Implement to pass tests
4. Code review
5. Mark story complete

**Exit Criteria**:
- All stories complete
- All tests passing
- Code reviewed

### Verification Phase
**Goal**: Validate the solution

**Activities**:
- Integration testing
- E2E testing
- Performance testing
- Security review
- Documentation review

**Exit Criteria**:
- All tests pass
- NFRs met
- Documentation complete

## Code Quality Standards

### All Languages
- Meaningful names (no single letters except loop indices)
- Functions do one thing
- Comments explain WHY, not WHAT
- No dead code
- Handle errors explicitly

### TypeScript/JavaScript
- Strict mode enabled
- ESLint with recommended rules
- Prettier for formatting
- Named exports preferred

### Python
- Type hints on all public functions
- Black formatter
- isort for imports
- Docstrings for public APIs

### Rust
- Clippy warnings are errors
- rustfmt for formatting
- Document public items
- Prefer `Result` over `panic!`

## Testing Standards

### Unit Tests
- Test behavior, not implementation
- One assertion per test (generally)
- Descriptive test names
- Mock external dependencies

### Integration Tests
- Test component interactions
- Use realistic test data
- Clean up test state

### E2E Tests
- Test critical user paths
- Stable selectors (data-testid)
- Reasonable timeouts

## Security Requirements

1. **Never log sensitive data** (credentials, PII, transcripts)
2. **Validate all inputs** at system boundaries
3. **Use secrets management** (not environment variables or config files)
4. **HTTPS/TLS** for all network communication
5. **Principle of least privilege** for all components

## Git Workflow

### Commit Messages
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Branch Strategy
- `main`: Production-ready code
- `feature/*`: Feature branches
- `fix/*`: Bug fix branches

### Code Review
- All changes require review (or self-review with checklist)
- Address all comments before merge
- Squash commits on merge

## Definition of Done

A story is DONE when:
- [ ] Code complete and compiles
- [ ] Unit tests written and passing
- [ ] Integration tests passing (if applicable)
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] No new linting warnings
- [ ] Story marked complete in tracker

## Continuous Improvement

### Retrospectives
After each phase completion:
1. What went well?
2. What could be improved?
3. What will we try differently?

### Learning Capture
Document learnings in `_prism/learnings/`:
- `project.md`: Project-specific learnings
- `sessions/`: Session-specific notes
- `skills/`: Reusable patterns and skills

---

*This is a living document. Update as the team learns and improves.*
