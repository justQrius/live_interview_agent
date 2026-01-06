---
description: Initialize a project for Prism SDLC - creates CLAUDE.md and project structure
argument-hint: Optional project name or path
agent: orchestrator
---

# Prism Initialization

You are initializing a project for use with the Prism SDLC framework. This creates the project CLAUDE.md and sets up the required structure.

## Core Principles

- **Analyze before generating** - Understand what exists before creating
- **Preserve user content** - If CLAUDE.md exists, enhance don't replace
- **Be comprehensive** - Extract all useful patterns from existing code

---

## Phase 1: Project Assessment

**Goal**: Determine project state and existing context

**Actions**:
1. Check if this is a fresh or existing project:
   ```
   - Does src/ or lib/ exist?
   - Does package.json, requirements.txt, etc exist?
   - Does CLAUDE.md already exist?
   - Does _prism/ directory exist?
   ```

2. Classify project:
   - **Fresh**: No source files, minimal config
   - **Existing**: Has source code, established patterns
   - **Already initialized**: Has _prism/ directory

3. Report findings to user

---

## Phase 2: Discovery (for Existing Projects)

**Goal**: Extract patterns and context from codebase

**Actions**:
1. **Identify tech stack** from config files:
   - package.json → Node.js dependencies
   - requirements.txt → Python packages
   - go.mod → Go modules
   - pom.xml / build.gradle → Java
   - Cargo.toml → Rust

2. **Discover project structure**:
   ```
   - List top-level directories
   - Identify src/, tests/, docs/ conventions
   - Note configuration files present
   ```

3. **Extract key patterns**:
   - Look for README.md for workflow hints
   - Check for existing scripts (npm scripts, Makefile)
   - Identify API routes if applicable
   - Note testing framework from test files

4. **Catalog important files**:
   - Entry points (main.ts, index.js, app.py)
   - Configuration (config/, .env.example)
   - Key services or modules

5. **Check for anti-patterns** in existing CLAUDE.md or docs

---

## Phase 3: CLAUDE.md and AGENTS.md Generation

**Goal**: Create or enhance CLAUDE.md and create AGENTS.md for cross-agent compatibility

### AGENTS.md Purpose

