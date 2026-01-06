import type { Plugin } from "@opencode-ai/plugin"

export const init: Plugin = async (ctx) => {
    return {
        description: "Prism SDLC Session Hooks",
        hooks: {
            SessionStart: [
                {
                    type: "prompt",
                    prompt: `Starting new session. Check for prior context:
1. Read _prism/session-notes.md if exists
2. Check _prism/status.yaml for current phase
3. If beads available, run 'bd ready' to find pending work

Summarize any context found and suggest what to work on next. Return 'approve' with context summary.`,
                    timeout: 30
                }
            ],
            PreCompact: [
                {
                    type: "prompt",
                    prompt: `Before context compaction, preserve important context:
1. Check if beads is available and export issues with 'bd export -o _prism/issues-backup.md'
2. Write session summary to _prism/session-notes.md with COMPLETED, IN PROGRESS, NEXT STEPS format
3. Note any critical decisions or blockers

Perform these actions now and return 'approve' with summary of what was saved.`,
                    timeout: 30
                }
            ],
            Stop: [
                {
                    type: "prompt",
                    prompt: `Verify task completion before stopping. Check:
1. If working on a story, are all acceptance criteria met?
2. If tests were expected, did they run and pass?
3. Were any beads issues that should be updated?
4. Were session notes written for context preservation?

Return 'approve' if complete, or 'block' with specific missing items.`,
                    timeout: 30
                }
            ]
        }
    }
}
