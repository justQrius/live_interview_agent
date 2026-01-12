# Live Interview Agent

## Quick Reference

**Status**: Phase 1-3 Complete, Phase 4-5 Implemented
**Project**: AI-powered live interview agent that provides real-time contextual answers and proactive coaching
**Architecture**: `_prism/architecture/architecture-phase4.md`
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
| Python Sidecar | Python 3.11+ | Handles audio/ML/RAG/Coaching |
| IPC | WebSocket (localhost:8765) | JSON message protocol |
| Audio Capture | WASAPI / Core Audio / PulseAudio | Platform-specific |
| VAD | Silero VAD v4 / Browser VAD (ONNX) | Hybrid (Client + Server) |
| STT | Groq / Deepgram / OpenAI / Gemini | Multi-provider support |
| LLM | OpenAI / Anthropic / Gemini | Multi-provider support |
| Embeddings | Gemini text-embedding-004 | 768-dim vectors |
| Vector DB | ChromaDB 0.4.22+ | Local persistent storage |
| Speaker Diarization | ECAPA-TDNN (speechbrain) | Voice embeddings |
| Memory Store | SQLite | Persistent candidate profile |

## Architecture

**Sidecar Pattern**: Tauri app handles UI and OS features, Python sidecar handles audio/ML/RAG/Coaching.

```
┌─────────────────────┐    WebSocket    ┌─────────────────────────────────────┐
│  Tauri (Rust + UI)  │◄───────────────►│         Python Sidecar              │
│  - React frontend   │  localhost:8765 │  - Audio capture & VAD              │
│  - Window manager   │                 │  - Multi-provider STT/LLM           │
│  - Keyring (API key)│                 │  - ChromaDB RAG + Enhanced Engine   │
│  - Coaching UI      │                 │  - Memory Store (SQLite)            │
└─────────────────────┘                 │  - Extraction Pipeline              │
                                        │  - Coaching (Story/Structure/Cons.) │
                                        │  - Gemini Cache & Search Grounding  │
                                        └─────────────────────────────────────┘
```

See `_prism/architecture/architecture-phase4.md` for full Phase 4 details.

## Project Structure

```
live_interview_agent/
├── src/                    # React UI (TypeScript)
│   └── ui/
│       ├── components/     # React components
│       │   ├── AnswerDisplay.tsx
│       │   ├── CoachingPanel.tsx       # Phase 4: Coaching hints container
│       │   ├── ConsistencyPanel.tsx    # Phase 4: Claim tracking
│       │   ├── StorySuggestionCard.tsx # Phase 4: STAR story recall
│       │   ├── StructureHintCard.tsx   # Phase 4: Answer frameworks
│       │   └── ...
│       ├── store/          # Zustand state
│       └── hooks/          # Custom hooks (useWebSocket, useVADFilter)
├── src-tauri/             # Tauri backend (Rust)
│   └── src/
│       ├── commands/       # Tauri IPC commands
│       └── utils/          # Keyring, platform utils
├── sidecar/               # Python sidecar
│   └── src/
│       ├── audio/          # Capture, VAD, diarization, noise reduction
│       ├── classification/ # Question detection, reformulation, splitting
│       ├── coaching/       # Phase 4: Story recall, structure, consistency
│       ├── context/        # Document parsing, chunking, Gemini cache
│       ├── extraction/     # Phase 4: Fact/story extraction pipeline
│       ├── memory/         # Phase 4: Persistent candidate profile
│       ├── playbook/       # Phase 4: Interview preparation generator
│       ├── providers/      # STT/LLM Provider implementations
│       ├── rag/            # ChromaDB + enhanced retrieval engine
│       ├── storage/        # Session and context persistence
│       └── server.py       # WebSocket server
└── _prism/                # SDLC artifacts
    ├── planning/           # PRDs (phase1-4)
    ├── architecture/       # Architecture docs (phase1-4)
    └── tasks.md            # Story tracking
```

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | MVP Foundation | ✅ Complete (20/20 stories) |
| Phase 2 | Multi-Provider & Optimization | ✅ Complete (13/13 stories) |
| Phase 3 | Intelligence Pipeline | ✅ Complete (19/19 stories) |
| Phase 4 | Interview Coach Evolution | 🟡 Implemented |
| Phase 5 | Gemini Integration | 🟡 Implemented |

### Phase 4 Features (Interview Coach)
- **Persistent Memory**: SQLite-backed candidate profile (~1000 tokens)
- **Extraction Pipeline**: Summarize → Extract Facts → Extract Stories → Generate Profile
- **STAR Story Bank**: 8-12 tagged stories from resume
- **Story Recaller**: Embedding similarity matching (<1s latency)
- **Structure Suggester**: STAR, PREP, Pyramid frameworks
- **Consistency Tracker**: Claim logging and contradiction detection

### Phase 5 Features (Gemini Integration)
- **Context Caching**: 2-hour TTL cache for reduced latency
- **Answer Enhancement**: 5 enhancement types (detail, specific, STAR, tone, shorten)
- **Enhanced RAG**: Child-to-parent expansion, question-type awareness
- **Google Search Grounding**: Real-time web research

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
- One module per concern (audio, stt, rag, llm, coaching, memory)
- pytest for testing
- Use `src.` prefix for all imports (e.g., `from src.audio.vad import VADProcessor`)

### IPC Protocol
- WebSocket on localhost:8765
- JSON messages with `type` discriminator
- See AGENTS.md for complete message type reference

## Testing

| Layer | Tool | Command |
|-------|------|---------|
| React UI | Vitest | `npm run test` |
| Rust | cargo test | `cd src-tauri && cargo test` |
| Python | pytest | `cd sidecar && pytest` |
| E2E | pytest | `cd sidecar && pytest tests/test_e2e_scenarios.py` |
| Latency | benchmark | `cd sidecar && python scripts/benchmark_latency.py` |

## Don't Do This

- **Don't embed Python in Rust via PyO3** - Use sidecar pattern instead
- **Don't use Electron** - Tauri is lighter and faster
- **Don't log transcripts/answers to disk** - Privacy requirement
- **Don't skip voice calibration** - Diarization accuracy drops significantly
- **Don't expose WebSocket to network** - localhost only (127.0.0.1)
- **Don't store API keys in plaintext** - Use OS keychain via keyring crate
- **Don't use `from audio.xxx` imports** - Always use `from src.audio.xxx`

## Key NFRs

| Requirement | Target |
|-------------|--------|
| End-to-end latency | <1.5 seconds (P50) |
| Story recall latency | <1 second |
| RAM usage | <500MB |
| CPU (idle) | <5% |
| Session stability | 2 hours, zero crashes |
| Setup time | <5 minutes |
| Profile size | <1500 tokens |

## Workflow

1. `/prism-plan` - Define requirements → PRD ✓
2. `/prism-solution` - Design architecture ✓
3. `/prism-implement` - Build with TDD ✓
4. `/prism-verify` - Test and document ✓

## Next Step

Run `/prism-verify` to execute verification stories or manually verify the application.
