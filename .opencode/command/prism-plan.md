---
description: Start the Planning phase - gather requirements and create PRD
argument-hint: Optional feature or product description
agent: pm
---

# Prism Planning Phase

You are starting the Planning phase of the SDLC. This phase gathers requirements and produces a Product Requirements Document (PRD).

## Core Principles

- **Ask clarifying questions**: Identify all ambiguities before documenting
- **Wait for answers**: Never assume - get explicit confirmation
- **Use beads**: Track all requirements as issues for continuity

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
   - **BEADS_MISSING**: Inform user and use `_prism/tasks.md` fallback:
     > "Beads CLI not found. Using `_prism/tasks.md` for task tracking.
     > For persistent tracking, install: `npm install -g @beads/bd`"

4. Set `$TRACKING_MODE` to either `"beads"` or `"fallback"` for use in later phases

See `templates/beads-check.md` for detailed fallback command mapping.

---

## Phase 1: Discovery

**Goal**: Understand what needs to be built

Initial request: $ARGUMENTS

**Actions**:
1. Create TodoWrite list with planning phases
2. Ask the user:
   - What problem are we solving?
   - Who are the target users?
   - What defines success?
   - What are the constraints?
   - What's the timeline/priority?
3. **WAIT FOR ANSWERS** - do not proceed without user input

---

## Phase 2: Requirements Gathering

**Goal**: Derive structured requirements from user answers

**Actions**:
1. Synthesize answers into:
   - Functional requirements (what it does)
   - Non-functional requirements (how it performs)
   - User personas and their needs
   - Use cases and user journeys
2. Present summary to user for validation
3. **Ask if anything is missing** before documenting

---

## Phase 3: PRD Creation

**Goal**: Document complete requirements

**Actions**:
1. **Use the pm subagent** to create a comprehensive PRD for [feature name] based on these requirements:
   
   Gather these inputs from the discovery phase and pass to the pm subagent:
   - Problem: [problem statement from Phase 1]
   - Users: [target users from Phase 1]
   - Success criteria: [what defines success]
   - Constraints: [identified constraints]
   
   Tell the pm subagent to:
   - Use the template at templates/prd-template.md
   - Write the output to _prism/planning/prd.md
   - Include problem statement, goals/non-goals, user personas, functional requirements with acceptance criteria, non-functional requirements with metrics, success metrics, and open questions
   - Return a summary of the PRD with the key requirements listed

2. After the pm subagent completes, verify the PRD was written to `_prism/planning/prd.md`

3. Review the PRD for completeness - it must include:
   - Problem statement
   - Goals and non-goals
   - User personas
   - Functional requirements with acceptance criteria
   - Non-functional requirements with metrics
   - Success metrics
   - Open questions

---

## Phase 4: Validation & Issue Creation

**Goal**: Get approval and create tracking issues

**CRITICAL**: Do NOT proceed without explicit approval

**Actions**:
1. Present PRD summary to user
2. **Ask for explicit approval** to proceed
3. After approval, create tracking issues based on `$TRACKING_MODE`:

   **If beads available**:
   ```bash
   bd create "Epic: [Feature Name]" -p 1 --type epic
   bd create "FR-1: [Requirement]" -p 1 --parent <epic-id>
   # ... for each requirement
   ```

   **If using fallback** (`_prism/tasks.md`):
   ```markdown
   ## Epic: [Feature Name]
   Status: open
   Created: [date]
   
   ### Requirements
   - [ ] P1: FR-1 - [Requirement] (ID: FR-001)
   - [ ] P1: FR-2 - [Requirement] (ID: FR-002)
   ```

4. Update `_prism/status.yaml` with current phase

---

## Phase 5: Summary

**Goal**: Document completion and next steps

**Actions**:
1. Mark planning todos complete
2. Summarize:
   - PRD location: `_prism/planning/prd.md`
   - Beads issues created
   - Ready for `/prism-solution` command
3. Write session notes to `_prism/session-notes.md`

---

## Phase Gate

**Exit Criteria for Planning Phase**:
- [ ] PRD document complete
- [ ] User explicitly approved PRD
- [ ] Beads issues created for requirements
- [ ] Session notes written

**Next Command**: `/prism-solution` when ready for architecture
