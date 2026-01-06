---
name: beads-integration
description: Use this when the user mentions "create task", "track issue", "status update", or "bd ready". Manages persistent task memory and tracking.
allowed-tools: "Read,Bash(bd:*)"
version: "1.0.0"
---

# Beads Integration - Persistent Task Memory

Guides usage of beads for multi-session work tracking that survives context compaction.

## Overview

This skill:
- Creates and manages beads issues
- Tracks dependencies between tasks
- Ensures compaction survival
- Syncs with git for persistence

## When to Use Beads vs TodoWrite

| Beads (bd) | TodoWrite |
|------------|-----------|
| Multi-session work | Single-session tasks |
| Has dependencies | Linear execution |
| Survives compaction | Conversation-scoped |
| Git-backed | Memory only |

**Decision Rule**: If resuming in 2 weeks would be hard without it, use beads.

## Core Commands

### Find Work

```bash
bd ready              # Show unblocked tasks (priority sorted)
bd list --status open # All open tasks
bd blocked            # Tasks with open blockers
bd show <id>          # Full task details
```

### Create Tasks

```bash
# Basic task
bd create "Task title" -p 1 --type task

# Bug with high priority
bd create "Fix auth bug" -p 0 --type bug

# Epic with children
bd create "Epic: OAuth" -p 1 --type epic
bd create "Research providers" -p 1 --parent <epic-id>
bd create "Implement endpoints" -p 1 --parent <epic-id>
```

### Update Progress

```bash
# Change status
bd update <id> --status in_progress
bd update <id> --status blocked
bd update <id> --status done

# Add notes (critical for compaction survival!)
bd update <id> --notes "COMPLETED: X. IN PROGRESS: Y. NEXT: Z"
```

### Manage Dependencies

```bash
# Add blocker (parent blocks child)
bd dep add <blocked-task> <blocking-task>

# View dependencies
bd dep list <id>
```

### Complete Work

```bash
bd close <id> --reason "Completed: [summary]"
bd ready  # Check newly unblocked work
```

### Sync with Git

```bash
bd sync  # Export, commit, push, pull, import
bd export -o backup.jsonl  # Export only
```

## Compaction Survival Notes

Write notes that enable future agents to continue with zero history:

```
COMPLETED: Specific deliverables (JWT auth endpoint implemented)
IN PROGRESS: Current state + next step (testing token refresh)
BLOCKERS: What's preventing progress (waiting on API fix)
KEY DECISIONS: Important context (chose Passport.js for OAuth)
NEXT STEPS: What to do next (add rate limiting)
```

## Session Workflow

### At Session Start
```bash
bd ready                    # Find work
bd show <highest-priority>  # Get context
bd update <id> --status in_progress
```

### During Work
```bash
bd update <id> --notes "Progress: ..."
```

### At Session End
```bash
bd update <id> --notes "COMPLETED: X. IN PROGRESS: Y. NEXT: Z"
bd sync
```

### Before Context Compaction
```bash
bd export -o _prism/issues-backup.md
```

## Installation

Beads is **optional but recommended** for multi-session work tracking.

### Install Options

```bash
# Option 1: npm (recommended for Node.js users)
npm install -g @beads/bd

# Option 2: curl script (macOS/Linux)
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Option 3: Homebrew (macOS)
brew install steveyegge/beads/bd

# Option 4: Go (if Go installed)
go install github.com/steveyegge/beads/cmd/bd@latest
```

### Initialize (run once per project)
```bash
bd init
# Or for private use on shared projects:
bd init --stealth
```

### Verify Installation
```bash
bd --version
bd ready
```

---

## Fallback: When Beads is Not Installed

If beads is not installed, Prism commands will still work with these alternatives:

### Use TodoWrite Instead
```
For in-session task tracking, use TodoWrite:
- [ ] Task 1
- [ ] Task 2
```

### Manual Tracking File
Create `_prism/tasks.md` for simple tracking:
```markdown
## Active Tasks
- [ ] P0: Critical task
- [/] P1: In progress task
- [x] P2: Completed task

## Notes
[Session notes here]
```

### Session Notes for Continuity
Write to `_prism/session-notes.md`:
```
COMPLETED: [what was done]
IN PROGRESS: [current state]
NEXT STEPS: [what to do next]
```

---

## Additional Resources

### Reference Files

For detailed patterns and advanced techniques, consult:

- **`references/command-reference.md`** - Complete command reference with all options
- **`references/advanced-patterns.md`** - Multi-session, dependency, and team collaboration patterns

### When to Read References

- Starting complex multi-session work → Read advanced-patterns.md
- Need specific command syntax → Read command-reference.md
- Troubleshooting beads issues → Check error handling section below

---

## Error Handling

### `bd: command not found`
Beads CLI not installed. Install with one of the options above, or use the fallback approach.

### `No .beads database found`
Run `bd init` to initialize (humans/users do this once).

### `Task not found`
Use `bd list` to verify task IDs.

### `Circular dependency detected`
Attempting to create A→B→A cycle. Restructure with `bd dep list <id>` to view current dependencies.

### Git merge conflicts in `.beads/issues.jsonl`
Run `bd sync --merge` for auto-resolution, or manually resolve then `bd import`.

---

## Output

- Task IDs for reference
- Status summaries
- Dependency graphs
- Audit trails

## Quality Checklist

- [ ] Notes written before session end (use compaction survival format)
- [ ] Beads exported before compaction: `bd export -o _prism/issues-backup.jsonl`
- [ ] Dependencies tracked for blocked work
- [ ] Status updated as work progresses
- [ ] Synced to git before switching branches: `bd sync`

