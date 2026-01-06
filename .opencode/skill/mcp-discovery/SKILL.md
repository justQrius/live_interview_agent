---
name: mcp-discovery
description: Use this when the user mentions "setup MCP", "install tools", or needs enhanced capabilities. Recommends and installs MCP servers.
allowed-tools: "Read,Glob,Bash"
version: "1.0.0"
---

# MCP Discovery - Enhanced Tool Setup

Helps users discover and install MCP servers that enhance Prism agent capabilities.

## Overview

This skill:
- Analyzes project tech stack
- Recommends relevant MCP servers
- Provides installation commands
- Explains agent enhancements

## Instructions

### Step 1: Check Current MCP Status

Run `/mcp` or equivalent to see what's already installed.

### Step 2: Analyze Project Tech Stack

Check for indicators:
```
package.json → JavaScript/TypeScript project
requirements.txt → Python project
go.mod → Go project
Cargo.toml → Rust project
*.test.*, *.spec.* → Has testing
.github/ → GitHub integration
```

### Step 3: Map Tech Stack to MCP Recommendations

| Detected | Recommended MCP | Install Command |
|----------|-----------------|-----------------|
| Any project | context7 | `/mcp add context7` |
| Any project | sequential-thinking | `/mcp add sequential-thinking` |
| GitHub repo | github | `/mcp add github` |
| Has tests | playwright | `/mcp add playwright` |
| PostgreSQL | postgres | `/mcp add postgres` |
| React/Vue/Angular | context7 | (for framework docs) |
| Node.js | context7 | (for npm package docs) |
| Python | context7 | (for PyPI package docs) |

### Step 4: Present Recommendations

Format output as:

```
## MCP Recommendations for [Project Name]

**Detected Tech Stack:**
- [Technology 1]
- [Technology 2]

**Recommended MCPs:**

### Essential (All Projects)
/mcp add context7        # Library documentation
/mcp add sequential-thinking  # Complex problem solving

### Project-Specific
/mcp add [specific]      # [Reason]

**To install all recommended:**
```

### Step 5: Explain Agent Enhancements

Show which agents benefit:
- **Explorer**: deepwiki for analyzing similar projects
- **Architect**: context7 for library best practices
- **Developer**: context7 for API documentation
- **Tester**: playwright for browser testing

## Tech Stack Detection

### JavaScript/TypeScript
```bash
# Check package.json
cat package.json | grep -E "(react|vue|angular|express|next|nest)"
```

### Python
```bash
# Check requirements or pyproject
cat requirements.txt 2>/dev/null || cat pyproject.toml 2>/dev/null
```

### Databases
```bash
# Check for database config
grep -r "postgres\|mysql\|mongo" . --include="*.json" --include="*.yaml" --include="*.env*" 2>/dev/null | head -5
```

## MCP Server Reference

### context7
- **Purpose**: Library documentation lookup
- **Agents**: architect, developer
- **Install**: `/mcp add context7`
- **Usage**: Ask for library best practices, API docs

### deepwiki
- **Purpose**: GitHub repository analysis
- **Agents**: explorer
- **Install**: `/mcp add deepwiki`
- **Usage**: Analyze similar projects, learn patterns

### sequential-thinking
- **Purpose**: Complex reasoning and decomposition
- **Agents**: architect, pm
- **Install**: `/mcp add sequential-thinking`
- **Usage**: Architecture decisions, problem breakdown

### github
- **Purpose**: GitHub integration
- **Agents**: all (for issues/PRs)
- **Install**: `/mcp add github`
- **Usage**: Create issues, review PRs

### playwright
- **Purpose**: Browser automation
- **Agents**: tester
- **Install**: `/mcp add playwright`
- **Usage**: E2E testing, screenshots

### sentry
- **Purpose**: Error monitoring
- **Agents**: tester, developer
- **Install**: `/mcp add sentry`
- **Usage**: Debug production issues

## Output

- List of installed MCPs
- Recommendations based on tech stack
- Install commands ready to run
- Agent enhancement explanations

## Quality Checklist

- [ ] Current MCPs checked
- [ ] Tech stack analyzed
- [ ] Recommendations provided
- [ ] Install commands given
- [ ] Agent benefits explained
