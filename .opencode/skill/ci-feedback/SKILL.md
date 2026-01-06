---
name: ci-feedback
description: Use this when the user mentions "CI failed", "test failed", "lint error", or "fix build". Parses failure logs and generates actionable fix prompts.
allowed-tools: "Read,Write,Grep,Glob,Bash"
version: "1.0.0"
---

# CI Feedback Skill

## Purpose

Parse CI/CD output (test failures, lint errors, build errors) and create actionable fix prompts for the AI to resolve.

## When to Use

- CI pipeline failed
- Tests failing locally or in CI
- Lint/type errors blocking merge
- Build failures

## CI Feedback Process

### Step 1: Gather CI Output

Get the CI failure output from user or fetch it:

```bash
# If user provides a file
cat ci-output.txt

# If GitHub Actions
gh run view --log-failed

# If local test run
npm test 2>&1 | tee test-output.txt
```

### Step 2: Parse Failure Type

Identify the failure category:

| Category | Indicators | Resolution Agent |
|----------|------------|------------------|
| Test Failures | `FAIL`, `AssertionError`, `expect` | developer |
| Lint Errors | `eslint`, `prettier`, `warning:` | developer |
| Type Errors | `TSxxxx`, `type 'X' is not assignable` | developer |
| Build Errors | `Cannot find module`, `SyntaxError` | developer |
| Security Issues | `vulnerability`, `CVE-` | reviewer |

### Step 3: Create Fix Prompts

For each failure, create a structured fix prompt:

```markdown
## CI Fix Required

### Failure Type: [Test/Lint/Type/Build]

### Error Details
```
[Paste exact error message]
```

### File Location
`path/to/file.ts:42`

### Context
[Any relevant context from the error]

### Fix Request
Please fix this [failure type] by:
1. [Specific action based on error]
2. Verify fix by running `[test command]`
3. Confirm the error is resolved
```

### Step 4: Route to Developer

Send fix prompts to developer agent:

> "Fix the following CI errors. After each fix, run the test to verify."

### Step 5: Verify Resolution

After fixes applied:

```bash
# Run the specific failing test
npm test -- --grep "failing test name"

# Or run full CI locally
npm run ci
```

## Output Format

```markdown
## CI Analysis Report

### Failures Found: X

| # | Type | File | Error | Status |
|---|------|------|-------|--------|
| 1 | Test | `file.ts:42` | Expected X got Y | ⏳ Fixing |
| 2 | Lint | `file.ts:15` | Missing semicolon | ✅ Fixed |

### Fix Progress
- [x] Fixed lint error in `file.ts`
- [ ] Fixing test failure in `test.ts`

### Commands Run
- `npm test -- file.test.ts` ✅
- `npm run lint:fix` ✅
```

## CI Tool Integration

### GitHub Actions
```bash
# Get failed run logs
gh run view <run-id> --log-failed

# Re-run failed jobs
gh run rerun <run-id> --failed
```

### Local CI Simulation
```bash
# Run the same checks CI would run
npm run lint && npm test && npm run build
```

## Quality Checklist

- [ ] All failures identified and categorized
- [ ] Each fix verified with test run
- [ ] No new errors introduced
- [ ] CI passes after all fixes
