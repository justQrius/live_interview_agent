---
description: Analyze session for learnings and capture them to project memory or skills
argument-hint: Optional scope (session|last-hour|correction)
---

# Prism Reflect - Self-Learning

This command analyzes the current session (or specified scope) to extract learnings, corrections, and useful patterns. It then facilitates updating the project's persistent memory.

## Why This Matters

"Correct once, never again." By capturing corrections and successes as persistent learnings, you improve the agent's performance over time and reduce repetition.

## Usage

```
/prism-reflect              # Reflect on entire current session
/prism-reflect last-hour    # Reflect on recent interactions
/prism-reflect correction   # Focus specifically on recent corrections
/prism-reflect [text]       # Manually add a specific learning
```

---

## Phase 1: Analyze Session

**Actions**:
1. Scan conversation history for:
   - **Corrections**: "No, not like that", "Change X to Y", "Don't use Z"
   - **Approvals**: "That's perfect", "Great job", "This works well"
   - **Repeated Patterns**: Solutions applied multiple times
2. Identify the confidence level (High/Medium/Low)
3. Correlate with active skills

---

## Phase 2: Propose Learnings

Present extracted learnings for user review:

```markdown
# Proposed Learnings

## High Confidence (Updates to ALWAYS/NEVER)
1. **NEVER** use `var` in TypeScript files (Confidence: 95)
   - *Source*: User correction "Don't use var"
   - *Target*: `_prism/learnings/project.md`

## Medium Confidence (Good Patterns)
2. Use `zod` for all API schema validation (Confidence: 80)
   - *Source*: Successful implementation of auth module
   - *Target*: `_prism/learnings/project.md`

## Skill Updates
3. `code-review` skill: Add check for `console.log`
   - *Source*: Review feedback loop
   - *Target*: `_prism/learnings/skills/code-review.md`
```

---

## Phase 3: Apply Updates

**Actions**:
1. Ask user for confirmation: "Apply these updates? (y/n/edit)"
2. If confirmed:
   - **Project Learnings**: Append to `_prism/learnings/project.md`
   - **Skill Updates**: 
     - Check if `_prism/learnings/skills/[skill].md` exists
     - If not, copy from `.claude/skills/[skill]/SKILL.md`
     - Apply changes to the copy
3. **Commit**:
   - `git add _prism/learnings/`
   - `git commit -m "chore: capture learnings from session"`

---

## Phase 4: Cross-Project Promotion (Optional)

If a learning seems universal (High confidence, generic):
- Suggest running `/prism-promote` to move it to `~/.claude/learnings/universal.md`

---

## Output Example

```
✅ Captured 3 new learnings
📝 Updated _prism/learnings/project.md
🧠 Updated _prism/learnings/skills/code-review.md
💾 Committed to git
```
