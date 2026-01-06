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

## Prism SDLC

This project uses the Prism SDLC framework. Follow this workflow:

1. **Planning**: Create PRD in `_prism/planning/prd.md`
2. **Solutioning**: Design architecture in `_prism/architecture/`
3. **Implementation**: TDD with story tracking
4. **Verification**: Test coverage and documentation

See CLAUDE.md for detailed conventions.
