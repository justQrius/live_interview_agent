---
description: Parse CI failures and generate fix prompts for the developer agent
argument-hint: CI output file or failure type
agent: developer
---

# Prism CI Feedback Command

Parse CI/CD output (test failures, lint errors, build errors) and route to developer for fixes.

## Usage

```
/prism-ci                    # Interactive - asks for CI output
/prism-ci test-output.txt    # Parse a specific output file
/prism-ci --github           # Fetch from GitHub Actions
```

---

## Phase 1: Gather CI Output

**Goal**: Get the failure output to parse

**Actions**:
1. If argument provided, read that file
2. If `--github` flag, run:
   ```bash
   gh run view --log-failed
   ```
3. If no argument, ask user:
   > "Please paste or provide the CI failure output, or specify a file path."

---

## Phase 2: Parse Failures

**Goal**: Identify and categorize all failures

**Actions**:
1. Parse the output for failure patterns:
   - Test failures: `FAIL`, `AssertionError`, `expect(`
   - Lint errors: `eslint`, `error:`, `warning:`
   - Type errors: `TS\d+`, `type 'X' is not assignable`
   - Build errors: `Cannot find module`, `SyntaxError`

2. For each failure, extract:
   - File path and line number
   - Error message
   - Expected vs actual (for tests)
   - Error code (for types/lint)

3. Create failure summary table

---

## Phase 3: Generate Fix Prompts

**Goal**: Create actionable prompts for each failure

**Actions**:
For each failure:
1. Create structured fix request with:
   - Exact error message
   - File location
   - Specific fix action
   - Verification command

2. Route to developer agent for implementation

---

## Phase 4: Execute Fixes

**Goal**: Apply fixes and verify

**Actions**:
1. Developer agent fixes each issue
2. After each fix, run verification:
   ```bash
   npm test -- [specific test]
   # or
   npm run lint -- [specific file]
   ```
3. Track fix progress in TodoWrite

---

## Phase 5: Final Verification

**Goal**: Confirm CI would pass

**Actions**:
1. Run full CI locally:
   ```bash
   npm run ci
   # or
   npm run lint && npm test && npm run build
   ```

2. Report results:
   ```markdown
   ## CI Fix Results
   
   | Issue | Status |
   |-------|--------|
   | Test: UserService | ✅ Fixed |
   | Lint: Missing semi | ✅ Fixed |
   
   **Local CI**: ✅ All checks pass
   ```

3. If using GitHub, suggest re-run:
   ```bash
   gh run rerun <run-id> --failed
   ```

---

## Related Skill

This command uses the `ci-feedback` skill. See `skills/ci-feedback/SKILL.md` for detailed parsing patterns.
