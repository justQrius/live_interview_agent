---
name: code-review
description: Use this when the user mentions "review code", "check PR", "verify changes", or "audit security". Performs comprehensive code review with confidence scoring.
allowed-tools: "Read,Glob,Grep,Bash"
version: "1.0.0"
---

# Code Review - Quality Validation Workflow

Guides systematic code review with confidence-based issue filtering.

## Overview

This skill:
- Reviews code against project guidelines
- Detects bugs and security issues
- Uses confidence scoring to filter noise
- Reports only high-priority issues

## Prerequisites

- Code changes to review (git diff, PR, or specified files)
- Access to CLAUDE.md for project conventions

## Instructions

### Step 1: Identify Scope

Determine what to review:

```bash
# Default: unstaged changes
git diff

# Staged changes
git diff --staged

# Specific PR
git diff main..feature-branch

# Specific files
# User specifies files directly
```

### Step 2: Read Project Guidelines

Read CLAUDE.md for:
- Code style conventions
- Framework patterns
- Forbidden practices
- Required patterns

### Step 3: Review Categories

Check each category:

**1. Project Guidelines Compliance**
- Import patterns
- Framework conventions
- Language style
- Naming conventions
- Error handling patterns

**2. Bug Detection**
- Logic errors
- Null/undefined handling
- Race conditions
- Security vulnerabilities
- Performance problems

**3. Code Quality**
- Code duplication
- Missing error handling
- Test coverage
- Accessibility issues

### Step 4: Confidence Scoring

Rate each issue 0-100:

| Score | Meaning | Action |
|-------|---------|--------|
| 0-25 | False positive | Skip |
| 26-50 | Minor nitpick | Skip |
| 51-75 | Valid, low impact | Skip |
| 76-90 | Important | Report |
| 91-100 | Critical | Report |

**Only report issues with confidence ≥ 80**

### Step 5: Report

```markdown
## Code Review: [scope]

### Summary
- **Files reviewed**: X
- **Issues found**: Y (Z critical)
- **Verdict**: [Approve / Changes Requested]

---

### Critical Issues (90-100)

#### Issue 1: [Title]
- **Confidence**: 95
- **File**: `path/to/file.ts:42`
- **Category**: [Bug / Security / Convention]
- **Guideline**: [Specific rule violated]
- **Problem**: 
  ```typescript
  // Current code
  ```
- **Fix**: 
  ```typescript
  // Suggested fix
  ```

---

### Important Issues (80-89)

#### Issue 2: [Title]
...

---

### Passed Checks ✅
- [ ] CLAUDE.md conventions followed
- [ ] No security vulnerabilities
- [ ] Error handling present
- [ ] Tests cover changes

---

### Recommendations
- [Optional improvements not requiring changes]
```

## Parallel Review Pattern

For large changes, invoke multiple reviewers:

```
Launch 3 reviewer agents in parallel:
- Focus 1: Code quality and simplicity
- Focus 2: Bug detection and edge cases
- Focus 3: Security and performance
```

Consolidate findings and deduplicate before reporting.

---

## Additional Resources

### Reference Files

For detailed patterns and prompt templates, consult:

- **`references/patterns.md`** - Parallel review prompts, confidence scoring guide, and anti-patterns

### When to Read References

- Doing parallel reviews → Get exact agent prompts from patterns.md
- Need scoring guidance → Read confidence scoring guide
- Unsure what to flag → Check anti-patterns list

---

## Output

- Review report with scored issues
- Verdict: Approve or Changes Requested
- Specific fix suggestions for each issue

## Quality Standards

- Only report confidence ≥ 80 issues
- Quality over quantity
- Include specific line numbers
- Provide concrete fix suggestions
- Group by severity

