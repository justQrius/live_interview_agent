---
name: reflect
description: Analyze interactions for self-learning, corrections, and pattern discovery. Use when user asks to "reflect", "learn from this", or after receiving corrections.
---

# Reflect Skill

This skill analyzes interaction history to extract reusable learnings, corrections, and successes, then formats them for persistent storage.

## Purpose

To enable "one-shot correction" - fixing a mistake once and never repeating it by updating the system's memory.

## When to Use

✅ User says "That's wrong, do X instead"
✅ User says "Remember this for next time"
✅ User says "Great job, that pattern worked"
✅ Session context needs to be distilled into rules
❌ Don't use for temporary/one-off instructions that won't apply later

## Confidence Scoring Rubric

Rate each learning from 0-100:

| Score | Signal Strength | Example |
|-------|----------------|---------|
| **90-100** | Explicit Command | "NEVER use `any` type", "ALWAYS use `logger.info`" |
| **80-89** | Strong Correction | "No, the API endpoint is `/v2/users`, not `/users`" |
| **70-79** | Pattern Approval | "Yes, that factory pattern is exactly what I wanted" |
| **60-69** | Implicit Success | Approach worked without issues (inferred) |
| **50-59** | Observation | "This library seems a bit slow" |
| **<50** | Weak/Noise | "Maybe we could try..." |

## Analysis Workflow

1. **Scan Context**: Look for Correction/Approval signals
2. **Extract Pattern**: "When [situation], do [action] because [reason]"
3. **Score Confidence**: Apply rubric
4. **Identify Target**: 
   - `_prism/learnings/project.md` (General)
   - `_prism/learnings/skills/[skill].md` (Specific skill improvement)

## Output Format

Start with a summary, then list structured findings:

```markdown
# Reflection Analysis

I've analyzed the recent interaction and found [N] learnings:

## 1. [Learning Title] (Confidence: [Score])
- **Pattern**: [Description]
- **Source**: [Quote from user or context]
- **Target**: [File path]
- **Action**: [Add/Update/Delete]

...
```

## Anti-Patterns

- **Over-learning**: Don't create rules for one-off preferences ("I like blue today")
- **Conflict**: Check if new learning contradicts existing High-Confidence rules
- **Vagueness**: Avoid "Write better code" -> Prefer "Use pure functions for logic"
