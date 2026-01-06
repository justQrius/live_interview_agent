---
name: create-spec
description: Use this when the user mentions "discover requirements", "start new project", "brainstorm", or lacks clear specs. Creates structured specification document through iterative discovery.
allowed-tools: "Read,Write,Grep,Glob,TodoWrite"
version: "1.0.0"
---

# Create Spec Skill

## Purpose

Create a comprehensive specification document (`spec.md`) through structured discovery before PRD creation. This is the "waterfall in 15 minutes" - rapid, structured planning that makes subsequent development smoother.

## When to Use

- Starting a new project or feature
- User has an idea but requirements are unclear
- Before `/prism-plan` command
- When vague requests need structure

## Discovery Process

### Phase 1: Initial Brainstorm (Iterative Q&A)

Ask the user these questions ONE AT A TIME, waiting for responses:

1. **Problem Statement**
   > "What problem are we solving? Why does it matter?"

2. **Target Users**
   > "Who will use this? What are their main characteristics?"

3. **Success Definition**
   > "What defines success? How will we know this works?"

4. **Constraints**
   > "What are the constraints? (Time, budget, tech stack, integrations)"

5. **Priority**
   > "What's the timeline? What's must-have vs nice-to-have?"

**IMPORTANT**: Do not proceed until each question is answered. Take notes on each response.

### Phase 2: Edge Case Discovery

After gathering basics, probe for edge cases:

> "Let's think about edge cases. What happens when:
> - A user does X in an unexpected way?
> - The system is under heavy load?
> - Data is missing or malformed?
> - A user tries to abuse the feature?"

Document all edge cases identified.

### Phase 3: Requirements Synthesis

From the answers, derive:
- Functional requirements (numbered FR-1, FR-2, etc.)
- Non-functional requirements (numbered NFR-1, NFR-2, etc.)
- Testing strategy outline

### Phase 4: Spec Document Creation

Write to `_prism/discovery/spec.md` using the template:

```markdown
# Spec: [Feature/Project Name]

## Overview
[One sentence summary]

## Problem Statement
[From Q1 answer]

## Target Users
### Primary Persona
- **Name**: [Derived from Q2]
- **Role**: [User type]
- **Goals**: [What they want to achieve]
- **Pain Points**: [Current frustrations]

## Discovery Questions Answered
[Document all Q&A from Phase 1]

## Edge Cases Identified
| Edge Case | How to Handle |
|-----------|---------------|
| [Case 1] | [Approach] |

## Requirements Summary
### Functional Requirements
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | [Requirement] | Must Have |

### Non-Functional Requirements  
| ID | Requirement | Metric |
|----|-------------|--------|
| NFR-1 | [Requirement] | [Target] |

## Testing Strategy Outline
- **Unit Tests**: [Coverage areas]
- **Integration Tests**: [Integration points]
- **E2E Tests**: [User flows]

## Open Questions
- [ ] [Any unresolved items]

## Next Step
**Proceed to**: PRD creation using `/prism-plan` command

---
*Spec created: [DATE]*
*Status: Draft*
```

### Phase 5: Review and Approval

Present the spec to the user:

> "Here's the specification I've created based on our discovery:
> 
> [Summary of key points]
> 
> Does this capture your vision? Any changes needed before we proceed to detailed PRD creation?"

Wait for approval before marking complete.

## Output

| Artifact | Location |
|----------|----------|
| Spec Document | `_prism/discovery/spec.md` |

## Quality Checklist

- [ ] All 5 discovery questions answered
- [ ] Edge cases explored and documented
- [ ] Requirements are numbered and prioritized
- [ ] Testing strategy outlined
- [ ] User has approved the spec
- [ ] Open questions are captured (if any)

## Next Step

After spec approval, proceed to `/prism-plan` which will use this spec as input for detailed PRD creation.

## Related Template

See `templates/spec-template.md` for the full template structure.
