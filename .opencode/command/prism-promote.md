---
description: Promote a project learning to a universal (cross-project) learning
argument-hint: Optional pattern ID or text
---

# Prism Promote - Cross-Project Learning

Promotes a high-confidence learning from project scope to universal scope, making it available to ALL projects on your machine.

## Why This Matters

Don't solve the same problem in every project. If you discover a universal truth (e.g., "This specific library version is broken", "Always use X pattern for Y"), promote it!

## Usage

```
/prism-promote              # Interactive promotion flow
/prism-promote "pattern"    # Promote specific text
```

---

## Phase 1: Identify Candidates

**Actions**:
1. Read `_prism/learnings/project.md`
2. Filter for "High Confidence" items
3. Present candidates to user:
   > "Found 3 candidates for promotion:"
   > 1. [TypeScript] Never use `enum`, use `const object`
   > 2. [React] Always wrap context providers in memo
   > 3. [Project-Specific] Use port 3000 (Ignored - too specific)

---

## Phase 2: Select & Refine

1. Ask user which item to promote
2. Ask user to generalize it (remove project specifics)
3. Ask for category (Language, Framework, Tooling, General)

---

## Phase 3: Update Universal Storage

**Actions**:
1. Check if `~/.claude/learnings/universal.md` exists, create if not
2. Append learning to universal file:

```markdown
### [Category]
- **[Pattern]**
  - *Source Project*: [Current Project]
  - *Date*: [Today]
```

3. Mark item in `_prism/learnings/project.md` as "Promoted"

---

## Phase 4: Confirmation

> "✅ Promoted to Universal Learnings! This pattern will now be available in all your Prism projects."

---

## Future Integration

When starting a new project (`/prism-init`), Prism will suggest reading `~/.claude/learnings/universal.md` to bootstrap knowledge.
