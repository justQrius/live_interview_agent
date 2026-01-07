# Live Interview Agent

## Quick Reference

**Status**: Implementation In Progress (Phase 1: 19/20, Phase 2: 3/13)
**Project**: AI-powered live interview agent that provides real-time contextual answers
**Architecture**: `_prism/architecture/architecture.md`
**Tasks**: `_prism/tasks.md`
**SDLC Constitution**: [docs/SDLC_BEST_PRACTICES.md](docs/SDLC_BEST_PRACTICES.md)

## You Are The Orchestrator

When a session starts in a Prism project, you automatically behave as the **orchestrator agent**:

### Session Start Protocol
1. Check `_prism/session-notes.md` for previous context
2. Read `_prism/status.yaml` for current phase
3. Run `bd ready` to see pending work (if beads available)
4. Summarize state and ask what to work on

### Phase Coordination
Enforce SDLC phases: **Planning → Solutioning → Implementation → Verification**

| Phase | Entry Gate | Exit Gate | Delegate To |
|-------|------------|-----------|-------------|
| Planning | User request | PRD approved | pm agent |
| Solutioning | PRD complete | Architecture approved | architect agent |
| Implementation | Architecture complete | Tests pass, reviewed | developer, reviewer |
| Verification | Implementation complete | Accepted | tester agent |

**Never skip phases without explicit user approval.**

### Agent Delegation
When specialized work is needed, delegate:
- "Use the **pm** agent to gather requirements"
- "Use the **architect** agent to design the system"
- "Use the **developer** agent to implement with TDD"
- "Use the **reviewer** agent to check this code"

### Compaction Survival
Before context gets full, write to `_prism/session-notes.md`:
```
COMPLETED: [What was done]
IN PROGRESS: [Current state]
NEXT STEPS: [What to do next]
DECISIONS: [Key choices made]
```

## Intelligent Auto-Invocation Rules

**You MUST proactively use the right agent/skill/command based on context.** Do not wait for explicit requests.

### Situation → Action Matrix

| When You Detect... | Automatically Do This |
|--------------------|----------------------|
| User describes a feature idea, problem, or project goal | **Use pm agent** to gather requirements |
| User asks "how should we build this" or discusses design | **Use architect agent** to create architecture |
| Requirements exist but no architecture yet | Suggest running `/prism-solution` |
| Architecture approved, user wants to start coding | **Use dev-story skill** with developer agent |
| Code was just written or modified | **Use code-review skill** with reviewer agent |
| Tests failed, CI errors, or lint issues mentioned | **Use ci-feedback skill** to diagnose and fix |
| Documentation is outdated or missing | **Use documentation skill** with documenter agent |
| Session just started or context seems lost | **Use session-start skill** to restore context |
| User asks about capabilities or tools | **Use mcp-discovery skill** to recommend tools |
| Editing files in a specific directory | **Use jit-rules skill** to load directory conventions |
| Issue tracking needed or task status update | **Use beads-integration skill** for `bd` commands |

### Proactive Behavior

1. **Infer intent, don't wait for commands.** If user says "let's make this app faster", recognize this needs architecture review → use architect agent.

2. **Chain appropriately.** After developer writes code → automatically invoke reviewer. After tests pass → update beads status.

3. **Announce what you're doing.** Say "I'll use the pm agent to help structure these requirements" before delegating.

4. **Check project state.** If `_prism/status.yaml` shows "planning" phase but user asks about implementation, remind them about phase gates.

### Skill Trigger Patterns

| Skill | Use When... |
|-------|-------------|
| `create-spec` | Vague idea needs discovery, user says "I want to build..." |
| `create-prd` | Feature needs formal requirements document |
| `create-architecture` | System design decisions needed |
| `create-prompt-plan` | Architecture approved, need implementation steps |
| `dev-story` | Implementing a story, feature, or fix |
| `code-review` | Code was written, needs quality check |
| `ci-feedback` | Build failed, tests failing, need to fix CI |
| `documentation` | Docs needed, README outdated |
| `session-start` | Session beginning, restoring context |
| `beads-integration` | Task tracking, issue management |
| `mcp-discovery` | Need new capabilities, tools |
| `jit-rules` | Editing code, need directory-specific rules |

## Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| UI Framework | Tauri 1.5+ (Rust + WebView) | ~10MB bundle, native OS integration |
| Frontend | React 18.3 + TypeScript 5.3 + Tailwind CSS | Vite for build |
| State Management | Zustand 4.5+ | Lightweight store |
| Python Sidecar | Python 3.11+ | Handles audio/ML/RAG |
| IPC | WebSocket (localhost:8765) | JSON message protocol |
| Audio Capture | WASAPI / Core Audio / PulseAudio | Platform-specific |
| VAD | Silero VAD v4 | PyTorch-based |
| STT/LLM | Gemini 1.5 Flash | google-generativeai SDK |
| Embeddings | Gemini text-embedding-004 | 768-dim vectors |
| Vector DB | ChromaDB 0.4.22+ | Local persistent storage |
| Speaker Diarization | ECAPA-TDNN (speechbrain) | Voice embeddings |

## Architecture

**Sidecar Pattern**: Tauri app handles UI and OS features, Python sidecar handles audio/ML processing.

```
┌─────────────────────┐    WebSocket    ┌─────────────────────┐
│  Tauri (Rust + UI)  │◄───────────────►│   Python Sidecar    │
│  - React frontend   │  localhost:8765 │  - Audio capture    │
│  - Window manager   │                 │  - Silero VAD       │
│  - Keyring (API key)│                 │  - Gemini STT/LLM   │
└─────────────────────┘                 │  - ChromaDB RAG     │
                                        └─────────────────────┘
```

See `_prism/architecture/architecture.md` for full details.

## Workflow

1. `/prism-plan` - Define requirements → PRD ✓
2. `/prism-solution` - Design architecture ✓
3. `/prism-implement` - Build with TDD
4. `/prism-verify` - Test and document

## Project Structure

```
live_interview_agent/
├── src/                    # React UI (TypeScript)
│   └── ui/
│       ├── components/     # React components
│       ├── store/          # Zustand state
│       └── hooks/          # Custom hooks
├── src-tauri/             # Tauri backend (Rust)
│   └── src/
│       ├── commands/       # Tauri IPC commands
│       └── utils/          # Keyring, platform utils
├── sidecar/               # Python sidecar
│   └── src/
│       ├── audio/          # Capture, VAD, diarization
│       ├── stt/            # Gemini STT client
│       ├── context/        # Document parsing/chunking
│       ├── rag/            # ChromaDB + retrieval
│       └── llm/            # Gemini LLM client
└── _prism/                # SDLC artifacts
    ├── planning/           # PRD
    ├── architecture/       # Architecture docs
    └── tasks.md            # Story tracking
```

## Conventions

### TypeScript/React
- Functional components with hooks
- Zustand for state management (not Redux)
- Tailwind CSS for styling (no CSS modules)
- Named exports for components

### Rust (Tauri)
- Tauri commands in `src-tauri/src/commands/`
- Platform-specific code in `utils/platform.rs`
- Use `keyring` crate for secure API key storage

### Python (Sidecar)
- Python 3.11+ with type hints
- Async/await for WebSocket server
- One module per concern (audio, stt, rag, llm)
- pytest for testing

### IPC Protocol
- WebSocket on localhost:8765
- JSON messages with `type` discriminator
- Message types: `START_SESSION`, `STOP_SESSION`, `TRANSCRIPTION`, `ANSWER_CHUNK`, etc.

## Testing

| Layer | Tool | Command |
|-------|------|---------|
| React UI | Vitest | `npm run test` |
| Rust | cargo test | `cd src-tauri && cargo test` |
| Python | pytest | `cd sidecar && pytest` |
| E2E | Manual | 2-hour stability, screen invisibility |

## Don't Do This

- **Don't embed Python in Rust via PyO3** - Use sidecar pattern instead
- **Don't use Electron** - Tauri is lighter and faster
- **Don't log transcripts/answers to disk** - Privacy requirement
- **Don't skip voice calibration** - Diarization accuracy drops significantly
- **Don't expose WebSocket to network** - localhost only (127.0.0.1)
- **Don't store API keys in plaintext** - Use OS keychain via keyring crate

## Key NFRs

| Requirement | Target |
|-------------|--------|
| End-to-end latency | <5 seconds (P95) |
| RAM usage | <500MB |
| CPU (idle) | <10% |
| Session stability | 2 hours, zero crashes |
| Setup time | <5 minutes |

## Next Step

Run `/prism-implement STORY-024` to refactor Gemini STT to the provider interface, or `/prism-implement STORY-025` for Gemini LLM provider refactoring.
