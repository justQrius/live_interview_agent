---
name: phase-gate
description: "Use this when transitioning phases, running /prism-solution, /prism-implement, /prism-verify, or user says 'move to next phase', 'ready for implementation'. Validates artifacts exist, checks gate requirements, and blocks transition if incomplete."
---

# Phase Gate Validator

Validates that all required artifacts and quality gates are satisfied before allowing phase transitions.

## When to Use

- Before running `/prism-solution` (Planning → Solutioning gate)
- Before running `/prism-implement` (Solutioning → Implementation gate)
- Before running `/prism-verify` (Implementation → Verification gate)
- When user says "move to next phase", "ready for implementation", "start verification"

## Gate Definitions

### Planning → Solutioning Gate

**Required Artifacts:**
- [ ] PRD exists at `_prism/planning/prd.md`
- [ ] NFRs section present (latency, reliability, security, observability, cost)
- [ ] Risk Matrix filled (at least one entry)
- [ ] Spike plans created for HIGH-risk items

**Validation Commands:**
```bash
# Check PRD exists
test -f _prism/planning/prd.md

# Check for NFRs section
grep -q "## Non-Functional Requirements\|## NFRs" _prism/planning/prd.md

# Check for Risk Matrix
grep -q "## Risk\|Risk Matrix\|Risk Register" _prism/planning/prd.md
```

**If Missing:** Block transition. Create beads issues for missing items.

---

### Solutioning → Implementation Gate

**Required Artifacts:**
- [ ] Architecture document exists at `_prism/architecture/`
- [ ] ADRs created for major decisions
- [ ] Spike results recorded with GO/NO-GO decisions
- [ ] Observability plan documented

**Validation Commands:**
```bash
# Check architecture exists
ls _prism/architecture/*.md 2>/dev/null

# Check for ADRs
ls _prism/architecture/adr-*.md 2>/dev/null || ls _prism/adrs/*.md 2>/dev/null
```

**If Missing:** Block transition. List specific missing items.

---

### Implementation → Verification Gate

**Required Artifacts:**
- [ ] CI pipeline green (or last test run passing)
- [ ] Tests added/updated for new code
- [ ] Code review completed (self or agent)
- [ ] Risk items from architecture addressed

**Validation:**
1. Check for test files corresponding to implementation
2. Verify reviewer sign-off in beads or commit history
3. Check `_prism/session-notes.md` for review confirmation

**If Missing:** Block transition. Require test run and review.

---

### Verification → Done Gate

**Required Artifacts:**
- [ ] Test coverage verified (target met)
- [ ] Parallel reviews completed (quality, security, performance)
- [ ] Documentation updated
- [ ] Runbook updated (if applicable)

**Validation:**
1. Check for coverage report or tester confirmation
2. Verify multiple review aspects covered
3. Check docs/ or README for updates

**If Missing:** Block transition. List outstanding verification items.

---

## Enforcement Behavior

### When Gate PASSES

```
✅ Gate Check: [Phase] → [Next Phase]

All requirements satisfied:
- PRD with NFRs: ✓
- Risk Matrix: ✓
- Spike plans: ✓ (none required OR completed)

Proceeding to [Next Phase].
```

### When Gate FAILS

```
❌ Gate Check: [Phase] → [Next Phase]

Missing requirements:
1. PRD exists but missing NFRs section
2. Risk Matrix has 2 HIGH items without spike plans
3. No ADRs found for architecture decisions

Action Required:
- Add NFRs section to _prism/planning/prd.md
- Create spike plans for: [list HIGH-risk items]
- Create ADR for: [major decision]

Would you like me to:
1. Create beads issues for these items?
2. Help complete the missing artifacts?
3. Override gate (requires explicit approval)?
```

---

## Override Protocol

Gates can only be overridden with **explicit user approval**:

```
User: "skip the gate check" / "override gate"
Agent: "⚠️ Gate override requested. Missing items:
        - [list items]
        
        These will be technical debt. Confirm override? (yes/no)"
User: "yes"
Agent: "Gate overridden. Added TODO items to _prism/session-notes.md"
```

---

## Integration with Beads

If beads is available:
- Create issues for missing gate requirements
- Tag with `gate-blocker` label
- Link to relevant phase

```bash
bd add "Complete NFRs section in PRD" -t gate-blocker -p high
bd add "Create spike for async+DB integration" -t gate-blocker -p critical
```

---

## Phase Status Tracking

Update `_prism/status.yaml` on successful gate passage:

```yaml
current_phase: implementation
previous_phase: solutioning
gate_passed: 2026-01-04T21:45:00
gate_requirements_met:
  - architecture_complete
  - adrs_created
  - spikes_validated
```
