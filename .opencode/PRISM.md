# Prism - SDLC Development Framework

A structured, methodology-driven development system for Claude Code that ensures consistent quality through phased development, test-first practices, and persistent task tracking.

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

### Subagent Delegation

When specialized work is needed, delegate to **subagents** (isolated context):
- "Use the **pm** agent to gather requirements"
- "Use the **architect** agent to design the system"
- "Use the **developer** agent to implement with TDD"
- "Use the **reviewer** agent to check this code"

**Subagent Pattern**: Subagents run in isolated context to prevent polluting the main session. Use when:
- Processing multiple items in parallel
- Handling conditional logic with branching
- Running exploratory tasks that generate lots of output

**Component Hierarchy** (build in reverse order):
```
Skills (foundation) → Subagents (isolated execution) → Commands (user trigger)
```

### Compaction Survival
Before context gets full, write to `_prism/session-notes.md`:
```
COMPLETED: [What was done]
IN PROGRESS: [Current state]  
NEXT STEPS: [What to do next]
DECISIONS: [Key choices made]
```

---

## Context Budget Management

**Context is precious.** Performance degrades as tokens increase, even before hitting limits.

### Context Thresholds

| Usage | Status | Action |
|-------|--------|--------|
| 0-40% | ✅ Healthy | Work freely |
| 40-60% | ⚠️ Growing | Reference `_prism/todo.md` to anchor attention |
| 60-75% | 🔶 Heavy | Run `/prism-handoff`, consider `/compact` |
| 75%+ | 🔴 Critical | `/compact` immediately or start new session |

### Best Practices

1. **Check context regularly**: Run `/context` before complex tasks
2. **Use Task tool for exploration**: Subagents don't bloat main context
3. **Anchor attention with todos**: Reference `_prism/todo.md` at 50%+
4. **Handoff before compacting**: Run `/prism-handoff` to preserve decisions
5. **Use /rewind for mistakes**: Checkpoints save context (`Esc + Esc`)

### When to Use Extended Thinking (ultrathink)

| Situation | Trigger |
|-----------|---------|
| Complex algorithm design | "ultrathink this solution" |
| Debugging elusive bugs | "think deeply about this bug" |
| Architecture decisions | "reason carefully about tradeoffs" |
| Self-review before committing | "ultrathink review this code" |
| Multi-step refactoring | "think through this refactor" |

---

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
| "risk", "unknown integration", "spike" mentioned | **Use explorer agent** + suggest spike plan |
| "SLO", "latency", "observability", "opentelemetry" | **Use architect agent** + add observability section |
| "security", "auth", "tokens", "PII", "secrets" | **Use reviewer agent (security lens)** earlier |
| "cross-platform", "windows", "linux", "mac" | **Use explorer agent** + platform testing checklist |
| "async", "threading", "concurrency" | **Use architect agent** + document concurrency model |

### Proactive Behavior

1. **Infer intent, don't wait for commands.** If user says "let's make this app faster", recognize this needs architecture review → use architect agent.

2. **Chain appropriately.** After developer writes code → automatically invoke reviewer. After tests pass → update beads status.

3. **Announce what you're doing.** Say "I'll use the pm agent to help structure these requirements" before delegating.

4. **Check project state.** If `_prism/status.yaml` shows "planning" phase but user asks about implementation, remind them about phase gates.

5. **Enforce gates.** Before phase transitions, run phase-gate skill. Block if requirements not met.

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
| `phase-gate` | Phase transition, validate gate requirements |

## Installation

```
/plugin marketplace add ./prism-marketplace
/plugin install prism@prism-marketplace
```

---

## Quick Reference

### Commands
| Command | Phase | Purpose |
|---------|-------|---------|
| `/prism-init` | Setup | Bootstrap CLAUDE.md + AGENTS.md + project structure |
| `/prism-plan` | Planning | Requirements → PRD |
| `/prism-solution` | Solutioning | Exploration → Architecture |
| `/prism-implement <id>` | Implementation | Story → TDD → Review |
| `/prism-verify` | Verification | Test → Review → Document |

### Agents
| Agent | Model | When to Use |
|-------|-------|-------------|
| `orchestrator` | Sonnet | Phase and session management |
| `pm` | Sonnet | Requirements, PRD creation |
| `architect` | Sonnet | System design, component blueprints |
| `developer` | Sonnet | TDD implementation |
| `reviewer` | Sonnet | Code review (confidence scoring) |
| `tester` | **Haiku** | Fast test execution |
| `explorer` | **Haiku** | Codebase exploration (read-only) |
| `documenter` | Sonnet | Documentation generation |

---

## Workflow

### SDLC Phases

```
/prism-init → /prism-plan → /prism-solution → /prism-implement → /prism-verify
     ↓            ↓              ↓                 ↓                 ↓
 CLAUDE.md       PRD        Architecture      Stories          Tests
+ AGENTS.md  (approved)     + CLAUDE.md      (TDD loop)    + CLAUDE.md
  created                    updated                         updated
```

**Phase Gate Rule**: Each phase must be explicitly approved before proceeding to the next.

### Test-First Development (TDD)

