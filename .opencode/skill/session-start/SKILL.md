---
name: session-start
description: Use this when the user mentions "start session", "resume work", or "where was I". Restores context from session notes and beads.
allowed-tools: "Read,Bash,TodoWrite"
version: "1.0.0"
---

# Session Start - Context Restoration Workflow

Guides context restoration when starting or resuming development sessions.

## Overview

This skill:
- Reads session notes for context
- Checks beads status for current work
- Identifies current phase
- Summarizes state for user

## Instructions

### Step 1: Check Session Notes

```bash
# Read session notes if they exist
cat _prism/session-notes.md 2>/dev/null || echo "No session notes found"
```

Session notes contain:
- COMPLETED: What was done
- IN PROGRESS: Current state
- BLOCKERS: What's blocking
- DECISIONS: Key context
- NEXT STEPS: What to do

### Step 2: Check Beads Status

```bash
# Get current work state
bd ready

# Check for in-progress work
bd list --status in_progress

# Check for blocked work
bd blocked
```

### Step 3: Identify Current Phase

Check `_prism/status.yaml` or infer from artifacts:

| Artifacts Present | Phase |
|-------------------|-------|
| No PRD | Planning |
| PRD, no architecture | Solutioning |
| Architecture, active stories | Implementation |
| Stories done, testing | Verification |

### Step 4: Check TodoWrite

Review any TodoWrite items from previous session.

### Step 5: Summarize for User

Present summary:

```markdown
## Session Restored

**Current Phase**: [Phase name]

**From Session Notes**:
- [Key context points]

**Beads Status**:
- In Progress: [count] tasks
- Ready: [count] tasks
- Blocked: [count] tasks

**Highest Priority Ready Work**:
1. [Task] - [Priority]
2. [Task] - [Priority]

**What would you like to work on?**
```

## Output

- Context restored from session notes
- Beads status summarized
- Current phase identified
- Ready work presented

## First Session (No History)

If no session notes or beads exist:

```markdown
## New Session

No previous context found. This appears to be a fresh start.

**Available Commands**:
- `/prism-plan` - Start planning a new feature
- `/prism-solution` - Begin architecture (if PRD exists)
- `/prism-implement` - Start implementation (if architecture exists)

**What would you like to work on?**
```

## Quality Checklist

- [ ] Session notes read (if exist)
- [ ] Beads status checked
- [ ] Current phase identified
- [ ] User presented with options
