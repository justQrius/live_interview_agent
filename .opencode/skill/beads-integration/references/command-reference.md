# Beads Command Reference

Complete reference of all beads CLI commands.

## Essential Commands (Top 10)

| Command | Purpose | Example |
|---------|---------|---------|
| `bd ready` | Show unblocked tasks | "What should I work on?" |
| `bd create "Title" -p 1` | Create new task | "Track new work" |
| `bd show <id>` | View task details | "Get full context" |
| `bd update <id> --status in_progress` | Start working | "Mark as active" |
| `bd update <id> --notes "..."` | Add progress notes | "Document progress" |
| `bd close <id> --reason "..."` | Complete task | "Mark done" |
| `bd dep add <child> <parent>` | Add dependency | "This blocks that" |
| `bd list` | See all tasks | "Show everything" |
| `bd search <query>` | Find tasks | "Find by keyword" |
| `bd sync` | Sync with git | "Backup to git" |

---

## Find Commands

### bd ready
Show tasks with no open blockers, sorted by priority.

```bash
bd ready
# Output:
# myproject-abc [P1] [task] open
#   Implement user authentication
# myproject-xyz [P0] [epic] in_progress
#   Refactor database layer
```

### bd list
View all tasks with optional filters.

```bash
bd list                      # All tasks
bd list --status open        # Only open tasks
bd list --status in_progress # Only in-progress
bd list --priority 0         # Only P0 (critical)
bd list --type bug           # Only bugs
bd list --label backend      # Only tagged "backend"
bd list --assignee alice     # Only assigned to alice
```

### bd show <id>
Full task details including description, dependencies, and audit trail.

```bash
bd show myproject-abc
# Shows:
# - Title and description
# - Status, priority, type
# - Dependencies (what blocks this, what this blocks)
# - Full audit trail (all changes)
# - Notes history
```

### bd search <query>
Text search across task titles and descriptions.

```bash
bd search "authentication"
bd search login --status open  # Combine with filters
```

### bd blocked
Show all tasks that have open blockers.

```bash
bd blocked
# Shows tasks waiting on something else
```

### bd stats
Project-level statistics.

```bash
bd stats
# Output:
# Total: 47 issues
# By status: 5 open, 2 in_progress, 1 blocked, 39 closed
# By priority: 2 P0, 5 P1, 10 P2, 15 P3, 15 P4
# By type: 10 bug, 20 feature, 12 task, 5 epic
```

---

## Create Commands

### bd create
Create a new task.

**Arguments:**
- Title (required): Brief description
- `-p, --priority`: 0-4 (0=critical, 4=backlog, default: 2)
- `--type`: bug, feature, task, epic, chore (default: task)
- `--parent`: Parent task ID for child tasks
- `--description`: Longer description

```bash
# Basic task
bd create "Fix login bug" -p 0 --type bug

# Feature with description
bd create "Add OAuth support" -p 1 --type feature --description "Support Google and GitHub OAuth"

# Child task under epic
bd create "Design OAuth flow" -p 1 --parent epic-oauth
```

---

## Update Commands

### bd update <id>
Update task properties.

```bash
# Change status
bd update myproject-abc --status in_progress
bd update myproject-abc --status blocked
bd update myproject-abc --status done

# Add notes (APPENDS to existing)
bd update myproject-abc --notes "COMPLETED: Auth endpoint. NEXT: Tests"

# Change priority
bd update myproject-abc -p 0  # Escalate to critical
```

### bd label
Manage task labels.

```bash
bd label add myproject-abc backend
bd label add myproject-abc security
bd label remove myproject-abc security
```

### bd reopen <id>
Reopen a closed task.

```bash
bd reopen myproject-abc
# Reopens with status 'open'
```

---

## Dependency Commands

### bd dep add <child> <parent>
Add dependency (parent must complete before child becomes ready).

```bash
bd dep add deploy-task test-task
# Meaning: test-task blocks deploy-task
```

### bd dep list <id>
View dependencies for a task.

```bash
bd dep list myproject-abc
# Shows:
# - What blocks this task (blockers)
# - What this task blocks (dependents)
```

### bd dep remove <child> <parent>
Remove a dependency.

```bash
bd dep remove deploy-task test-task
```

---

## Complete Commands

### bd close <id>
Mark task complete.

```bash
bd close myproject-abc --reason "Implemented and tested. PR #42 merged."
```

### bd epic close-eligible
Auto-close epics where all children are closed.

```bash
bd epic close-eligible
```

---

## Sync Commands

### bd sync
All-in-one git synchronization.

```bash
bd sync
# 1. Export database to .beads/issues.jsonl
# 2. Commit changes to git
# 3. Pull from remote (merge if needed)
# 4. Import updated JSONL
# 5. Push to remote
```

### bd export
Export database to JSONL.

```bash
bd export -o backup.jsonl
bd export -o _prism/issues-backup.jsonl  # Before compaction
```

### bd import
Import from JSONL file.

```bash
bd import -i backup.jsonl
```

---

## Epic Commands

### bd epic status <id>
Show epic completion status.

```bash
bd epic status myproject-epic
# Output:
# Epic: myproject-epic
# Progress: 3/5 children completed (60%)
# Open: 2 tasks remaining
```

### bd epic close-eligible
Auto-close completed epics.

```bash
bd epic close-eligible
# Closes all epics where 100% of children are closed
```

---

## Cleanup Commands

### bd delete <id>
Delete a task (requires --force).

```bash
bd delete myproject-test --force
# Permanently removes task
```

### bd admin compact
Archive old closed tasks.

```bash
bd admin compact
# Moves old closed issues to archive
```

---

## Status Values

| Status | Meaning |
|--------|---------|
| `open` | Not started, waiting to be worked on |
| `in_progress` | Actively being worked on |
| `blocked` | Stuck, waiting on something |
| `closed` | Completed |

---

## Priority Values

| Priority | Meaning | Use For |
|----------|---------|---------|
| P0 | Critical | Production issues, blockers |
| P1 | High | Current sprint work |
| P2 | Medium | Planned work (default) |
| P3 | Low | Nice to have |
| P4 | Backlog | Future consideration |

---

## Type Values

| Type | Meaning |
|------|---------|
| `task` | General work item (default) |
| `bug` | Defect to fix |
| `feature` | New functionality |
| `epic` | Large feature with children |
| `chore` | Maintenance, cleanup |