All implementation MUST follow this loop:
1. **Write failing test** - Capture acceptance criterion
2. **Implement** - Write minimum code to pass
3. **Verify** - Run tests, confirm passing
4. **Refactor** - Improve code quality
5. **Update beads** - Track progress

---

## Agent Invocation

**CRITICAL**: Agents must be explicitly invoked using the **Task tool** with specific prompts.

### How to Invoke Agents

Use the Task tool to launch a subagent. The prompt you provide becomes the agent's instructions:

```
Task tool → Select agent (e.g., "explorer") → Provide specific prompt
```

### Invocation Pattern

**DO THIS**:
```
Launch the explorer agent with this prompt:
"Analyze the authentication system. Find entry points, trace execution flow,
and return a list of 5-10 essential files to understand."
```

**NOT THIS**:
```
Use the explorer agent to analyze authentication.
```

### Parallel Agents

Launch multiple agents simultaneously for faster results:
- **Exploration**: Launch 2-3 explorer agents with different focuses
- **Review**: Launch 3 reviewer agents (quality, bugs, conventions)
- Wait for all to complete, then consolidate findings

### Agent Return Values

Always specify what the agent should return:
- Summary of findings
- List of files to read
- Specific recommendations
- Confidence scores (for reviewers)

---

## Skills

Skills are procedural knowledge that auto-trigger based on user phrases. They extend agent capabilities with detailed workflows.

### Available Skills
 
 | Skill | Auto-Triggers On | Used By |
 |-------|------------------|---------|
 | `create-spec` | "discover", "brainstorm", "start project" | PM |
 | `create-prd` | "create PRD", "define requirements" | PM |
 | `create-architecture` | "design architecture", "system design" | Architect |
 | `create-prompt-plan` | "create implementation plan", "prompt plan" | Architect |
 | `dev-story` | "implement story", "TDD", "fix bug" | Developer |
 | `ci-feedback` | "fix CI", "test failed", "lint error" | Developer |
 | `code-review` | "review code", "check PR" | Reviewer |
 | `documentation` | "write docs", "create README" | Documenter |
 | `beads-integration` | "create task", "track issue", "bd ready" | All |
 | `session-start` | "where was I", "resume work" | All |
 | `mcp-discovery` | "setup MCP", "install tools" | All |
 | `jit-rules` | "directory rules", "conventions" | All |

### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (always in context) - ~100 words
2. **SKILL.md body** (when skill triggers) - ~1,500 words
3. **references/** (loaded as needed) - Unlimited

For complex tasks, the skill will reference additional files in `references/` that provide detailed patterns, examples, and advanced techniques.

---

## MCP Servers (Optional Enhancement)

MCP servers extend agent capabilities. Install based on your project needs.

### Recommended by Phase

| Phase | MCP | Install Command | Purpose |
|-------|-----|-----------------|---------|
| Init/Solution | `deepwiki` | `/mcp add deepwiki` | Analyze similar GitHub repos |
| Plan | `github` | `/mcp add github` | Issue/PR integration |
| Solution/Implement | `context7` | `/mcp add context7` | Library documentation |
| Implement | `playwright` | `/mcp add playwright` | Browser testing |
| Verify | `sentry` | `/mcp add sentry` | Error monitoring |

### Quick Setup

```bash
# Essential trio for most projects
/mcp add context7
/mcp add deepwiki
/mcp add sequential-thinking

# Check what's installed
/mcp
```

### Agent MCP Capabilities

| Agent | Enhanced By | Capability |
|-------|-------------|------------|
| `explorer` | deepwiki | Analyze similar GitHub projects |
| `architect` | context7, sequential-thinking | Library docs, complex reasoning |
| `developer` | context7 | API documentation lookup |
| `tester` | playwright | Browser automation tests |

> **Note**: Agents work without MCPs but gain enhanced research capabilities when available.

---

## Directory-Specific Rules (Elite Pattern)

An **elite context engineering pattern** that loads rules based on proximity to the file being edited.

### How It Works

When editing a file, check for rules in the directory hierarchy:
```
src/api/handlers/user.ts  ← File being edited

Rules loaded (in priority order):
1. src/api/handlers/.claude/rules/*.md  (closest - highest priority)
2. src/api/.claude/rules/*.md           (parent)
3. src/.claude/rules/*.md               (grandparent)
4. .claude/rules/*.md                   (project root)
```

### Benefits

- **Context Efficiency**: Only relevant rules in context window
- **Modularity**: Teams can own their component's conventions
- **Discoverability**: Rules live near the code they govern

### Creating Directory Rules

Place `.md` files in `.claude/rules/` directories:

```yaml
---
globs: ["*.ts", "*.tsx"]
description: API endpoint conventions
---

# API Rules
- All handlers must validate input
- Errors must include request ID
- Use consistent response format
```

See `skills/jit-rules/SKILL.md` for complete guidance on creating and using directory rules.

---

## Extensibility (Future Scope)

Prism is designed to coexist with and leverage other plugins, agents, and tools.

### Current Behavior

| Component | During Prism Commands | Outside Prism Commands |
|-----------|----------------------|------------------------|
| **Agents** | Prism agents explicitly invoked | Any matching agent may be used |
| **Skills** | Prism skills used | Any matching skill may trigger |
| **MCPs** | Shared - all MCPs available | Shared - all MCPs available |
| **Hooks** | All plugins' hooks fire | All plugins' hooks fire |

### Future: External Integration

Prism will be enhanced to:

1. **Discover external agents** - Use specialized agents from other plugins (e.g., `security-reviewer` from a security plugin)
2. **Compose skills** - Chain Prism skills with external skills (e.g., security-scan → code-review)
3. **Leverage any MCP** - Use any documentation/search/database MCP, not just those listed
4. **Prompt for preferences** - "I found X plugin. Should I use it for Y?"

See `docs/extensibility.md` for the full roadmap.

---

## Beads Integration (Critical)

Beads provides persistent task memory that survives context compaction.

### Essential Commands

```bash
# Session start
bd ready                  # Show unblocked tasks (priority sorted)
bd show <id>              # Get full task context

# During work
bd update <id> --status in_progress
bd update <id> --notes "COMPLETED: X. IN PROGRESS: Y"

# Completion
bd close <id> --reason "Implemented: [summary]"
bd sync                   # Push to git
```

### Compaction Survival Notes Format

**CRITICAL**: Write notes that enable a future agent with zero context to continue:

```
COMPLETED: [specific deliverables]
IN PROGRESS: [current state + next step]
BLOCKERS: [what's preventing progress]
KEY DECISIONS: [important context]
NEXT STEPS: [what to do next]
```

### When to Use Beads vs TodoWrite

| Use Beads (bd) | Use TodoWrite |
|----------------|---------------|
| Multi-session work | Single-session tasks |
| Has dependencies | Linear execution |
| Survives compaction | Conversation-scoped |
| Needs git backup | Memory only |

**Decision Rule**: If resuming in 2 weeks would be hard without it, use beads.

---

## Skills

| Skill | Trigger Phrases | Purpose |
|-------|-----------------|---------|
| `create-prd` | "requirements", "PRD", "define feature" | PRD creation workflow |
| `create-architecture` | "architecture", "system design" | Architecture design |
| `dev-story` | "implement story", "TDD" | Story implementation |
| `code-review` | "review code", "check PR" | Confidence-scored review |
| `session-start` | "resume work", "where was I" | Context restoration |
| `beads-integration` | "create task", "what's ready" | Issue tracking |
| `documentation` | "document", "README" | Doc generation |

---

## Templates

All output artifacts use templates from `templates/`:

| Template | Output Location | Purpose |
|----------|-----------------|---------|
| `prd-template.md` | `_prism/planning/prd.md` | Feature requirements |
| `architecture-template.md` | `_prism/architecture/architecture.md` | System design |
| `story-template.md` | `_prism/stories/<id>.md` | Implementation story |
| `review-template.md` | (inline output) | Code review report |

---

## Session Protocol

### On Session Start
1. **Check session notes**: `_prism/session-notes.md`
2. **Check beads status**: `bd ready`
3. **Identify current phase**: Check `_prism/status.yaml`
4. **Resume highest priority work**

### Before Compaction / Session End
1. **Export beads**: `bd export -o _prism/issues-backup.jsonl`
2. **Write session notes** with survival format above
3. **Sync beads to git**: `bd sync`

---

## Don't Do This ❌

- **Skip phase approvals** - Each phase gate requires explicit user approval
- **Implement without tests** - TDD is mandatory, not optional
- **Forget beads export** - Context will be lost on compaction
- **Skip self-review** - Check CLAUDE.md compliance before agent review
- **Hardcode sensitive data** - Use environment variables
- **Ignore the explorer agent** - Always understand before modifying
- **Vague agent invocation** - Always provide specific prompts via Task tool, not just "use the explorer agent"

---

## Agent Model Selection Rationale

| Model | Cost | Speed | Use For |
|-------|------|-------|---------|
| **Haiku** | Low | Fast | Exploration, testing, simple tasks |
| **Sonnet** | Medium | Medium | Implementation, review, most tasks |
| **Opus** | High | Slow | Complex architecture decisions only |

**Default**: Sonnet for balanced quality/cost
**Upgrade to Opus**: Only for critical architecture decisions
**Downgrade to Haiku**: For high-volume, fast, read-only tasks

---

## Project Structure

```
prism/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── .mcp.json                 # MCP server configuration
├── CLAUDE.md                 # This file (agent context)
├── README.md                 # Human documentation
├── agents/                   # 8 agent definitions
├── commands/                 # 4 phase commands
├── skills/                   # 7 SKILL.md files
├── hooks/                    # Event hooks + scripts
└── templates/                # Output templates
```

---

## Related Documentation

- [Implementation Plan](../docs/implementation-plan.md) - Task tracking
- [Vision](../docs/vision.md) - Project goals
- [ADR-001](../docs/adr/ADR-001-direct-claude-code-first.md) - Architecture decision
- [Agent Specs](../docs/specs/agents/) - Detailed agent specifications
- [Skill Specs](../docs/specs/skills/) - Detailed skill specifications
