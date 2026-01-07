# AGENTS.md

## Setup Commands

- Install dependencies: `[PACKAGE_MANAGER] install`
- Start development server: `[PACKAGE_MANAGER] dev`
- Run tests: `[PACKAGE_MANAGER] test`
- Build for production: `[PACKAGE_MANAGER] build`

## Code Style

- [Language configuration (e.g., TypeScript strict mode)]
- [Quote preference]
- [Semicolon preference]
- [Functional vs OOP patterns]
- Follow conventions in CLAUDE.md

## Testing Instructions

- All tests must pass before committing
- Run `[TEST_COMMAND]` for full test suite
- Use TDD: write failing test first, then implement
- Coverage target: [X]%

## File Organization

```
src/           # Source code
tests/         # Test files
docs/          # Documentation
_prism/        # Prism SDLC artifacts (PRD, architecture, etc.)
```

## Key Patterns

- [Pattern 1]
- [Pattern 2]
- [Pattern 3]

## Don't Do This

- Don't commit without running tests
- Don't bypass linting
- Don't expose secrets in code
- Don't ignore CLAUDE.md conventions

## Prism SDLC Workflow

This project uses the Prism SDLC framework. Follow this phased workflow:

| Phase | Command | Artifact | Agent |
|-------|---------|----------|-------|
| Planning | `/prism-plan` | `_prism/planning/prd.md` | pm |
| Solutioning | `/prism-solution` | `_prism/architecture/` | architect |
| Implementation | `/prism-implement` | Code + Tests | developer |
| Verification | `/prism-verify` | Reviewed + Documented | tester, reviewer |

## Component Hierarchy

Prism follows a **Skills → Subagents → Commands** pattern:

```
Skills (foundation) → Subagents (isolated execution) → Commands (user trigger)
```

**Build in reverse**: Create skills first, then subagents that use them, then commands that orchestrate.

## Intelligent Subagent Selection

**Use these subagents proactively based on context** (they run in isolated context):

| Situation | Use This Subagent |
|-----------|------------------|
| Feature ideas, requirements gathering | **pm** subagent |
| System design, "how to build", architecture | **architect** subagent |
| Writing code, implementing features, TDD | **developer** subagent |
| Code review, quality check, security audit | **reviewer** subagent |
| Running tests, verifying coverage | **tester** subagent |
| Exploring codebase, understanding existing code | **explorer** subagent |
| Writing docs, updating README | **documenter** subagent |
| Session management, phase transitions | **orchestrator** (main session) |

## Skill Auto-Triggering

**These skills activate automatically based on context:**

| Skill | Triggers When... |
|-------|-----------------|
| `create-spec` | Vague ideas need structured discovery |
| `create-prd` | Requirements need formal documentation |
| `create-architecture` | System design decisions needed |
| `dev-story` | Implementing stories with TDD |
| `code-review` | Code written, needs quality check |
| `ci-feedback` | CI fails, tests broken |
| `documentation` | Docs missing or outdated |
| `session-start` | Session begins, restore context |
| `beads-integration` | Task tracking needed |
| `phase-gate` | Phase transition, validate requirements |

## Proactive Behavior

1. **Infer intent** - Don't wait for explicit commands
2. **Chain actions** - Code → Review → Test → Document
3. **Announce delegation** - "I'll use the architect agent for this"
4. **Check phase gates** - Run phase-gate skill before transitions

## Prism Non-Negotiables

> These rules are non-negotiable. Violation blocks progress.

1. **Never advance phases without meeting gates** - Phase-gate skill must pass
2. **Always create spikes for HIGH-risk integrations** - Document results before proceeding
3. **Always run tests + CI before done** - No exceptions
4. **Never introduce secrets in code** - Use env vars + secret managers
5. **Prefer adapters around external APIs** - Isolate integrations
6. **Document decisions, not just code** - Create ADRs for significant choices

## References

- [CLAUDE.md](CLAUDE.md) - Complete conventions
- [docs/SDLC_BEST_PRACTICES.md](docs/SDLC_BEST_PRACTICES.md) - SDLC constitution
