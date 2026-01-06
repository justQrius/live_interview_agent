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
```

## Code Style

### TypeScript/React
- Functional components with hooks
- Zustand for state management (not Redux)
- Tailwind CSS for styling (no CSS modules)
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
- One module per concern (audio, stt, rag, llm)
- Docstrings for public functions
- Black formatter, isort for imports

## Testing Instructions

- All tests must pass before committing
- Use TDD: write failing test first, then implement
- Test coverage targets:
  - Python: >80% for core modules (audio, stt, rag, llm)
  - TypeScript: >70% for components
  - Rust: Unit tests for all commands

## Architecture Overview

```
┌─────────────────────┐    WebSocket    ┌─────────────────────┐
│  Tauri (Rust + UI)  │◄───────────────►│   Python Sidecar    │
│  - React frontend   │  localhost:8765 │  - Audio capture    │
│  - Window manager   │                 │  - Silero VAD       │
│  - Keyring (API key)│                 │  - Gemini STT/LLM   │
└─────────────────────┘                 │  - ChromaDB RAG     │
                                        └─────────────────────┘
```

## Project Structure

```
live_interview_agent/
├── src/                    # React UI (TypeScript)
│   └── ui/
│       ├── App.tsx
│       ├── components/     # SessionControls, AnswerDisplay, etc.
│       ├── store/          # Zustand sessionStore.ts
│       └── hooks/          # useWebSocket.ts
├── src-tauri/             # Tauri backend (Rust)
│   └── src/
│       ├── main.rs
│       ├── commands/       # config.rs, window.rs, sidecar.rs
│       └── utils/          # keyring.rs, platform.rs
├── sidecar/               # Python sidecar
│   └── src/
│       ├── server.py       # WebSocket server
│       ├── audio/          # capture.py, vad.py, diarization.py
│       ├── stt/            # gemini_stt.py
│       ├── context/        # manager.py
│       ├── rag/            # engine.py
│       └── llm/            # gemini_llm.py
└── _prism/                # SDLC artifacts
```

## IPC Protocol (WebSocket)

Port: `localhost:8765`

### Client → Server Messages
```json
{"type": "START_SESSION", "apiKey": "..."}
{"type": "STOP_SESSION"}
{"type": "UPLOAD_CONTEXT", "files": [...]}
{"type": "CALIBRATE_VOICE", "audioData": "base64..."}
{"type": "MANUAL_QUESTION", "question": "..."}
```

### Server → Client Messages
```json
{"type": "TRANSCRIPTION", "speaker": "Interviewer", "text": "..."}
{"type": "ANSWER_CHUNK", "chunk": "...", "complete": false}
{"type": "ANSWER_CHUNK", "chunk": "...", "complete": true, "confidence": "high"}
{"type": "ERROR", "message": "..."}
{"type": "STATUS", "state": "listening|processing|idle"}
```

## Key Dependencies

### Frontend (package.json)
- `react`: ^18.3.0
- `typescript`: ^5.3.0
- `@tauri-apps/api`: ^1.5.0
- `zustand`: ^4.5.0
- `tailwindcss`: ^3.4.0

### Rust (Cargo.toml)
- `tauri`: 1.5+
- `keyring`: 2.2+
- `tokio`: 1.35+

### Python (requirements.txt)
- `websockets`: >=12.0
- `google-generativeai`: >=0.3.2
- `chromadb`: >=0.4.22
- `silero-vad`: >=4.0
- `speechbrain`: (for ECAPA-TDNN)
- `pyaudiowpatch`: >=0.2.12 (Windows)
- `sounddevice`: >=0.4.6 (macOS/Linux)
- `pypdf`: >=3.17
- `python-docx`: >=1.1.0

## Don't Do This

- **Don't embed Python in Rust via PyO3** - Use sidecar pattern
- **Don't use Electron** - Tauri is lighter and faster
- **Don't log transcripts/answers to disk** - Privacy requirement
- **Don't skip voice calibration** - Diarization accuracy drops significantly
- **Don't expose WebSocket to network** - localhost only (127.0.0.1)
- **Don't store API keys in plaintext** - Use OS keychain
- **Don't use Redux** - Zustand is simpler for this use case
- **Don't use CSS modules** - Tailwind CSS only

## NFR Targets

| Requirement | Target |
|-------------|--------|
| End-to-end latency | <5 seconds (P95) |
| RAM usage | <500MB |
| CPU (idle) | <10% |
| CPU (active) | <30% |
| Session stability | 2 hours, zero crashes |
| Setup time | <5 minutes |
| STT accuracy | >90% WER (clear English) |
| Diarization accuracy | >85% |

## Prism SDLC

This project uses the Prism SDLC framework.

| Phase | Command | Status |
|-------|---------|--------|
| Planning | `/prism-plan` | Complete |
| Solution | `/prism-solution` | Complete |
| Implementation | `/prism-implement` | In Progress (10/20) |
| Verification | `/prism-verify` | Pending |

### Key Documents
- PRD: `_prism/planning/prd.md`
- Architecture: `_prism/architecture/architecture.md`
- Tasks: `_prism/tasks.md`

### Next Step
Run `/prism-implement STORY-011` to build the RAG Engine.