AGENTS.md is an [open standard](https://agents.md/) used by 60k+ projects. It provides:
- Cross-agent compatibility (works with Codex, Cursor, Gemini CLI, Aider, etc.)
- Concise build/test/style information
- Complements CLAUDE.md with agent-focused quick reference

### For Fresh Projects:

Create minimal CLAUDE.md scaffold:

```markdown
# [Project Name]

## Quick Reference

**Status**: Early development - using Prism SDLC

## Workflow

1. `/prism-plan` - Define requirements → PRD
2. `/prism-solution` - Design architecture
3. `/prism-implement` - Build with TDD
4. `/prism-verify` - Test and document

## Conventions

[To be established during /prism-solution phase]

## Testing

[To be defined after initial implementation]

## Don't Do This

[Anti-patterns will be documented as discovered]
```

Create AGENTS.md (from templates/agents-template.md):

```markdown
# AGENTS.md

## Setup Commands

- Install dependencies: `npm install` (or detected package manager)
- Run tests: `npm test`
- Build: `npm build`

## Code Style

- Follow conventions in CLAUDE.md

## Testing Instructions

- All tests must pass before committing
- Use TDD: write failing test first, then implement

## Prism SDLC

This project uses the Prism SDLC framework.
See CLAUDE.md for detailed conventions.
```

### For Existing Projects:

Generate comprehensive CLAUDE.md from discoveries:

```markdown
# [Project Name]

## Quick Reference

**Tech Stack:**
- [Discovered technologies]

**Commands:**
- [Discovered scripts/commands]

**Key Files:**
- [Important files discovered]

## Workflow

[Existing patterns + Prism integration]

## Conventions

[Patterns extracted from code analysis]

## Testing

[Testing commands and patterns found]

## Don't Do This

- [Any anti-patterns found]
```

Generate AGENTS.md with discovered values:

```markdown
# AGENTS.md

## Setup Commands

- Install dependencies: `[discovered install command]`
- Run tests: `[discovered test command]`
- Build: `[discovered build command]`
- Dev server: `[discovered dev command]`

## Code Style

[Discovered code style patterns]
- Follow conventions in CLAUDE.md

## Testing Instructions

[Discovered testing patterns]
- All tests must pass before committing

## File Organization

[Discovered project structure]

## Prism SDLC

This project uses the Prism SDLC framework.
See CLAUDE.md for detailed conventions.
```

### For Projects with Existing CLAUDE.md:

**CRITICAL**: Do NOT replace - enhance!
1. Read existing CLAUDE.md
2. Identify sections that can be enhanced
3. Add missing sections only
4. Ask user permission before major additions

### For Projects with Existing AGENTS.md:

1. Read existing AGENTS.md
2. Add Prism SDLC section if not present
3. Reference CLAUDE.md for detailed conventions
4. Do NOT overwrite existing content

---

## Phase 4: Project Structure Setup

**Goal**: Create Prism working directory

**Actions**:
1. Create `_prism/` directory if not exists:
   ```bash
   mkdir -p _prism/planning
   mkdir -p _prism/architecture
   mkdir -p _prism/stories
   ```

2. Create initial status file:
   ```yaml
   # _prism/status.yaml
   phase: initialized
   last_updated: [date]
   current_work: null
   beads_available: [true/false]
   ```

3. **Check beads availability**:
   ```bash
   # Check if bd command exists
   command -v bd
   ```
   
   **If beads IS available**:
   ```bash
   bd status || bd init
   ```
   
   **If beads is NOT available**:
   - Note in status.yaml: `beads_available: false`
   - Create `_prism/tasks.md` as fallback:
     ```markdown
     # Task Tracking (Beads Not Installed)
     
     ## Active Tasks
     [Tasks will be tracked here]
     
     ## Notes
     To enable full tracking, install beads:
     npm install -g @beads/bd
     ```
   - Inform user: "Beads not installed. Using manual task tracking in _prism/tasks.md. For full tracking, install beads."

---

## Phase 5: User Confirmation

**Goal**: Confirm setup with user

**CRITICAL**: Present summary and get approval

**Actions**:
1. Show what was discovered
2. Show what was created/modified
3. Show beads status:
   - If available: "Beads ready - full task tracking enabled"
   - If not: "Beads not installed - using manual tracking (install with: npm install -g @beads/bd)"
4. Show recommended next steps:
   - For fresh project: Run `/prism-plan` to start planning
   - For existing project: Review CLAUDE.md, then `/prism-plan` for new work

---

## Output Checklist

- [ ] CLAUDE.md exists and is appropriate for project state
- [ ] AGENTS.md exists for cross-agent compatibility
- [ ] _prism/ directory created
- [ ] _prism/status.yaml initialized
- [ ] Beads checked (or fallback created if not available)
- [ ] User informed of next steps

---

## Error Handling

**If CLAUDE.md exists and is comprehensive**:
- Ask user if they want enhancements
- Offer to add Prism workflow section only

**If project type unrecognized**:
- Ask user about technology stack
- Create generic scaffold with user-provided info

**If write access issues**:
- Report the error
- Provide manual instructions

**If beads not installed**:
- DO NOT fail or block initialization
- Create `_prism/tasks.md` as fallback
- Inform user how to install beads for full tracking
- Continue with initialization

---

## Beads Installation (Optional)

To enable full task tracking:

```bash
# npm (recommended)
npm install -g @beads/bd

# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Homebrew (macOS)
brew install steveyegge/beads/bd

# Initialize after install
bd init
```

---

## Phase 6: MCP Recommendations

**Goal**: Suggest MCP servers based on detected tech stack

**Actions**:
1. **Check current MCPs**:
   ```
   /mcp
   ```

2. **Map detected tech to MCP recommendations**:

   | Detected | Recommend | Install |
   |----------|-----------|---------|
   | Any project | context7, sequential-thinking | `/mcp add context7` |
   | GitHub repo | github | `/mcp add github` |
   | Has tests | playwright | `/mcp add playwright` |
   | Database refs | postgres/mysql MCP | `/mcp add postgres` |

3. **Present recommendations**:
   ```
   ## MCP Recommendations
   
   Based on your project, consider installing:
   
   **Essential (all projects):**
   /mcp add context7
   /mcp add sequential-thinking
   
   **Project-specific:**
   [Based on tech stack]
   
   These enhance agent capabilities:
   - Explorer: deepwiki for similar project analysis
   - Architect: context7 for library best practices
   - Developer: context7 for API docs
   ```

4. **MCPs are optional** - do not block init if user declines

---

## Output Checklist (Updated)

- [ ] CLAUDE.md exists and is appropriate for project state
- [ ] AGENTS.md exists for cross-agent compatibility
- [ ] _prism/ directory created
- [ ] _prism/status.yaml initialized
- [ ] Beads checked (or fallback created)
- [ ] MCP recommendations presented
- [ ] User informed of next steps
