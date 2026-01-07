#!/bin/bash

# prism-reflect-hook.sh
# Analyzes the last session and proposes learnings if auto-reflect is enabled

# 1. Check if auto-reflect is enabled
if [ ! -f "_prism/learnings/auto-reflect-enabled" ]; then
    # Silently exit if disabled
    exit 0
fi

# 2. Check if we have a valid session context
# (Simple check: is there a recent user message?)
LAST_MSG_TIME=$(stat -c %Y .claude/history.json 2>/dev/null)
NOW=$(date +%s)
DIFF=$((NOW - LAST_MSG_TIME))

# If history is older than 5 minutes, we might not need to reflect immediately, 
# but for now, we'll let the command decide logic.

echo "🧠 Auto-Reflect: Analyzing session for learnings..."

# 3. Trigger the reflection command
# We use the 'last-hour' scope to focus on recent interactions
# and run in a mode that generates suggestions without blocking
claude run "/prism-reflect last-hour --auto"

echo "✨ Reflection complete. Check _prism/learnings/ for proposals."
