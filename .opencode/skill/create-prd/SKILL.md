---
name: create-prd
description: Use this when the user mentions "create PRD", "define requirements", or "product planning". Guides structured requirements gathering and PRD documentation.
allowed-tools: "Read,Write,Glob,Grep,TodoWrite"
version: "1.0.0"
---

# Create PRD - Requirements Documentation Workflow

Guides creation of complete Product Requirements Documents through structured discovery and documentation.

## Overview

This skill:
- Asks clarifying questions to understand needs
- Gathers functional and non-functional requirements
- Creates structured PRD document
- Validates for completeness
- Creates beads issues for tracking

## Instructions

### Step 1: Discovery

Ask clarifying questions before documenting:

1. **Problem**: What problem are we solving?
2. **Users**: Who are the target users?
3. **Success**: What defines success?
4. **Constraints**: What are the constraints?
5. **Timeline**: What's the priority/timeline?

**CRITICAL: Wait for user answers before proceeding.**

### Step 2: Requirements Gathering

From user answers, derive:

- **Functional Requirements**: What the system does
- **Non-Functional Requirements**: How the system performs
- **User Personas**: Who uses the system and their needs
- **Use Cases**: Key user journeys

### Step 3: Create PRD

Write to `_prism/planning/prd.md`:

```markdown
# PRD: [Feature Name]

## Problem Statement
[Clear problem description with user pain points and business impact]

## Goals
- [Measurable goal 1]
- [Measurable goal 2]

## Non-Goals
- [Explicitly out of scope item]

## User Personas

### [Persona Name]
- **Description**: [Who they are]
- **Needs**: [What they need]
- **Pain Points**: [Current frustrations]

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | [Description] | Must Have | [Testable criterion] |
| FR-2 | [Description] | Should Have | [Testable criterion] |

## Non-Functional Requirements

| ID | Requirement | Priority | Metric |
|----|-------------|----------|--------|
| NFR-1 | Performance | Must Have | [Target, e.g., <200ms] |
| NFR-2 | Security | Must Have | [Standard] |

## Success Metrics
- [Metric 1 with target]
- [Metric 2 with target]

## Dependencies
- [External dependencies]

## Open Questions
- [ ] [Unresolved question 1]
- [ ] [Unresolved question 2]
```

### Step 4: Validation

1. Check for completeness (all sections filled)
2. Verify no ambiguity (requirements are testable)
3. Present to user for approval
4. Iterate based on feedback

### Step 5: Create Beads Issues

After PRD approval:

```bash
# Create epic for the feature
bd create "Epic: [Feature Name]" -p 1 --type epic
# Returns: <epic-id>

# Create issues for each requirement
bd create "FR-1: [Requirement]" -p 1 --type task --parent <epic-id>
bd create "FR-2: [Requirement]" -p 2 --type task --parent <epic-id>
```

## Output

- `_prism/planning/prd.md` - Complete PRD document
- Beads issues for each requirement

## Quality Checklist

- [ ] Requirements are testable (measurable criteria)
- [ ] No ambiguous language ("should", "may")
- [ ] All user types considered
- [ ] Edge cases documented
- [ ] Dependencies identified
- [ ] Beads issues created
