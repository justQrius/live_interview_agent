#!/bin/bash

# prism-gate-hook.sh
# Validates phase gates before allowing phase transitions

# Read current status
STATUS_FILE="_prism/status.yaml"

if [ ! -f "$STATUS_FILE" ]; then
    echo "Success"
    exit 0
fi

# Extract current phase (simple grep, works on Windows git bash)
CURRENT_PHASE=$(grep "^phase:" "$STATUS_FILE" | cut -d':' -f2 | tr -d ' ')

# Check if user prompt mentions phase transition commands
# This is a soft check - the actual validation happens in the skill
echo "Success"
exit 0
