# Code Review Patterns

Common patterns and techniques for effective code review.

## Parallel Review Pattern

For large changes, launch multiple reviewers with different focuses:

**Using the Task tool, launch 3 reviewer agents in parallel:**

### Focus 1: Code Quality & Simplicity
```
Review code quality for [scope].

Focus on:
- DRY: Is code duplicated anywhere that should be extracted?
- Elegance: Is the solution unnecessarily complex when a simpler approach exists?
- Readability: Can a new developer understand this code without explanation?
- Maintainability: Will this be easy to modify in the future?

Use confidence scoring (0-100). Only report issues >= 80 confidence.
Return findings with file:line references and suggested improvements.
```

### Focus 2: Bugs & Security
```
Review for bugs and security issues in [scope].

Focus on:
- Logic errors: Any incorrect conditionals, off-by-one errors, race conditions?
- Null handling: Are null/undefined cases properly handled?
- Error handling: Are errors caught and handled appropriately?
- Security: Any injection vulnerabilities, auth bypass, data exposure?

Use confidence scoring (0-100). Only report issues >= 80 confidence.
Return findings with file:line references, severity, and fixes.
```

### Focus 3: Conventions & Integration
```
Review conventions and integration for [scope].

Focus on:
- CLAUDE.md compliance: Does code follow project conventions?
- Pattern consistency: Does it match existing patterns in codebase?
- Integration: Does it integrate cleanly without breaking changes?
- API contracts: Are interfaces consistent with existing APIs?

Use confidence scoring (0-100). Only report issues >= 80 confidence.
Return findings with file:line references and convention references.
```

**After all agents complete:**
1. Consolidate findings from all reviewers
2. Deduplicate overlapping issues
3. Prioritize by confidence score (highest first)
4. Present unified report to user

---

## Confidence Scoring Guide

### 91-100: Critical - Must Fix
- Explicit guideline violation documented in CLAUDE.md
- Security vulnerability (injection, auth bypass, etc.)
- Certain production bug (will cause crashes or data loss)
- Breaking change to public API

### 80-90: Important - Should Fix
- Likely bug based on code patterns
- Missing error handling for common cases
- Significant code smell (large duplicate blocks)
- Performance issue with clear impact

### 51-79: Valid but Skip
- Stylistic preference not in guidelines
- Minor optimization opportunity
- Could be improved but works correctly

### 0-50: Filter Out
- Pre-existing issue (not in current diff)
- False positive from pattern matching
- Subjective opinion without guideline backing

---

## Review Categories

### Security Review Checklist
- [ ] No SQL/command injection vulnerabilities
- [ ] User input properly validated and sanitized
- [ ] Authentication/authorization correctly implemented
- [ ] Sensitive data not logged or exposed
- [ ] CSRF/XSS protections in place (for web)
- [ ] Secrets not hardcoded

### Performance Review Checklist
- [ ] No N+1 query patterns
- [ ] Appropriate use of caching
- [ ] No unnecessary re-renders (for UI)
- [ ] Database queries optimized
- [ ] Memory leaks addressed

### Convention Review Checklist
- [ ] Import order follows project standard
- [ ] Naming conventions followed
- [ ] Error handling pattern consistent
- [ ] Testing pattern consistent
- [ ] File structure follows project organization

---

## Report Template

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
- **Guideline**: [Specific rule violated or security concern]
- **Problem**: 
  ```typescript
  // Current code showing the issue
  ```
- **Fix**: 
  ```typescript
  // Suggested corrected code
  ```

---

### Important Issues (80-89)

#### Issue 2: [Title]
...

---

### Passed Checks ✅
- [x] CLAUDE.md conventions followed
- [x] No security vulnerabilities
- [x] Error handling present
- [x] Tests cover changes

---

### Recommendations
- [Optional improvements not requiring changes]
```

---

## Anti-Patterns to Flag

### Always Report (90+ confidence)
- Hardcoded credentials or secrets
- SQL string concatenation with user input
- Missing error handling on I/O operations
- Direct DOM manipulation in React/Vue (bypassing virtual DOM)
- Sync I/O in async contexts

### Usually Report (80+ confidence)
- Empty catch blocks
- Console.log statements in production code
- TODO comments without associated issue tracking
- Magic numbers without constants
- Deep nesting (> 3 levels)
