---
description: Manage session todos as attention anchors - keeps goals in recent context
argument-hint: Optional action (show|add|done|clear) and text
---

# Prism Todo - Attention Anchor Management

This command manages a `todo.md` file that serves as an **attention anchor** - keeping your current goals in the model's recent attention span to prevent "lost-in-the-middle" drift.

## Why This Matters

As context grows, LLMs suffer from attention degradation. Goals stated at the start of a session get "buried" by newer content. By periodically referencing `todo.md`, you push critical objectives back into recent attention.

## Usage

```
/prism-todo              # Show current todos
/prism-todo add [text]   # Add a todo item
/prism-todo done [num]   # Mark item as complete
/prism-todo clear        # Clear completed items
```

---

## Phase 1: Initialize or Load

**Actions**:
1. Check if `_prism/todo.md` exists
2. If not, create it:
   ```markdown
   # Session Todos - Attention Anchor
   
   > This file keeps current goals in recent attention. Reference it regularly.
   
   ## Current Focus
   - [ ] [No todos yet]
   
   ## Completed This Session
   [None yet]
   ```

3. Read current contents

---

## Phase 2: Execute Command

Based on $ARGUMENTS:

### Show (default)
Display current todos and remind about their purpose:
```
📋 Current Session Todos (Attention Anchor):

1. [ ] Complete implementation of authentication
2. [ ] Add tests for edge cases
3. [x] Set up project structure

💡 Tip: These todos keep your goals in recent attention. 
Reference this file when context grows large.
```

### Add [text]
1. Add new item to "Current Focus" section
2. Use `- [ ]` format
3. Confirm addition

### Done [number]
1. Mark item as `[x]`
2. Move to "Completed This Session" section
3. Show updated list

### Clear
1. Remove all `[x]` items from Current Focus
2. Archive to Completed section with timestamp

---

## Phase 3: Context Budget Check

After any todo operation, check context usage:

```
/context
```

If context > 50%:
```
⚠️ Context at [X]%. Consider:
- Running /compact to summarize
- Starting fresh session with /prism-handoff
- Using Task tool for exploratory work
```

---

## Attention Anchor Best Practices

1. **Start sessions by reviewing todos** - Brings goals to top of attention
2. **Add todos for each major goal** - Explicit > implicit
3. **Check todos before major decisions** - Ensures alignment
4. **Update todos as scope changes** - Keep them current
5. **Reference todos at 50% context** - Refresh attention

---

## Integration Points

- **Session start**: `session-start` skill should reference todo.md
- **Compaction**: `PreCompact` hook should save todos
- **Handoff**: `/prism-handoff` should include todo status

---

## Output Example

```
📋 Session Todos (Attention Anchor)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Focus:
1. [ ] Implement user authentication flow
2. [ ] Add rate limiting to API endpoints
3. [ ] Write integration tests for auth

Completed:
✓ Set up project structure
✓ Create database schema

Context: 42% | Status: ✅ Healthy
```
