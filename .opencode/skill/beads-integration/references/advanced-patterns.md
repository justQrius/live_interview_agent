# Beads Advanced Patterns

Advanced patterns and workflows for complex multi-session work tracking.

## Multi-Session Epic Pattern

When work spans multiple sessions with complex dependencies:

```bash
# Session 1: Create the epic structure
bd create "Epic: OAuth Implementation" -p 0 --type epic
# Returns: myproject-abc

# Create child tasks with parent relationship
bd create "Research OAuth providers (Google, GitHub, Microsoft)" -p 1 --parent myproject-abc
# Returns: myproject-abc.1

bd create "Implement backend auth endpoints" -p 1 --parent myproject-abc
# Returns: myproject-abc.2

bd create "Add frontend login UI components" -p 2 --parent myproject-abc
# Returns: myproject-abc.3

# Add dependencies (backend must complete before frontend)
bd dep add myproject-abc.3 myproject-abc.2

# Start with research
bd update myproject-abc.1 --status in_progress
bd update myproject-abc.1 --notes "STARTED: Evaluating OAuth providers"
```

**Session 1 End:**
```bash
bd update myproject-abc.1 --notes "COMPLETED: Research done. Chose Auth0 for simplicity. IN PROGRESS: Setting up Auth0 account. NEXT: Create OAuth endpoints"
bd sync
```

**Session 2 (weeks later):**
```bash
bd ready
# Shows: myproject-abc.2 (next ready task)

bd show myproject-abc.2
# Full context from previous session notes preserved!

bd update myproject-abc.2 --status in_progress
```

---

## Blocked Work Pattern

When you discover a blocker during implementation:

```bash
# Mark current task as blocked
bd update myproject-xyz --status blocked --notes "API endpoint /auth returns 503, reported to backend team"

# Create blocker task
bd create "Fix /auth endpoint 503 error" -p 0 --type bug
# Returns: myproject-blocker

# Link dependency (blocker blocks original task)
bd dep add myproject-xyz myproject-blocker

# Find other ready work to stay productive
bd ready
# Shows tasks that aren't blocked - switch to those
```

**Result**: Blocked work is documented, and you can work on something else.

---

## Complex Dependency Chains

For features with multi-level dependencies:

```bash
# Create tasks
bd create "Deploy to production" -p 0
# Returns: deploy-prod

bd create "Run integration tests" -p 1
# Returns: integration-tests

bd create "Fix failing unit tests" -p 1
# Returns: fix-tests

# Create dependency chain: fixes → integration → deploy
bd dep add deploy-prod integration-tests      # Integration blocks deploy
bd dep add integration-tests fix-tests        # Fixes block integration

# Check what's ready
bd ready
# Shows: fix-tests (has no blockers)
# Hides: integration-tests (blocked by fix-tests)
# Hides: deploy-prod (blocked by integration-tests)

# Work on ready task
bd update fix-tests --status in_progress
# ... fix tests ...
bd close fix-tests --reason "All unit tests passing"

# Check ready again
bd ready
# Shows: integration-tests (now unblocked!)
# Still hides: deploy-prod (still blocked)
```

---

## Team Collaboration Pattern

When working with others using git sync:

**Alice's Session (Day 1):**
```bash
bd create "Refactor database layer" -p 1
bd update db-refactor --status in_progress
bd update db-refactor --notes "Started: Migrating to Prisma ORM"

# End of day - sync to git
bd sync
# Commits tasks to git, pushes to remote
```

**Bob's Session (Day 2):**
```bash
# Start of day - sync from git
bd sync
# Pulls latest tasks from remote

bd ready
# Shows: db-refactor [P1] [in_progress] (assigned to alice)

# Bob checks status
bd show db-refactor
# Sees Alice's notes: "Started: Migrating to Prisma ORM"

# Bob works on different task (no conflicts)
bd create "Add API rate limiting" -p 2
bd update rate-limit --status in_progress

# End of day
bd sync
# Both Alice's and Bob's tasks synchronized
```

---

## Compaction Survival Format

Write notes that enable future agents to continue with ZERO conversation history:

```
COMPLETED: [Specific deliverables - be explicit]
  - JWT authentication endpoint implemented
  - Token refresh logic with 15-minute expiry
  - Rate limiting at 100 req/minute per user

IN PROGRESS: [Current state + what's being worked on]
  - Implementing OAuth callback handler
  - Currently stuck on PKCE flow - researching

BLOCKERS: [What's preventing progress]
  - Waiting for Auth0 admin credentials from team lead
  - Need decision on session timeout value

KEY DECISIONS: [Important context or user guidance]
  - Chose Auth0 over Firebase Auth for better enterprise support
  - User approved 15-minute token expiry

NEXT STEPS: [What to do when resuming]
  1. Complete PKCE implementation
  2. Add integration tests for auth flow
  3. Update API documentation
```

**Key Principle**: Another agent should be able to continue your work with ONLY the beads notes - no conversation history needed.

---

## Priority Escalation Pattern

When priorities change during development:

```bash
# Urgent bug discovered
bd create "Critical: Production auth failing" -p 0 --type bug
# Returns: critical-auth

# Immediately mark other work as blocked by this
bd dep add current-feature critical-auth

# Escalate priority of existing low-priority task
bd update low-priority-task -p 0

# Check what's now urgent
bd list --priority 0
```

---

## Epic Completion Pattern

When all children of an epic are done:

```bash
# Check epic status
bd epic status myproject-abc
# Shows: 3/3 children closed

# Auto-close eligible epics
bd epic close-eligible
# Automatically closes epics where all children are done

# Or manually close with reason
bd close myproject-abc --reason "OAuth implementation complete. 3 PRs merged, tests passing."
```
