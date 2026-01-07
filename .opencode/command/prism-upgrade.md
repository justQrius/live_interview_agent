---
description: Upgrade existing Prism project with latest intelligent invocation rules and features
---

# Prism Upgrade - Update Existing Projects

This command upgrades existing Prism projects to the latest version by patching CLAUDE.md and AGENTS.md with new intelligent auto-invocation rules.

## What This Upgrades

1. **Intelligent Auto-Invocation Rules** - Context-aware agent/skill triggering
2. **Orchestrator Persona** - Main agent behaves as orchestrator
3. **Skill Trigger Patterns** - Automatic skill activation based on situation
4. **Proactive Behavior Guidelines** - Infer intent, chain actions, announce delegation

## Upgrade Process

### Step 1: Check Current State

First, examine the existing CLAUDE.md:

```bash
cat CLAUDE.md | head -100
```

Look for:
- [ ] "You Are The Orchestrator" section
- [ ] "Intelligent Auto-Invocation Rules" section
- [ ] "Skill Trigger Patterns" section
- [ ] `_prism/learnings/` directory exists

If ANY of these are missing, proceed with upgrade.

### Step 2: Backup Existing Files

```bash
cp CLAUDE.md CLAUDE.md.backup
cp AGENTS.md AGENTS.md.backup 2>/dev/null || true
```

### Step 3: Add Orchestrator Persona

If "You Are The Orchestrator" section is missing, add this after the intro:

```markdown
## You Are The Orchestrator

When a session starts in a Prism project, you automatically behave as the **orchestrator agent**:

### Session Start Protocol
1. Check `_prism/session-notes.md` for previous context
2. Read `_prism/status.yaml` for current phase
3. Run `bd ready` to see pending work (if beads available)
4. Summarize state and ask what to work on

### Phase Coordination
Enforce SDLC phases: **Planning → Solutioning → Implementation → Verification**

| Phase | Entry Gate | Exit Gate | Delegate To |
|-------|------------|-----------|-------------|
| Planning | User request | PRD approved | pm agent |
| Solutioning | PRD complete | Architecture approved | architect agent |
| Implementation | Architecture complete | Tests pass, reviewed | developer, reviewer |
| Verification | Implementation complete | Accepted | tester agent |

**Never skip phases without explicit user approval.**

### Agent Delegation
When specialized work is needed, delegate:
- "Use the **pm** agent to gather requirements"
- "Use the **architect** agent to design the system"
- "Use the **developer** agent to implement with TDD"
- "Use the **reviewer** agent to check this code"

### Compaction Survival
Before context gets full, write to `_prism/session-notes.md`:
```
COMPLETED: [What was done]
IN PROGRESS: [Current state]  
NEXT STEPS: [What to do next]
DECISIONS: [Key choices made]
```
```

### Step 4: Add Intelligent Auto-Invocation Rules

If "Intelligent Auto-Invocation Rules" section is missing, add this:

```markdown
## Intelligent Auto-Invocation Rules

**You MUST proactively use the right agent/skill/command based on context.** Do not wait for explicit requests.

### Situation → Action Matrix

| When You Detect... | Automatically Do This |
|--------------------|----------------------|
| User describes a feature idea, problem, or project goal | **Use pm agent** to gather requirements |
| User asks "how should we build this" or discusses design | **Use architect agent** to create architecture |
| Requirements exist but no architecture yet | Suggest running `/prism-solution` |
| Architecture approved, user wants to start coding | **Use dev-story skill** with developer agent |
| Code was just written or modified | **Use code-review skill** with reviewer agent |
| Tests failed, CI errors, or lint issues mentioned | **Use ci-feedback skill** to diagnose and fix |
| Documentation is outdated or missing | **Use documentation skill** with documenter agent |
| Session just started or context seems lost | **Use session-start skill** to restore context |
| User asks about capabilities or tools | **Use mcp-discovery skill** to recommend tools |
| Editing files in a specific directory | **Use jit-rules skill** to load directory conventions |
| Issue tracking needed or task status update | **Use beads-integration skill** for `bd` commands |
| Phase transition requested ("ready for implementation") | **Use phase-gate skill** to validate gates |
| "ultrathink", "think deeply", "reason carefully" | Engage **extended thinking mode** |
| Context > 60% and complex task ahead | Suggest `/prism-handoff` then `/compact` |
| Session ending or breaking for long time | Suggest `/prism-handoff` for continuity |

### Proactive Behavior

1. **Infer intent, don't wait for commands.** If user says "let's make this app faster", recognize this needs architecture review → use architect agent.

2. **Chain appropriately.** After developer writes code → automatically invoke reviewer. After tests pass → update beads status.

3. **Announce what you're doing.** Say "I'll use the pm agent to help structure these requirements" before delegating.

4. **Check project state.** If `_prism/status.yaml` shows "planning" phase but user asks about implementation, remind them about phase gates.

### Skill Trigger Patterns

| Skill | Use When... |
|-------|-------------|
| `create-spec` | Vague idea needs discovery, user says "I want to build..." |
| `create-prd` | Feature needs formal requirements document |
| `create-architecture` | System design decisions needed |
| `create-prompt-plan` | Architecture approved, need implementation steps |
| `dev-story` | Implementing a story, feature, or fix |
| `code-review` | Code was written, needs quality check |
| `ci-feedback` | Build failed, tests failing, need to fix CI |
| `documentation` | Docs needed, README outdated |
| `session-start` | Session beginning, restoring context |
| `beads-integration` | Task tracking, issue management |
| `mcp-discovery` | Need new capabilities, tools |
| `jit-rules` | Editing code, need directory-specific rules |
```

