# Beads Environment Check Template

Use this template at the start of any command that requires task tracking.

## Phase 0: Environment Check

**Goal**: Verify beads is available or set up fallback tracking

**Actions**:

### Step 1: Check Beads Installation
```bash
command -v bd >/dev/null 2>&1 && echo "BEADS_AVAILABLE" || echo "BEADS_MISSING"
```

### Step 2: Check Beads Initialization (if available)
```bash
[ -d ".beads" ] && echo "BEADS_INITIALIZED" || echo "BEADS_NOT_INITIALIZED"
```

### Step 3: Decision Tree

**If BEADS_AVAILABLE + BEADS_INITIALIZED**:
- ✅ Proceed with beads commands (`bd ready`, `bd create`, etc.)
- Set `$TRACKING_MODE = "beads"`

**If BEADS_AVAILABLE + BEADS_NOT_INITIALIZED**:
- Ask user:
  > "Beads is installed but not initialized in this project. Would you like me to run `bd init`?"
- If yes: Run `bd init` and proceed with beads
- If no: Use fallback tracking

**If BEADS_MISSING**:
- Inform user:
  > "Beads CLI not found. Using `_prism/tasks.md` for task tracking.
  > For persistent multi-session tracking, install beads: `npm install -g @beads/bd`"
- Set `$TRACKING_MODE = "fallback"`
- Create/update `_prism/tasks.md` instead of beads commands

---

## Fallback Commands Mapping

When `$TRACKING_MODE = "fallback"`, use these alternatives:

| Beads Command | Fallback Action |
|---------------|-----------------|
| `bd ready` | Read `_prism/tasks.md` and show tasks marked `[ ]` |
| `bd create "Title"` | Add `- [ ] Title` to `_prism/tasks.md` |
| `bd update <id> --status in_progress` | Change `[ ]` to `[/]` in tasks.md |
| `bd update <id> --status done` | Change `[/]` to `[x]` in tasks.md |
| `bd close <id>` | Mark task complete with `[x]` and add note |
| `bd show <id>` | Read task section from tasks.md |
| `bd sync` | Commit `_prism/tasks.md` to git |

---

## Fallback Task File Format

Create `_prism/tasks.md` with this structure:

```markdown
# Project Tasks

## Epic: [Feature Name]
Status: in_progress
Created: [date]

### Stories
- [ ] P0: Critical story (ID: S-001)
- [/] P1: In progress story (ID: S-002)
- [x] P2: Completed story (ID: S-003)

### Notes
[Session notes for compaction survival]

---

## Completed
- [x] Previous epic (completed [date])
```
