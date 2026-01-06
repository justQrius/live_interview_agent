---
description: Start the Verification phase - test, review, and document
argument-hint: Optional scope to verify (defaults to all changes)
agent: orchestrator
---

# Prism Verification Phase

You are starting the Verification phase of the SDLC. This phase tests, reviews, and documents the completed work.

## Prerequisites

- All implementation stories should be complete
- Tests should be passing

Check prereqs:
```bash
bd stats  # Check completion status
bd list --status in_progress  # Should be empty
```

## Core Principles

- **Comprehensive testing**: Verify all acceptance criteria
- **Parallel reviews**: Multiple aspects simultaneously
- **Document thoroughly**: Enable future maintenance
- **Close the loop**: Complete all tracking items

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

## Phase 1: Preparation

**Goal**: Understand scope of verification

**Actions**:
1. Check session notes: `_prism/session-notes.md`
2. Get list of completed work:
   ```bash
   bd list --status closed
   bd show <epic-id>  # Full epic status
   ```
3. Identify all changes made (git diff against main)
4. Create TodoWrite verification checklist

---

## Phase 2: Test Verification

**Goal**: Ensure comprehensive test coverage and passing tests

**Actions**:
1. **Use the tester subagent** to verify test coverage and quality for the completed implementation.
   
   Provide the tester subagent with:
   - Epic: [epic-id] - [epic title]
   - Scope: All files modified in this implementation cycle
   
   Tell the tester subagent to:
   - Verify all acceptance criteria have corresponding tests
   - Check edge cases (null inputs, boundary values, error conditions)
   - Verify integration points are tested
   - Run the full test suite and report coverage metrics
   - Return: test results summary, coverage percentage, acceptance criteria test status, recommended additional tests

2. **Wait for tester subagent to complete**

3. Review test results:
   - If all tests pass: proceed to Phase 3
   - If failures found:
     - Create beads issue for each failure: `bd create "Bug: [failure description]"`
     - Decide: fix now (return to implementation) or document for later

---

## Phase 3: Parallel Quality Reviews

**Goal**: Multi-aspect code review for production readiness

**IMPORTANT**: Launch all 3 agents SIMULTANEOUSLY using parallel Task tool calls.
This is an elite orchestration pattern that reduces review time by 3x.

**Actions**:
1. **Use 3 reviewer subagents in parallel** - invoke ALL THREE simultaneously:

   **Use the reviewer subagent** for quality and simplicity:
   - Focus on: DRY, elegance, readability, maintainability
   - Use confidence scoring (0-100), only report issues >= 80
   - Return findings with file:line references and suggested improvements

   **Use another reviewer subagent** for bugs and security:
   - Focus on: logic errors, null handling, error handling, security vulnerabilities
   - Use confidence scoring (0-100), only report issues >= 80
   - Return findings with file:line references, severity, and fixes

   **Use a third reviewer subagent** for conventions and integration:
   - Focus on: CLAUDE.md compliance, pattern consistency, clean integration, API contracts
   - Use confidence scoring (0-100), only report issues >= 80
   - Return findings with file:line references and convention references

2. **Wait for all 3 reviewer subagents to complete** (they run in parallel)

3. Consolidate findings from all reviewers

4. Prioritize by severity (CRITICAL > IMPORTANT)

5. **Present consolidated findings to user** and ask what to address:
   - Which CRITICAL issues to fix now?
   - Which IMPORTANT issues to fix vs defer?

---

## Phase 4: Documentation & CLAUDE.md Update

**Goal**: Ensure documentation is complete and CLAUDE.md reflects current state

**Actions**:
1. **Use the documenter subagent** to update documentation for [epic-id]: [epic title]
   
   Provide the documenter subagent with:
   - Key features/components added
   - New APIs or commands
   - Configuration changes
   
   Tell the documenter subagent to:
   - Update README.md if needed (new features, setup changes)
   - Add/update API documentation for new endpoints or functions
   - Update any affected guides or tutorials
   - Verify code examples actually work
   - Return: list of files updated, summary of changes, documentation gaps needing user input

2. **Wait for documenter subagent to complete**

3. **Update CLAUDE.md** with discoveries from this cycle:
   - Add new commands/APIs to Quick Reference
   - Add new key files to Key Files section
   - Add new patterns to Conventions section
   - Add anti-patterns discovered during review to "Don't Do This" section

4. Verify all documentation is accurate

5. Test any code examples in documentation

---

## Phase 4.5: As-Built Sync

**Goal**: Ensure PRD and Architecture docs reflect what was actually built

This prevents "documentation drift" where the original design no longer matches the implementation.

**Actions**:
1. **Compare implementation against PRD** (`_prism/planning/prd.md`):
   - Were all requirements implemented as specified?
   - Were any requirements changed, added, or dropped during implementation?
   - Are acceptance criteria still accurate?

2. **Compare implementation against Architecture** (`_prism/architecture/architecture.md`):
   - Does the architecture diagram still match the code?
   - Were any components added, removed, or renamed?
   - Are the data models still accurate?

3. **If drift detected**, propose updates to user:
   > "The implementation differs from the original design:
   > - **[Change 1]**: PRD specified X, but we built Y instead because [reason]
   > - **[Change 2]**: Architecture showed component A, but we added component B
   > 
   > Would you like me to update the PRD and Architecture docs to reflect the 'as-built' state?"

4. **With user approval**, update:
   - `_prism/planning/prd.md` with actual requirements implemented
   - `_prism/architecture/architecture.md` with actual architecture
   - Add a "Change Log" section noting what changed and why

5. If no drift detected, confirm:
   > "✅ Implementation matches design documents. No updates needed."

---

## Phase 5: Final Validation

**Goal**: Get user sign-off

**CRITICAL**: Explicit approval required

**Actions**:
1. Present summary:
   - All tests passing
   - Review findings and actions taken
   - Documentation updates
   - Any remaining items
2. **Ask user for explicit sign-off**
3. If approved, proceed to completion

---

## Phase 6: Completion

**Goal**: Close out all tracking and document for future

**Actions**:
1. Close epic in beads:
   ```bash
   bd epic close-eligible  # Auto-close if all children done
   bd close <epic-id> --reason "Verified and complete: [summary]"
   ```
2. Sync beads to git:
   ```bash
   bd sync
   ```
3. Create final summary:
   - What was built (features, components)
   - What was tested (coverage, results)
   - What was documented (files updated)
   - Key decisions and lessons learned
4. Write to `_prism/session-notes.md` for future reference

---

## Phase Gate

**Exit Criteria for Verification Phase**:
- [ ] All tests passing
- [ ] All reviews completed
- [ ] Documentation updated
- [ ] User explicitly signed off
- [ ] Beads issues closed
- [ ] Beads synced to git

**SDLC Complete** 🎉

Ready to start new feature with `/prism-plan`
