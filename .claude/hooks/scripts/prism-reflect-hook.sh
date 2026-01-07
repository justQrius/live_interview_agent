#!/bin/bash

# prism-reflect-hook.sh
# Analyzes the session for learnings if auto-reflect is enabled

# 1. Check if auto-reflect is enabled
if [ ! -f "_prism/learnings/auto-reflect-enabled" ]; then
    # Silently exit if disabled
    exit 0
fi

# 2. Trigger reflection analysis
echo "Auto-Reflect: Session analysis triggered..."

# Note: This hook signals that reflection should happen
# The actual reflection is handled by the agent
exit 0