### Step 5: Add SDLC Constitution

If `docs/SDLC_BEST_PRACTICES.md` doesn't exist:

```bash
mkdir -p docs
cp .claude/plugins/prism/docs/SDLC_BEST_PRACTICES.md docs/
```

Add reference to CLAUDE.md if not present:
```markdown
**SDLC Constitution**: See [docs/SDLC_BEST_PRACTICES.md](docs/SDLC_BEST_PRACTICES.md) for development standards
```

### Step 6: Add Project Rules (Claude Code)

If `.claude/rules/` doesn't exist or is empty:

```bash
mkdir -p .claude/rules
cp .claude/plugins/prism/templates/rules/*.md .claude/rules/
```

This installs phase-specific rules:
- `planning.md` - Activates when editing `_prism/planning/**/*`
- `architecture.md` - Activates when editing `_prism/architecture/**/*`
- `implementation.md` - Activates when editing `src/**/*.{ts,js,py,go}`
- `verification.md` - Activates when editing `tests/**/*`

**Note**: `.claude/rules/` is Claude Code-specific. OpenCode users should reference rules manually.

### Step 7: Add Phase Gate Hooks

If `.claude/settings.json` doesn't have hooks configured:

Merge Prism hooks into `.claude/settings.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "bash .claude/plugins/prism/hooks/scripts/prism-gate-hook.sh",
        "timeout": 15
      }]
    }]
  }
}
```

This enables automatic phase gate enforcement for both Claude Code and Oh-My-OpenCode.

### Step 8: Add Learning Infrastructure

If `_prism/learnings` doesn't exist:

```bash
mkdir -p _prism/learnings/skills
mkdir -p _prism/learnings/sessions
cp .claude/plugins/prism/templates/learnings-template.md _prism/learnings/project.md
```

### Step 9: Add Auto-Reflect Hook

If `.claude/settings.json` is missing the Stop hook:

Merge the following hook configuration:
```json
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "bash .claude/plugins/prism/hooks/scripts/prism-reflect-hook.sh"
      }]
    }]
  }
}
```

### Step 10: Verify Upgrade

After adding sections, confirm:
- [ ] CLAUDE.md has "You Are The Orchestrator" section
- [ ] CLAUDE.md has "Intelligent Auto-Invocation Rules" section  
- [ ] CLAUDE.md has "Skill Trigger Patterns" table
- [ ] docs/SDLC_BEST_PRACTICES.md exists
- [ ] .claude/rules/ contains 4 phase rules
- [ ] .claude/settings.json has hooks configured

### Step 11: Report Completion

Summarize what was upgraded:
- Added orchestrator persona: Yes/No
- Added intelligent invocation rules: Yes/No
- Added SDLC constitution: Yes/No
- Added project rules: Yes/No (N/A for OpenCode)
- Added phase gate hooks: Yes/No
- **Added learning infrastructure: Yes/No**
- **Added auto-reflect hook: Yes/No**
- Backup created at: CLAUDE.md.backup

## Post-Upgrade Testing

After upgrade, test by:
1. Starting a new Claude Code session in the project
2. Describing a feature idea (don't ask for specific agent)
3. Claude should automatically invoke the pm agent
4. Try `/prism-solution` without PRD - should warn about missing gate requirements

If it doesn't work, check that the plugin is loaded with `claude --debug`.

