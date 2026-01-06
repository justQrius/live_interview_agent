---
name: dev-story
description: Use this when the user mentions "implement story", "build feature", "TDD", or "fix bug". Implements code using Test-Driven Development loops.
allowed-tools: "Read,Write,Edit,Glob,Grep,Bash,TodoWrite"
version: "1.0.0"
---

# Dev Story - TDD Implementation Workflow

Guides implementation of stories using Test-Driven Development practices.

## Overview

This skill:
- Reads story requirements and acceptance criteria
- Creates failing tests first
- Implements to pass tests
- Refactors for quality
- Updates beads status

## Prerequisites

- Story file or beads issue with acceptance criteria
- Architecture document for context

## Instructions

### Step 1: Preparation

1. **Read the story**:
   ```bash
   bd show <story-id>
   ```
   Or read story file with acceptance criteria.

2. **Create checklist from acceptance criteria**:
   Use TodoWrite to track each criterion.

3. **Review architecture**:
   Read `_prism/architecture/architecture.md` for context.

### Step 2: Understand Codebase

- Search for similar implementations
- Read relevant existing files
- Note conventions to follow (check CLAUDE.md)
- Identify files to create/modify

### Step 3: TDD Loop

For each acceptance criterion:

#### a. Write Failing Test
```
1. Create test that captures the criterion
2. Run test - confirm it fails
3. Mark todo as in-progress
```

#### b. Implement
```
1. Write minimum code to pass test
2. Follow project conventions
3. Handle errors appropriately
```

#### c. Verify
```
1. Run test - confirm it passes
2. Run full test suite
3. Mark criterion complete
```

#### d. Refactor (if needed)
```
1. Improve code quality
2. Ensure tests still pass
```

### Step 4: Final Verification

1. Run full test suite
2. Verify all acceptance criteria met
3. Self-review for quality (CLAUDE.md compliance)

### Step 5: Update Beads

```bash
# Mark story as done
bd update <story-id> --status done --notes "COMPLETED: [summary of implementation]"

# Check for newly unblocked work
bd ready
```

## Output

Provide implementation summary:

```markdown
## Implementation Summary

### What Was Built
- [Feature/change 1]
- [Feature/change 2]

### Files Modified
| File | Changes |
|------|---------|
| `path/to/file.ts` | [Description] |
| `path/to/test.ts` | [Tests added] |

### Tests Added
- `test/path/file.test.ts`: [Coverage notes]

### Acceptance Criteria Status
| Criterion | Status |
|-----------|--------|
| AC-1: [Description] | ✅ |
| AC-2: [Description] | ✅ |

### Key Decisions
- [Decision]: [Rationale]

### Beads Updated
- `bd update <id> --status done`
```

## Error Handling

### Tests Won't Pass
1. Read error messages carefully
2. Check for missing dependencies
3. Verify test setup is correct
4. If blocked, update beads status:
   ```bash
   bd update <story-id> --status blocked --notes "Blocked: [reason]"
   ```

### Can't Meet Acceptance Criteria
1. Document what's not achievable
2. Discuss with user before marking incomplete
3. Create follow-up issue if needed

## Quality Checklist

- [ ] All tests pass
- [ ] All acceptance criteria met
- [ ] Code follows CLAUDE.md conventions
- [ ] No hardcoded values
- [ ] Comprehensive error handling
- [ ] Comments explain "why" not "what"
- [ ] Beads status updated
