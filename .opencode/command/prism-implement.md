---
description: Start the Implementation phase - develop stories using TDD
argument-hint: Story ID or story file to implement
agent: developer
---

# Prism Implementation Phase

You are starting the Implementation phase of the SDLC. This phase develops stories using Test-Driven Development.

## Prerequisites

- Architecture must exist at `_prism/architecture/architecture.md`
- Story must exist in beads or as a story file

Check prereqs:
```bash
bd ready  # Find stories ready to implement
bd show <story-id>  # Get story details
```

## Core Principles

- **TDD always**: Write failing test first, then implement
- **Follow conventions**: Check CLAUDE.md before coding
- **Incremental progress**: Update beads after each criterion
- **Review before commit**: Self-review, then agent review

---

## Phase 0: Environment Check

**Goal**: Verify beads is available or set up fallback tracking

**Actions**:
1. Check if beads CLI is installed:
   ```bash
   command -v bd >/dev/null 2>&1 && echo "BEADS_AVAILABLE" || echo "BEADS_MISSING"
   ```

2. If beads available, check if initialized:
   ```bash
   [ -d ".beads" ] && echo "BEADS_INITIALIZED" || echo "BEADS_NOT_INITIALIZED"
   ```

3. **Handle each case**:
   - **BEADS_AVAILABLE + INITIALIZED**: ✅ Proceed with beads commands
   - **BEADS_AVAILABLE + NOT_INITIALIZED**: Ask user if they want to run `bd init`
   - **BEADS_MISSING**: Inform user and use `_prism/tasks.md` fallback

4. Set `$TRACKING_MODE` for use in later phases

See `templates/beads-check.md` for detailed fallback command mapping.

---

## Phase 1: Story Selection

**Goal**: Choose and understand the story to implement

**Actions**:
1. If $ARGUMENTS provided, use that story ID
2. Otherwise, run `bd ready` and present options
3. User selects story (or confirm provided one)
4. Get full context: `bd show <story-id>`
5. Mark story in progress:
   ```bash
   bd update <story-id> --status in_progress
   ```

---

## Phase 2: Preparation

**Goal**: Understand requirements and codebase context

**Actions**:
1. Create TodoWrite list from acceptance criteria
2. Read architecture: `_prism/architecture/architecture.md`
3. Read CLAUDE.md for project conventions
4. Search for similar implementations
5. Identify files to create/modify

---

## Phase 3: TDD Development Loop

**Goal**: Implement each acceptance criterion with tests first

**Option A: Use isolated developer subagent via Task tool** (recommended for complex stories):

```
Use Task tool to spawn isolated developer subagent:
- Agent: developer
- Prompt: "Implement story [story-id]: [story title]

  Acceptance Criteria:
  - AC-1: [criterion]
  - AC-2: [criterion]
  - AC-3: [criterion]
  
  Context:
  - Architecture: [relevant section from _prism/architecture/architecture.md]
  - Conventions: Follow CLAUDE.md guidelines
  
  Tasks:
  - For EACH acceptance criterion, follow TDD: write failing test → implement → verify → refactor
  - Run full test suite after ALL criteria are complete
  - Update beads: bd update [story-id] --notes 'COMPLETED: [summary]'
  
  Return: implementation summary with files modified and tests added"
```

**Why Task tool**: Developer runs in isolated context. Implementation details 
don't pollute main orchestration session. Complex TDD loops contained.

**Option B: Manual TDD loop** (for simpler stories or when you want more control):

For each acceptance criterion:

### 3a. Write Failing Test
1. Create test that captures the criterion
2. Run test suite - confirm new test fails
3. Mark criterion todo as in-progress

### 3b. Implement
1. Write minimum code to pass test
2. Follow project conventions (CLAUDE.md)
3. Handle errors appropriately

### 3c. Verify
1. Run test - confirm it passes
2. Run full test suite
3. Mark criterion todo complete

### 3d. Refactor (if needed)
1. Improve code quality
2. Ensure tests still pass

**Update beads after each criterion**:
```bash
bd update <story-id> --notes "COMPLETED: AC-1. IN PROGRESS: AC-2"
```

---

## Phase 4: Self-Review

**Goal**: Ensure quality before agent review

**Actions**:
1. Run full test suite
2. Check all acceptance criteria met
3. Verify CLAUDE.md compliance
4. Review for obvious issues

---

## Phase 5: Agent Review

**Goal**: Get thorough code review before completing

**Actions**:
1. **Spawn isolated reviewer subagent using Task tool**:
   
   ```
   Use Task tool:
   - Agent: reviewer
   - Prompt: "Review code changes for story [story-id]: [story title]
     
     Files modified: [file1.ts, file2.ts, test files]
     
     Review for:
     - Code quality, bugs, security
     - Conventions compliance (CLAUDE.md)
     - Test coverage
     
     Use confidence scoring (0-100), only report issues >= 80
     Return: findings organized by severity (CRITICAL: 90-100, IMPORTANT: 80-89)"
   ```
   
   **Why Task tool**: Reviewer runs in isolated context. Review findings 
   consolidated cleanly without polluting main session.

2. **Collect reviewer subagent results** when Task completes

3. Address feedback:
   - For each issue include: file:line, description, suggested fix

2. **Wait for reviewer agent to complete**

3. Review findings and address issues:
   - Fix all CRITICAL issues immediately
   - Fix IMPORTANT issues or document why deferring

4. Re-run tests after fixes

5. If significant changes were made, consider a second review pass

---

## Phase 5.5: Capture Learnings

Run `/prism-reflect` to capture implementation insights:
- Code patterns or idioms that worked well?
- API gotchas or hidden behaviors?
- Debugging lessons?
- Testing strategies that were effective?

---

## Phase 6: Completion

**Goal**: Mark story complete and prepare for next

**Actions**:
1. Close story in beads:
   ```bash
   bd close <story-id> --reason "Implemented: [summary]"
   bd ready  # Check newly unblocked work
   ```
2. Provide implementation summary:
   - What was built
   - Files modified
   - Tests added
   - Key decisions
3. Write session notes

---

## Phase Gate

**Exit Criteria for Story Implementation**:
- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Code reviewed (self + agent)
- [ ] Beads status updated

**Next Actions**:
- `/prism-implement [next-story-id]` for next story
- `/prism-verify` when all stories complete
