# AGENTS.md

## Setup Commands

### Tauri App (Frontend + Rust Backend)
```bash
# Install Node dependencies
npm install

# Install Rust (if not installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Tauri CLI
npm install -g @tauri-apps/cli

# Run development mode
npm run tauri dev

# Build for production
npm run tauri build
```

### Python Sidecar
```bash
# Create virtual environment
cd sidecar
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run standalone (development)
python src/server.py
```

### Run Tests
```bash
# React UI tests
npm run test

# Rust tests
cd src-tauri && cargo test

# Python tests
cd sidecar && pytest

# End-to-End Latency Benchmark (requires server running)
cd sidecar && python scripts/benchmark_latency.py
```

## Code Style

### TypeScript/React
- Functional components with hooks
- Zustand for state management
- Tailwind CSS for styling
- Named exports for components
- Strict TypeScript (`strict: true`)

### Rust (Tauri)
- Tauri commands in `src-tauri/src/commands/`
- Platform-specific code in `utils/platform.rs`
- Use `keyring` crate for secure API key storage
- Handle all errors with `Result<T, String>`

### Python (Sidecar)
- Python 3.11+ with type hints
- Async/await for WebSocket server
- **Provider Pattern**: Implement `STTProvider` or `LLMProvider` interfaces for new AI services
- **Factory Pattern**: Use `ProviderFactory` for instantiation
- Black formatter, isort for imports

## Testing Instructions

- All tests must pass before committing
- Use TDD: write failing test first, then implement
- Test coverage targets:
  - Python: >80% for core modules
  - TypeScript: >70% for components
  - Rust: Unit tests for commands

## Architecture Overview

```
┌─────────────────────┐    WebSocket    ┌─────────────────────┐
│  Tauri (Rust + UI)  │◄───────────────►│   Python Sidecar    │
│  - React frontend   │  localhost:8765 │  - Provider Factory │
│  - Browser VAD      │                 │  - Groq/OpenAI/etc  │
│  - Keyring (Keys)   │                 │  - RAG Engine       │
└─────────────────────┘                 │  - Pre-warmed Models│
                                        └─────────────────────┘
```

## Project Structure

```
live_interview_agent/
├── src/                    # React UI (TypeScript)
│   └── ui/
│       ├── hooks/          # useWebSocket.ts, useVADFilter.ts
│       ├── components/     # SessionControls, ProviderSettings, etc.
│       └── store/          # sessionStore.ts
├── src-tauri/             # Tauri backend (Rust)
│   └── src/
│       ├── commands/       # config.rs (Multi-key support)
│       └── utils/          # keyring.rs
├── sidecar/               # Python sidecar
│   └── src/
│       ├── server.py       # WebSocket server
│       ├── warmup.py       # Model pre-warming
│       ├── providers/      # AI Provider implementations
│       │   ├── stt/        # Groq, Deepgram, OpenAI, Gemini
│       │   ├── llm/        # OpenAI, Anthropic, Gemini
│       │   └── factory.py  # Provider instantiation logic
│       ├── audio/          # capture.py, vad.py
│       └── rag/            # engine.py
└── _prism/                # SDLC artifacts
```

## IPC Protocol (WebSocket)

Port: `localhost:8765`

### Client → Server Messages
```json
{
  "type": "START_SESSION",
  "data": {
    "apiKeys": { "gemini": "...", "groq": "...", "openai": "..." },
    "preferences": { "sttProvider": "groq", "llmProvider": "openai" }
  }
}
```

### Server → Client Messages
```json
{"type": "TRANSCRIPTION", "speaker": "Interviewer", "text": "..."}
{"type": "ANSWER_CHUNK", "chunk": "...", "complete": false}
```

## Prism SDLC

This project uses the Prism SDLC framework.

| Phase | Command | Status |
|-------|---------|--------|
| Planning | `/prism-plan` | Complete (Phase 1 + 2) |
| Solution | `/prism-solution` | Complete (Phase 1 + 2) |
| Implementation | `/prism-implement` | Complete (33/33) |
| Verification | `/prism-verify` | Ready for Manual |

### Key Documents
- Phase 2 PRD: `_prism/planning/prd-phase2.md`
- Phase 2 Architecture: `_prism/architecture/architecture-phase2.md`
- Verification Report: `_prism/verification/e2e_report.md`
