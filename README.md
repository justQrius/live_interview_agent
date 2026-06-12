# Live Interview Agent & Meeting Copilot

> **One app, two modes.** A cross-platform desktop assistant that listens to a live conversation — job interview, sales call, standup, customer discovery, 1:1 — and quietly drafts the right answer on your screen, drawn from your own documents, stories, and notes.

Live Interview Agent captures the audio of the conversation (your microphone and the *other* side's audio via system loopback), transcribes it in real time, detects when you're being asked a question, and produces a grounded, in-context answer before you've finished formulating your own. The same pipeline that coaches you through "tell me about a time you handled conflict" can also keep a sales call on track, take running notes for a 1:1, or pre-draft answers for a panel interview.

Built with a sidecar architecture combining **Tauri (Rust)** for the desktop shell, **React (TypeScript)** for the UI, and a **Python AI engine** for real-time speech-to-text, RAG-powered answers, and intelligent coaching.

![Phase Status](https://img.shields.io/badge/Phase-10%20Complete-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Table of Contents

- [What it does](#what-it-does)
- [Use cases](#use-cases)
- [How it works](#how-it-works)
- [Features](#features)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project structure](#project-structure)
- [Development](#development)
- [Roadmap status](#roadmap-status)
- [Performance](#performance)
- [Privacy](#privacy)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [License](#license)

---

## What it does

You put the app on a second monitor (or just leave it open). It listens to:

1. **Your microphone** — so it knows when you're answering (and can stay quiet).
2. **System audio (loopback)** — so it hears the other side of the call on Zoom, Teams, Google Meet, or any browser-based interview platform.

When the other person asks you a question:

1. The app transcribes what they said (locally, by default — no audio leaves your machine).
2. A 4-tier completeness detector waits for the *whole* question, including natural pauses like "tell me about… [pause] …and how you handled it."
3. A RAG pipeline pulls relevant material from documents you've uploaded — your resume, prepared Q&A, the job description, company research, your own meeting notes.
4. An LLM drafts an answer grounded in that material, streamed to the UI in real time.
5. Optional coaching panels pop up with STAR stories, structure hints (STAR / SOAR / PREP / CAR), and consistency warnings.

The target end-to-end latency is **<1.5 seconds** from the end of the question to the first answer token on screen — fast enough that the answer is waiting for you, not the other way around.

---

## Use cases

The pipeline is general; the prompts and document types are configurable. Today the app is tuned for these scenarios:

| Scenario | How it helps |
|---|---|
| **Job interviews** | Real-time answer drafts, STAR story recall, consistency tracking, tone adjustment |
| **Behavioral & technical screens** | Splits compound questions, resolves "tell me more about that project" anaphora across turns |
| **Panel interviews** | Multi-question splitting, QA prioritization, document-aware retrieval |
| **Sales / discovery calls** | Live answer drafts from your playbook, talking points, objection handling |
| **1:1s & standups** | Captures both sides, surfaces relevant context from past notes or docs |
| **Customer / vendor calls** | Keeps your talking points in front of you without breaking eye contact |
| **Live meeting assistant** | Same pipeline with meeting-mode prompts; transcribe both sides while you stay focused on the conversation |

> The app is interview-mode by default because the coaching layer is most mature there, but nothing in the architecture is interview-specific — the question detector, RAG, and answer-generation stages work the same way regardless of what the *other* person is asking.

---

## How it works

```
┌──────────────────┐                          ┌──────────────────┐
│  Other person    │──► System audio ──┐      │   You            │
│  (Zoom / Meet /  │   (WASAPI /        │      │                  │
│   Teams / phone) │    Core Audio)     │      │   Microphone ────┼──►
└──────────────────┘                    │      └──────────────────┘
                                        ▼              │
                                ┌──────────────────────────┐
                                │  VAD + Speaker ID         │
                                │  (Silero VAD, ECAPA-TDNN) │
                                └──────────────┬───────────┘
                                               │  speech segments
                                               ▼
                                ┌──────────────────────────┐
                                │  STT (Local Whisper /     │
                                │  Deepgram streaming /     │
                                │  Gemini fallback)         │
                                └──────────────┬───────────┘
                                               │  text
                                               ▼
                                ┌──────────────────────────┐
                                │  Utterance Accumulator   │
                                │  (4-tier completeness +  │
                                │   LiveKit semantic EOT)   │
                                └──────────────┬───────────┘
                                               │  finalized question
                                               ▼
   ┌────────────────────┐   ┌──────────────────────────┐   ┌────────────────────┐
   │  RAG retrieval     │──►│  LLM (Gemini / OpenAI /  │──►│  Streamed answer   │
   │  ChromaDB + Gemini │   │  Anthropic, cached)      │   │  to UI             │
   │  context cache     │   │  + coaching overlays     │   │  + STAR story      │
   └────────────────────┘   └──────────────────────────┘   └────────────────────┘
                ▲                            ▲
                │                            │
        ┌───────┴────────┐          ┌────────┴────────┐
        │  Your docs     │          │  Your profile   │
        │  (resume, JD,  │          │  (STAR bank,    │
        │   notes, Q&A)  │          │   candidate     │
        │                │          │   identity)     │
        └────────────────┘          └─────────────────┘
```

For the full system architecture, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Features

### 🎙️ Real-time audio capture
- **System loopback + microphone** — hears the *other* side on any video-call platform, not just your mic
- **Multi-provider STT** — local Whisper (GPU-accelerated, 100% private) with Gemini cloud fallback
- **Streaming transcription** — Deepgram Nova-3 WebSocket for ~150ms interim latency
- **Speaker diarization** — ECAPA-TDNN voice embeddings distinguish "you" from "them" via a 10-second voice calibration
- **Noise reduction** — adaptive filtering for calls in noisy environments
- **Browser VAD** — Silero VAD in the UI thread for low-latency turn detection

### 🧠 Intelligence pipeline
- **Question detection** — 3-tier classification (Regex → Context → LLM) at <10ms typical latency
- **Compound question splitting** — "Tell me about X and also Y" → two parallel RAG queries
- **Multi-turn anaphora** — TopicStack tracks conversation across N turns, resolving "that project" or "go back to the first topic"
- **4-tier utterance accumulation** — punctuation → syntax → timing → LLM semantic check; handles natural mid-thought pauses
- **Hybrid endpointing** — LiveKit semantic turn detection (~25ms) takes priority over Deepgram acoustic signals (~100ms)

### 📚 RAG and context
- **Hierarchical chunking** — parent (2048 chars) + child (512 chars) chunks for precision + context
- **Document-aware priority** — `SAMPLE_QA` → `RESUME` → `JOB_DESCRIPTION` → `COMPANY_INFO` → `INTERVIEWER_INFO`
- **QA-atomic chunking** — prepared Q&A pairs are never split mid-answer
- **Gemini context caching** — 2-hour TTL reduces latency and cost for long sessions
- **Document persistence** — uploaded documents survive app restarts; selective deletion supported
- **Web search grounding** — Gemini's grounding or DuckDuckGo for fresh company / interviewer research
- **RAG manifest** — inspect and audit exactly which document chunks fed each answer

### 🎯 Live coaching
- **STAR story bank** — automatic extraction of 8–12 achievement stories from your resume at upload time
- **Real-time story recall** — relevant stories surface within ~300ms of behavioral questions
- **Answer frameworks** — suggests STAR, SOAR, PREP, or CAR based on detected question type
- **Consistency tracking** — flags contradictions across your answers ("5 years" vs "3 years")
- **Candidate profile injection** — a ~1000-token identity summary is included in every LLM prompt
- **Preparation mode** — pre-session summary of your own materials and likely questions

### ✨ Answer quality and control
- **Streaming answer chunks** — answers appear token-by-token, not all at once
- **5 enhancement modes** — *Add Detail*, *Make Specific*, *Suggest STAR*, *Adjust Tone*, *Shorten*
- **Barge-in support** — pause answer generation when you start speaking
- **Groundedness evaluation** — Phase 9 scoring verifies every answer is anchored in your documents
- **Session history** — browse, replay, and export past sessions

### 🔒 Privacy and security
- **Local-first STT** — default to on-device Whisper; audio never leaves your machine unless you opt in to a cloud provider
- **OS keychain** — API keys stored in Windows Credential Manager, macOS Keychain, or Linux Secret Service
- **Session isolation** — conversation history cleared on stop; documents optionally preserved
- **No telemetry** — the app makes no outbound calls except to providers you explicitly configure

### ⚡ Low-latency architecture
- **Target**: <1.5s from speech end to first answer token (currently ~1.2s)
- **Model pre-warming** — VAD, speaker ID, and Whisper loaded at app startup, not on first question
- **Speculative retrieval** — RAG begins retrieving before the question is fully finalized
- **Parallel coaching** — story recall and structure suggestion run alongside answer generation
- **Context caching** — long conversation context stays in the LLM's cache to avoid re-tokenization

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Tauri Desktop Shell                           │
│  (Window management, OS integration, secure keyring, sidecar lifecycle) │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ IPC
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         React UI (TypeScript)                           │
│  (Zustand state, WebSocket client, coaching panels, answer display)     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ WebSocket (localhost:8765)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Python Sidecar (asyncio)                           │
│                                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  Audio  │ │   STT   │ │   RAG   │ │   LLM   │ │Coaching │          │
│  │ Capture │ │Provider │ │ Engine  │ │Provider │ │ Engine  │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  VAD    │ │Question │ │ Memory  │ │Extract  │ │  Eval   │          │
│  │(Silero) │ │Detector │ │ Store   │ │Pipeline │ │(Ground) │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐                    │
│  │ LiveKit Turn Det.    │  │ Search / Grounding   │                    │
│  │ (semantic endpointing)│ │ (Gemini / DuckDuckGo) │                    │
│  └──────────────────────┘  └──────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         External Services (opt-in)                      │
│  Gemini (STT/LLM/Cache/Search) │ OpenAI (GPT-5) │ Anthropic │ Deepgram │
└─────────────────────────────────────────────────────────────────────────┘
```

For component-level detail, data flow, and extension points, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Getting started

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Node.js** | 20+ | Frontend build |
| **Rust** | 1.77+ | Tauri backend |
| **Python** | 3.11+ | AI sidecar |
| **CUDA** | 12.x | Optional, for local Whisper GPU acceleration |

**OS-specific build tools:**
- **Windows** — Visual Studio C++ Build Tools
- **macOS** — Xcode Command Line Tools
- **Linux** — `build-essential`, `libwebkit2gtk-4.0-dev`, `libssl-dev`

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/justQrius/live_interview_agent.git
cd live_interview_agent

# 2. Install frontend dependencies
npm install

# 3. Set up the Python sidecar
cd sidecar
python -m venv venv

# Activate the virtual environment
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate

pip install -r requirements.txt

# Optional: NVIDIA GPU acceleration for local Whisper
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

cd ..
```

### Running the application

**Development mode** (two terminals):

```bash
# Terminal 1 — start the Python sidecar
cd sidecar
# (activate venv first)
python -m src.server

# Terminal 2 — start the Tauri app
npm run tauri dev
```

**Production build:**

```bash
npm run tauri build
```

The bundled installer will land in `src-tauri/target/release/bundle/`.

---

## Configuration

1. Launch the app and click the **Settings** icon.
2. Enter API keys for any providers you want to use:

| Provider | Purpose | Required? |
|---|---|---|
| **Gemini** | STT, LLM, embeddings, context caching, web search | Recommended |
| **OpenAI** | LLM (GPT-5 / 4o) | Optional |
| **Anthropic** | LLM (Claude 4 / 3.5) | Optional |
| **Deepgram** | Streaming STT | Optional |

3. **STT** defaults to **Local Whisper** (on-device, GPU if available). Enable Deepgram in Settings for ~150ms streaming mode.
4. API keys are stored in your **OS keychain** — never in plaintext config files.

### Provider fallback chain

| Category | Primary | Fallback |
|---|---|---|
| **STT** | Local Whisper (GPU) | Gemini (cloud) |
| **Streaming STT** | Deepgram Nova-3 | Batch mode (disabled streaming) |
| **LLM** | Gemini (cached context) | OpenAI → Anthropic |
| **Turn detection** | LiveKit semantic | Silero VAD timing |
| **Search** | Gemini grounding | DuckDuckGo |

### Environment variables

```bash
# Streaming STT
STREAMING_STT_PROVIDER=deepgram                # deepgram, disabled

# Utterance Accumulation
ACCUMULATOR_ENABLED=true
ACCUMULATOR_ENDPOINTING_MODE=hybrid            # timing, streaming, hybrid
ACCUMULATOR_MERGE_GAP_MS=500
ACCUMULATOR_SOFT_TIMEOUT_MS=2000
ACCUMULATOR_HARD_TIMEOUT_MS=5000
ACCUMULATOR_MAX_CHARACTERS=2000
ACCUMULATOR_USE_LLM_FALLBACK=true

# Local Whisper
WHISPER_MODEL_SIZE=large-v3-turbo              # large-v3-turbo, distil-large-v3, medium, small
WHISPER_DEVICE=cuda                            # cuda, cpu

# Answer quality
GROUNDEDNESS_EVALUATION_ENABLED=true
```

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the complete list and defaults.

---

## Usage

### Basic workflow

1. **Upload context** — Add your resume, job description, prepared Q&A, company research, or any documents you want the app to draw from. The extraction pipeline automatically identifies STAR stories and builds a candidate profile.
2. **Calibrate your voice** — Record a 10-second sample so the system can distinguish you from the other speakers. (Only needed once per device.)
3. **Start a session** — Open the app, then open Zoom / Teams / Meet / your phone. The app captures the conversation from both sides.
4. **Have the conversation** — The app transcribes the other person, detects when a question is complete, and drafts a grounded answer in real time.
5. **Use coaching** — Watch for STAR story suggestions, structure hints, and consistency warnings as you go.
6. **Enhance or export** — Use the *Enhance* menu to re-draft an answer (more detail, more specific, STAR format, different tone, shorter). Export the full session transcript when you're done.

### Document types

| Type | Priority | Used for |
|---|---|---|
| `SAMPLE_QA` | Highest | Your prepared answers (retrieved first) |
| `RESUME` | High | Hard facts, dates, metrics |
| `JOB_DESCRIPTION` | Medium | Role requirements, tailoring |
| `COMPANY_INFO` | Medium | "Why us?" questions |
| `INTERVIEWER_INFO` | Low | Background on the other person |
| **Custom** | Configurable | Meeting notes, playbooks, briefs, anything |

### Answer enhancement

After an answer is generated, click **Enhance** to re-draft it:

- **Add Detail** — re-query RAG with a higher limit, pull in more context
- **Make Specific** — add metrics and concrete examples
- **Suggest STAR** — link the answer to a relevant achievement story
- **Adjust Tone** — rewrite with a different confidence level
- **Shorten** — compress to the essential points

---

## Project structure

```
live_interview_agent/
├── src/                      # React frontend (TypeScript)
│   └── ui/
│       ├── components/       # 25+ components (AnswerDisplay, CoachingPanel, …)
│       ├── hooks/            # useWebSocket, useVAD
│       └── store/            # Zustand sessionStore
├── src-tauri/                # Tauri desktop shell (Rust)
│   └── src/
│       ├── commands/         # sidecar, config, window
│       └── utils/            # keyring, platform, storage
├── sidecar/                  # Python AI engine
│   └── src/
│       ├── server.py         # WebSocket IPC server
│       ├── warmup.py         # Model pre-warming
│       ├── protocol.py       # Message types
│       ├── audio/            # capture, VAD, diarization, noise reduction
│       ├── classification/   # question detector, reformulator, splitter, accumulator
│       ├── coaching/         # story recall, structure suggester, consistency tracker
│       ├── context/          # manager, chunker, gemini cache, file uploader
│       ├── extraction/       # pipeline, fact/story/profile extractors
│       ├── evaluation/       # groundedness scoring
│       ├── livekit_integration/  # semantic turn detection (Phase 10)
│       ├── memory/           # SQLite store, models
│       ├── providers/        # STT, LLM, search providers + factory
│       ├── rag/              # engine, enhanced engine, embeddings, retrieval
│       └── storage/          # session store, exporter, RAG manifest
├── scripts/                  # Build & installer scripts
├── ARCHITECTURE.md           # Detailed system architecture
├── CONTRIBUTING.md           # Contribution guide
├── SECURITY.md               # Vulnerability reporting
└── README.md                 # This file
```

---

## Development

### Running tests

```bash
# Frontend (Vitest)
npm run test

# Rust
cd src-tauri && cargo test

# Python sidecar (66 test files)
cd sidecar && pytest

# Targeted suites
pytest tests/test_question_detector.py        # Intelligence pipeline
pytest tests/test_query_reformulator.py       # Multi-turn anaphora
pytest tests/test_utterance_accumulation.py   # 4-tier completeness
pytest tests/test_streaming_stt.py            # Deepgram / LiveKit
pytest tests/test_memory_store.py             # Persistence
pytest tests/test_extraction_pipeline.py      # STAR story extraction
pytest tests/test_coaching.py                 # Story recall, consistency
pytest tests/test_evaluation.py               # Groundedness
```

### Latency benchmarks

```bash
# End-to-end latency (requires running server)
cd sidecar && python scripts/benchmark_latency.py

# LiveKit turn detection specifically
python scripts/benchmark_livekit_turn_detection.py

# Replay-based integration tests
python scripts/test_with_recordings.py
```

### Code style

- **TypeScript / React** — functional components, hooks, Zustand, Tailwind, named exports, strict mode
- **Rust** — Tauri commands in `src-tauri/src/commands/`, platform-specific code in `utils/platform.rs`, all errors as `Result<T, String>`
- **Python** — 3.11+ type hints, async/await, Black + isort, `Provider` and `Factory` patterns, always `from src.…` import prefix
- **Provider Pattern** — implement `STTProvider` / `LLMProvider` / `SearchProvider` for new services
- **Factory Pattern** — use `ProviderFactory` for instantiation so config and fallback work uniformly

### Testing guidelines

- All tests must pass before opening a PR
- TDD preferred: write the failing test first
- Coverage targets: **Python >80%** for core modules, **TypeScript >70%** for components, **Rust unit tests** for every command

---

## Roadmap status

| Phase | Description | Status |
|---|---|---|
| Phase 1 | MVP Foundation | ✅ Complete |
| Phase 2 | Multi-Provider & Optimization | ✅ Complete |
| Phase 3 | Intelligence Pipeline (question detection, reformulation) | ✅ Complete |
| Phase 4 | Interview Coach Evolution (memory, stories, consistency) | ✅ Complete |
| Phase 5 | Gemini Integration (caching, grounding, file uploader) | ✅ Complete |
| Phase 6 | Utterance Accumulation (4-tier completeness) | ✅ Complete |
| Phase 7 | Streaming STT & Semantic Endpointing | ✅ Complete |
| Phase 8 | RAG Persistence (manifest, selective deletion) | ✅ Complete |
| Phase 9 | Answer Quality & Grounding Evaluation | ✅ Complete |
| Phase 10 | LiveKit Turn Detection Production Readiness | ✅ Complete |

---

## Performance

| Metric | Target | Typical (measured) |
|---|---|---|
| End-to-end latency (speech end → first answer token) | <1.5s | ~1.2s |
| Question detection | <10ms | ~5ms |
| RAG retrieval | <200ms | ~150ms |
| First LLM token (with Gemini context cache) | <500ms | ~400ms |
| STAR story recall | <1s | ~300ms |
| Deepgram streaming interim | — | ~150ms |
| LiveKit semantic turn detection | — | ~25ms |

---

## Privacy

Live Interview Agent is designed to keep your data local by default:

- **Audio** stays on your machine when using Local Whisper (the default). You only opt in to cloud STT if you want lower latency on a machine without a GPU.
- **Documents** you upload are stored in the local app data directory. Nothing is uploaded to any server unless you choose a cloud LLM provider, in which case only the relevant chunks (not your full library) are sent per query.
- **API keys** live in the OS keychain — never in config files or environment variables that get committed.
- **Conversation history** is cleared when you stop a session. You can opt in to persistence and export anytime.
- **No telemetry.** The app makes no outbound calls except to the providers you explicitly configure.

If you need a stricter setup (fully air-gapped, on-prem LLMs), the provider factory makes it straightforward to swap in local model servers.

---

## Contributing

Bug reports, feature requests, and pull requests are all welcome. Please see **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide — it covers development setup, the provider / factory extension patterns, testing requirements, and the style guide for TypeScript, Rust, and Python.

For security issues, see **[SECURITY.md](SECURITY.md)** — please do **not** open a public GitHub Issue for vulnerability reports.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Tauri](https://tauri.app/) — desktop framework
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — local STT
- [Silero VAD](https://github.com/snakers4/silero-vad) — voice activity detection
- [SpeechBrain](https://speechbrain.github.io/) — ECAPA-TDNN speaker embeddings
- [ChromaDB](https://www.trychroma.com/) — vector store
- [Zustand](https://github.com/pmndrs/zustand) — React state management
- [LiveKit Agents](https://github.com/livekit/agents) — semantic turn detection
- [Deepgram](https://deepgram.com/) — streaming STT
