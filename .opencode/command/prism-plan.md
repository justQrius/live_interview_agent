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

## Phase 1: Spec Discovery (Effective Requirements)

**Goal**: Create a comprehensive specification through structured discovery - "waterfall in 15 minutes"

**Related Skill**: `create-spec`

Initial request: $ARGUMENTS

### Step 1: Structured Q&A

Ask these questions ONE AT A TIME, waiting for each answer:

1. **Problem Statement**
   > "What problem are we solving? Why does it matter?"

2. **Target Users**  
   > "Who will use this? What are their main characteristics?"

3. **Success Definition**
   > "What defines success? How will we know this works?"

4. **Constraints**
   > "What are the constraints? (Time, budget, tech stack, integrations)"

5. **Priority**
   > "What's the timeline? What's must-have vs nice-to-have?"

**⚠️ WAIT FOR ANSWERS** - Do not proceed without user input on each question.

### Step 2: Edge Case Discovery

After gathering basics, probe for edge cases:

> "Let's think about edge cases. What happens when:
> - A user does something unexpected?
> - The system is under load?
> - Data is missing or malformed?"

Document all edge cases identified.

### Step 3: Spec Creation

Create `_prism/discovery/spec.md` with:
- Problem statement
- User personas
- Discovery Q&A summary
- Edge cases table
- Initial requirements list (FR-1, FR-2, NFR-1, etc.)
- Testing strategy outline

See `templates/spec-template.md` for full template.

### Step 4: Spec Approval

**Action**: Ask user to review `_prism/discovery/spec.md`.

When approved:
1. Update status to "approved" in frontmatter
2. Report checklist of comprehensive requirements

## Phase 5: Capture Learnings

Run `/prism-reflect` to capture any insights from the requirements gathering process:
- Common requirement patterns?
- Questions that clarified ambiguity?
- Edge cases relevant to other projects?

Present spec summary to user:
> "Here's the specification I've created. Does this capture your vision?"

**Wait for approval before Phase 2.**

---

## Phase 2: Requirements Synthesis

**Goal**: Derive structured requirements from approved spec

**Actions**:
1. Read spec from `_prism/discovery/spec.md`
2. Expand requirements into detailed list with acceptance criteria
3. Present summary to user for validation
4. **Ask if anything is missing** before PRD creation

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
