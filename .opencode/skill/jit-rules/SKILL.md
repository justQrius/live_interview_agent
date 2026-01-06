---
name: jit-rules
description: Use this when editing code or checking conventions. Loads project rules from .claude/rules/ based on file proximity.
allowed-tools: "Read,Glob,Grep"
version: "1.0.0"
---

# JIT Rules - Just-in-Time Context Loading

Guides the pattern of loading directory-specific rules based on proximity to the file being edited.

## Overview

This is an **elite context engineering pattern** that prevents context window bloat by loading only the rules relevant to the current file's directory, rather than all project rules at once.

## The Problem

Loading all project rules at startup wastes context window space:
- Frontend rules are irrelevant when editing backend code
- Database patterns aren't needed when working on UI
- Test conventions don't apply when editing configs

## The Solution: Proximity-Based Rules

Rules are loaded **on-demand** based on which file is being edited:

```
When editing: src/db/user.ts
Load rules from (in priority order):
1. src/db/.claude/rules/*.md       (closest - highest priority)
2. src/.claude/rules/*.md          (parent directory)
3. .claude/rules/*.md              (project root)
4. ~/.claude/rules/*.md            (global - lowest priority)
```

## Rule File Structure

### Location Convention

```
project/
├── .claude/rules/                  # Project-wide rules
│   ├── coding-standards.md
│   └── error-handling.md
├── src/
│   ├── api/.claude/rules/          # API-specific rules
│   │   └── rest-conventions.md
│   ├── db/.claude/rules/           # Database-specific rules
│   │   ├── sql-patterns.md
│   │   └── migration-rules.md
│   └── ui/.claude/rules/           # Frontend-specific rules
│       └── react-patterns.md
└── tests/.claude/rules/            # Test-specific rules
    └── testing-conventions.md
```

### Rule File Format

Use YAML frontmatter with optional glob patterns:

```yaml
---
globs: ["*.ts", "*.tsx"]       # Optional: Only apply to these files
alwaysApply: false             # If true, always load regardless of location
description: React component patterns for UI development
---

# React Patterns

## Component Structure
- Use functional components with hooks
- Props interface must be exported
- One component per file

## State Management
- Local state with useState for component-scoped data
- Context for shared state within feature boundaries
- Avoid prop drilling beyond 2 levels
```

## When to Load Rules

### Automatic Triggers

Load rules when:
1. **Opening a file for editing** - Check for `.claude/rules/` in the file's directory chain
2. **Switching to a new directory** - Load rules for the new context
3. **Starting a new task** - Identify affected directories and preload their rules

### Manual Check Pattern

```bash
# Find rules applicable to a file
find_rules() {
  local file="$1"
  local dir=$(dirname "$file")
  
  while [ "$dir" != "." ] && [ "$dir" != "/" ]; do
    if [ -d "$dir/.claude/rules" ]; then
      echo "Rules found: $dir/.claude/rules/"
      ls "$dir/.claude/rules/"
    fi
    dir=$(dirname "$dir")
  done
}
```

## Integration with Prism Workflow

### During Implementation

When `/prism-implement` is run:
1. Identify files to be modified from the story
2. For each file's directory, check for `.claude/rules/`
3. Load applicable rules before writing code
4. Reference rules in implementation decisions

### During Review

When `/prism-verify` runs parallel reviewers:
1. Reviewers should check code against directory-specific rules
2. Report violations with reference to the specific rule file
3. Higher priority (closer) rules override lower priority (farther) rules

## Creating Effective Rules

### Good Rule: Specific and Actionable

```markdown
# API Error Handling (src/api/.claude/rules/)

## Required Pattern
All API endpoints MUST:
1. Wrap handler in try/catch
2. Log errors with request ID
3. Return standardized error response

## Example
```typescript
try {
  // handler logic
} catch (error) {
  logger.error({ requestId, error });
  return { error: 'Internal server error', code: 500 };
}
```
```

### Bad Rule: Vague and General

```markdown
# General Rules
- Write good code
- Handle errors properly
- Follow best practices
```

## Benefits

- **Context Efficiency**: Only relevant rules in context window
- **Modularity**: Teams can own their component's rules
- **Discoverability**: Rules live near the code they govern
- **Maintainability**: Update rules without touching global config

## Quality Checklist

- [ ] Rules placed in `.claude/rules/` directories
- [ ] Specific globs used to target file types
- [ ] Rules are actionable with examples
- [ ] Priority is clear (closer = higher priority)
- [ ] Rules don't conflict with parent directory rules
