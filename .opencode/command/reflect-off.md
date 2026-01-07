---
description: Disable automatic reflection
---

# Reflect Off

Disables the "Auto-Reflect" feature. Learnings will only be captured when you manually run `/prism-reflect` or specifically in phase transitions.

## Usage

```
/reflect-off
```

## Actions

1. Remove marker file `_prism/learnings/auto-reflect-enabled`
2. Report status: "❌ Auto-Reflect is now OFF. Use /prism-reflect to capture learnings manually."
