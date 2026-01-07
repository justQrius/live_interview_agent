---
description: Enable automatic reflection at the end of sessions
---

# Reflect On

Enables the "Auto-Reflect" feature. When enabled, Prism will automatically analyze your session when you stop or exit, ensuring no learning is lost.

## Usage

```
/reflect-on
```

## Actions

1. Create marker file `_prism/learnings/auto-reflect-enabled`
2. specific Stop hook integration (if not already active)
3. Report status: "✅ Auto-Reflect is now ON. Learnings will be captured automatically."

## note
Requires the `Stop` hook to be configured in `.claude/settings.json`.
