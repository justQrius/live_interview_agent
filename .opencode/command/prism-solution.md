---
description: Start the Solutioning phase - explore codebase and design architecture
argument-hint: Optional focus area for architecture
agent: orchestrator
---

# Prism Solutioning Phase

You are starting the Solutioning phase of the SDLC. This phase explores the codebase and produces an architecture design.

## Prerequisites

- PRD must exist at `_prism/planning/prd.md`
- PRD must be approved (check beads status)

Check prereqs first:
```bash
bd list --status open --type epic
```

## Core Principles

- **Understand before designing**: Explore existing patterns first
- **Use parallel exploration**: Launch multiple explorer agents
- **Make decisive choices**: One architecture, not multiple options
- **Get approval**: User must approve before implementation

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

**Goal**: Load context and verify prerequisites

**Actions**:
1. Read PRD from `_prism/planning/prd.md`
2. Check session notes: `_prism/session-notes.md`
3. Verify Planning phase complete via beads
4. Create TodoWrite list for solutioning phases

---

## Phase 2: Codebase Exploration

**Goal**: Understand existing patterns and integration points

**Actions**:
1. **Spawn 2-3 isolated explorer subagents in parallel using Task tool**:

   ```
   # Task 1: Similar Features (spawn immediately)
   Use Task tool:
   - Agent: explorer
   - Prompt: "Find features similar to [PRD feature] in the codebase
     Trace entry points, execution flow, patterns, and conventions
     Return: entry points with file:line references, execution flow summary, 
     key patterns, 5-10 essential files"
   
   # Task 2: Architecture Mapping (spawn immediately, don't wait for Task 1)
   Use Task tool:
   - Agent: explorer
   - Prompt: "Map the architecture and abstractions for [relevant area from PRD]
     Analyze abstraction layers, design patterns, interfaces, cross-cutting concerns
     Return: architecture layer diagram, key components, integration points, 
     5-10 essential files"
   
   # Task 3: Data Model (spawn immediately if applicable)
   Use Task tool:
   - Agent: explorer
   - Prompt: "Analyze data model and storage patterns for [relevant area]
     Investigate data structures, schemas, storage mechanisms, data flow, validation
     Return: data model summary, storage patterns, validation approaches, 
     5-10 essential files"
   ```
   
   **Why parallel Task tools**: Each explorer runs in isolated context. Prevents 
   exploration output from polluting main session. All 3 run simultaneously.

2. **Collect all explorer subagent results** when Tasks complete

3. **Read all key files** identified by the subagents (typically 15-30 files total)

4. Synthesize findings into a comprehensive patterns summary

---

## Phase 3: Clarifying Questions

**Goal**: Resolve technical ambiguities before designing

**CRITICAL**: This is essential. DO NOT SKIP.

**Actions**:
1. Review codebase findings + PRD
2. Identify underspecified technical aspects:
   - Integration approaches
   - Technology choices
   - Performance requirements
   - Backward compatibility needs
   - Edge cases in data model
3. **Present all questions to user**
4. **WAIT for answers before designing**

---

## Phase 4: Architecture Design

**Goal**: Create comprehensive architecture blueprint

**Actions**:
1. **Use the architect subagent** to design the architecture for [feature name]
   
   Provide the architect subagent with:
   - PRD Summary: [key requirements from _prism/planning/prd.md]
   - Codebase Patterns Discovered: [patterns from exploration phase]
   - User's Technical Decisions: [answers to clarifying questions]
   
   Tell the architect subagent to:
   - Write architecture blueprint to _prism/architecture/architecture.md
   - Include architecture diagram (mermaid), component designs, data model, integration points, build sequence, trade-offs
   - Make decisive choices - pick one approach and commit
   - Be specific with file paths, function names, concrete implementation steps
   - Return summary with key components, build sequence, and critical decisions

2. **Wait for architect subagent to complete**

3. Verify architecture document was written to `_prism/architecture/architecture.md`

4. Present architecture summary to user for review

---

## Phase 5: Approval & Story Creation

**Goal**: Get approval and create implementation stories

**CRITICAL**: Do NOT proceed without explicit approval

**Actions**:
1. **Ask user to approve architecture**
2. After approval, create stories in beads:
   ```bash
   # Create stories from build sequence
   bd create "Story: [Component 1]" -p 1 --parent <epic-id>
   bd create "Story: [Component 2]" -p 1 --parent <epic-id>
   
   # Add dependencies based on build sequence
   bd dep add <story-2> <story-1>
   ```
3. Update `_prism/status.yaml` to Implementation phase

---

## Phase 6: Update CLAUDE.md and AGENTS.md

**Goal**: Reflect architecture decisions in project documentation

**Actions**:
1. Read current CLAUDE.md (if exists)
2. Update or add sections:
   - **Tech Stack**: From architecture decisions
   - **Conventions**: Coding patterns chosen
   - **Key Components**: From architecture diagram
3. Add architecture reference:
   ```markdown
   ## Architecture
   See `_prism/architecture/architecture.md` for full details.
   ```
4. Preserve existing user content

5. **Update AGENTS.md** with discovered commands and conventions:
   ```markdown
   ## Setup Commands
   
   - Install dependencies: `[discovered install command]`
   - Run tests: `[discovered test command]`
   - Build: `[discovered build command]`
   - Dev server: `[discovered dev command]`
   
   ## Code Style
   
   - [Key conventions from architecture]
   - Follow conventions in CLAUDE.md
   ```

---

## Phase 6.5: Capture Learnings

Run `/prism-reflect` to capture architecture and design insights:
- Tech stack choices and rationale?
- Unexpected constraints discovered?
- Design patterns selected for this project?
- "Tenet" workflow insights?

---

## Phase 7: Summary

**Goal**: Document completion and next steps

**Actions**:
1. Mark solutioning todos complete
2. Summarize:
   - Architecture location: `_prism/architecture/architecture.md`
   - CLAUDE.md updated with tech decisions
   - AGENTS.md updated with commands
   - Stories created in beads
   - Ready for `/prism-implement` command
3. Write session notes

---

## Phase Gate

**Exit Criteria for Solutioning Phase**:
- [ ] Architecture document complete
- [ ] User explicitly approved architecture
- [ ] CLAUDE.md updated with tech stack and conventions
- [ ] **AGENTS.md updated with commands**
- [ ] Stories created with dependencies
- [ ] Session notes written

**Next Command**: `/prism-implement [story-id]` to start implementation

