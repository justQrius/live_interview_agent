# Code Review: [Scope/PR/Feature]

> **Reviewer**: [Name/Agent]
> **Date**: [Date]
> **Files Reviewed**: [Count]
> **Verdict**: ✅ Approved | ⚠️ Changes Requested | ❌ Blocked

---

## Summary

**Total Issues Found**: [X] ([Y] critical, [Z] important)

| Category | Critical | Important | Passed |
|----------|----------|-----------|--------|
| Quality | [X] | [X] | [X] |
| Bugs | [X] | [X] | [X] |
| Security | [X] | [X] | [X] |
| Conventions | [X] | [X] | [X] |

---

## Critical Issues (Confidence 90-100)

> These MUST be fixed before merge

### Issue 1: [Title]

| Attribute | Value |
|-----------|-------|
| **Confidence** | [95] |
| **File** | `path/to/file.ts:42` |
| **Category** | Bug / Security / Convention |
| **Guideline** | [CLAUDE.md rule or security standard] |

**Problem**:
```typescript
// Current code
const data = JSON.parse(userInput);
```

**Fix**:
```typescript
// Suggested fix
try {
  const data = JSON.parse(userInput);
} catch (e) {
  throw new ValidationError('Invalid JSON input');
}
```

**Why**: [Explanation of why this is a problem and why the fix addresses it]

---

### Issue 2: [Title]

| Attribute | Value |
|-----------|-------|
| **Confidence** | [92] |
| **File** | `path/to/file.ts:78` |
| **Category** | |
| **Guideline** | |

**Problem**:
```
// Current code
```

**Fix**:
```
// Suggested fix
```

---

## Important Issues (Confidence 80-89)

> These SHOULD be fixed, but are lower risk

### Issue 3: [Title]

| Attribute | Value |
|-----------|-------|
| **Confidence** | [85] |
| **File** | `path/to/file.ts:123` |
| **Category** | |
| **Guideline** | |

**Problem**:
[Description]

**Recommendation**:
[How to improve]

---

## Passed Checks ✅

> What was verified and found acceptable

- [x] **CLAUDE.md Conventions**: Code follows project style guidelines
- [x] **Error Handling**: Errors are caught and handled appropriately
- [x] **Security**: No obvious vulnerabilities (injection, XSS, etc.)
- [x] **Performance**: No obvious performance issues
- [x] **Test Coverage**: Changes are tested
- [x] **Documentation**: Code is documented where needed

---

## Files Reviewed

| File | Lines Changed | Issues |
|------|---------------|--------|
| `path/to/file1.ts` | +50, -10 | 2 |
| `path/to/file2.ts` | +20, -5 | 0 |
| `path/to/test.ts` | +30, -0 | 0 |

---

## Recommendations

> Non-blocking suggestions for improvement

1. **[Recommendation]**: [Suggestion for future improvement]
2. **[Recommendation]**: [Suggestion for future improvement]

---

## Resolution Tracking

| Issue | Status | Resolved In |
|-------|--------|-------------|
| Issue 1 | ⬜ Open / ✅ Fixed / 🚫 Won't Fix | [Commit/PR] |
| Issue 2 | ⬜ Open / ✅ Fixed / 🚫 Won't Fix | [Commit/PR] |
| Issue 3 | ⬜ Open / ✅ Fixed / 🚫 Won't Fix | [Commit/PR] |

---

## Final Verdict

**[✅ APPROVED / ⚠️ CHANGES REQUESTED / ❌ BLOCKED]**

[Summary statement explaining the verdict and next steps]

---

## Reviewer Notes

[Any additional context, observations, or feedback for the author]
