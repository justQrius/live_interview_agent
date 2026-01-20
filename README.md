# Live Interview Agent

A cross-platform desktop application that provides real-time AI assistance during job interviews. Built with a sidecar architecture combining **Tauri (Rust)** for the desktop shell, **React (TypeScript)** for the UI, and a **Python AI engine** for real-time speech-to-text, RAG-powered answers, and intelligent coaching.

![Phase Status](https://img.shields.io/badge/Phase-9%20Complete-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

### 🎙️ Real-Time Speech Processing
- **Multi-Provider STT**: Local Whisper (GPU-accelerated, 100% private) with Gemini cloud fallback
- **Streaming Transcription**: Deepgram Nova-3 WebSocket for ~150ms latency interim results
- **Speaker Diarization**: Distinguishes interviewer from candidate via voice calibration
- **Noise Reduction**: Adaptive filtering for clear audio in noisy environments

### 🧠 Intelligence Pipeline
- **Question Detection**: 3-tier classification (Regex → Context → LLM) with <10ms typical latency
- **Multi-Turn Context**: TopicStack tracks conversation across turns, resolving "that project" or "go back to the first topic"
- **Compound Question Splitting**: "Tell me about X and also Y" → separate RAG queries for comprehensive answers
- **Utterance Accumulation**: 4-tier completeness detection handles natural speech pauses ("Tell me about... [pause] ...and how you handled it")

### 📚 RAG & Context Management
- **Hierarchical Chunking**: Parent (4096 chars) + child (1024 chars) chunks for precision + context
- **Document-Aware Priority**: SAMPLE_QA → RESUME → JOB_DESCRIPTION → COMPANY_INFO
- **QA-Atomic Chunking**: Prepared Q&A pairs never split across chunks
- **Gemini Context Caching**: 2-hour TTL cache reduces latency and cost for long sessions
- **Document Persistence**: Uploaded documents survive app restarts

### 🎯 Interview Coaching
- **STAR Story Bank**: Automatic extraction of 8-12 achievement stories from your resume
- **Real-Time Story Recall**: Relevant stories surface within 1 second of behavioral questions
- **Answer Frameworks**: Suggests STAR, SOAR, PREP, CAR based on question type
- **Consistency Tracking**: Alerts if you contradict previous answers (e.g., "5 years" vs "3 years")
- **Candidate Profile**: ~1000-token identity injected into every LLM prompt

### ⚡ Low-Latency Architecture
- **End-to-End Target**: <1.5 seconds from speech end to first answer token
- **Model Pre-Warming**: VAD, speaker ID, and Whisper load at app startup
- **Hybrid Endpointing**: Semantic detection (when available) bypasses timing buffers
- **Parallel Processing**: Coaching runs alongside answer generation

### 🔒 Privacy & Security
- **Local-First STT**: Default to on-device Whisper (no audio leaves your machine)
- **Secure Key Storage**: API keys stored in OS keychain (Windows Credential Manager, macOS Keychain)
- **Session Isolation**: Conversation history cleared on stop; documents optionally preserved

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
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         External Services                               │
│  Gemini (STT/LLM/Cache) │ OpenAI (GPT-5) │ Anthropic │ Deepgram │ Local│
└─────────────────────────────────────────────────────────────────────────┘
```

For detailed architecture documentation, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Node.js** | 20+ | Frontend build |
| **Rust** | 1.75+ | Tauri backend |
| **Python** | 3.11+ | AI sidecar |
| **CUDA** | 12.x | Optional, for local Whisper GPU acceleration |

**OS-Specific Build Tools:**
- **Windows**: Visual Studio C++ Build Tools
- **macOS**: Xcode Command Line Tools
- **Linux**: `build-essential`, `libwebkit2gtk-4.0-dev`, `libssl-dev`

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/live_interview_agent.git
cd live_interview_agent

# Install frontend dependencies
npm install

# Setup Python sidecar
cd sidecar
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# For NVIDIA GPU acceleration (recommended):
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

cd ..
```

### Running the Application

**Development Mode** (two terminals):

```bash
# Terminal 1: Start Python sidecar
cd sidecar
# Activate venv first
python -m src.server

# Terminal 2: Start Tauri app
npm run tauri dev
```

**Production Build:**

```bash
npm run tauri build
```

---

## Configuration

1. Launch the app and click the **Settings** icon
2. Enter API keys for your preferred providers:

| Provider | Purpose | Required |
|----------|---------|----------|
| **Gemini** | STT, LLM, embeddings, context caching | Recommended |
| **OpenAI** | LLM (GPT-5/4o) | Optional |
| **Anthropic** | LLM (Claude 4/3.5) | Optional |
| **Deepgram** | Streaming STT | Optional |

3. **STT** defaults to **Local Whisper** (GPU). Enable Deepgram in Settings for streaming mode.
4. Keys are stored securely in your OS keychain.

### Provider Fallback Chain

| Category | Primary | Fallback |
|----------|---------|----------|
| **STT** | Local Whisper (GPU) | Gemini (Cloud) |
| **LLM** | Gemini (cached context) | OpenAI → Anthropic |
| **Streaming** | Deepgram Nova-3 | Disabled (batch mode) |

---

## Usage

### Basic Workflow

1. **Upload Context**: Add your resume, job description, and prepared Q&A
2. **Calibrate Voice**: Record a short sample so the system recognizes you vs. the interviewer
3. **Start Session**: Begin the interview coaching session
4. **Interview**: The system automatically detects interviewer questions and generates contextual answers
5. **Coaching**: Watch for story suggestions, structure hints, and consistency warnings

### Document Types

| Type | Priority | Purpose |
|------|----------|---------|
| `SAMPLE_QA` | Highest | Your prepared answers (used first) |
| `RESUME` | High | Hard facts, dates, metrics |
| `JOB_DESCRIPTION` | Medium | Role requirements for tailoring |
| `COMPANY_INFO` | Medium | For "Why us?" questions |
| `INTERVIEWER_INFO` | Low | Background on the interviewer |

### Answer Enhancement

After an answer is generated, click **Enhance** to:
- **Add Detail**: Re-query RAG for more context
- **Make Specific**: Add metrics and concrete examples
- **Suggest STAR**: Link to a relevant achievement story
- **Adjust Tone**: Rewrite with different confidence level
- **Shorten**: Compress to key points

---

## Project Structure

```
live_interview_agent/
├── src/                    # React Frontend
│   └── ui/
│       ├── components/     # UI components
│       ├── hooks/          # useWebSocket, useVAD
│       └── store/          # Zustand sessionStore
├── src-tauri/              # Tauri Backend (Rust)
│   └── src/
│       ├── commands/       # sidecar, config
│       └── utils/          # keyring
├── sidecar/                # Python AI Engine
│   └── src/
│       ├── server.py       # WebSocket server
│       ├── audio/          # capture, vad, diarization
│       ├── providers/      # stt/, llm/, factory
│       ├── classification/ # detector, reformulator, splitter
│       ├── rag/            # engine, store, embeddings
│       ├── context/        # manager, chunker, gemini_cache
│       ├── memory/         # SQLite store, models
│       ├── coaching/       # story recall, structure, consistency
│       ├── extraction/     # document processing pipeline
│       └── evaluation/     # groundedness scoring
├── ARCHITECTURE.md         # Detailed system architecture
├── AGENTS.md               # AI agent development guide
└── README.md               # This file
```

---

## Development

### Testing

```bash
# Frontend tests
npm run test

# Rust tests
cd src-tauri && cargo test

# Python sidecar tests
cd sidecar && pytest

# Specific test suites
pytest tests/test_question_detector.py      # Intelligence pipeline
pytest tests/test_memory_store.py           # Persistence
pytest tests/test_streaming_stt.py          # Streaming transcription
pytest tests/test_evaluation.py             # Groundedness evaluation

# Latency benchmark
python scripts/benchmark_latency.py
```

### Environment Variables

```bash
# Streaming STT
STREAMING_STT_PROVIDER=deepgram           # deepgram, disabled

# Utterance Accumulation
ACCUMULATOR_ENABLED=true
ACCUMULATOR_ENDPOINTING_MODE=hybrid       # timing, streaming, hybrid

# Local Whisper
WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_DEVICE=cuda

# Evaluation
GROUNDEDNESS_EVALUATION_ENABLED=true
```

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | MVP Foundation | ✅ Complete |
| Phase 2 | Multi-Provider & Optimization | ✅ Complete |
| Phase 3 | Intelligence Pipeline | ✅ Complete |
| Phase 4 | Interview Coach Evolution | ✅ Complete |
| Phase 5 | Gemini Integration | ✅ Complete |
| Phase 6 | Utterance Accumulation | ✅ Complete |
| Phase 7 | Streaming STT & Semantic Endpointing | ✅ Complete |
| Phase 8 | RAG Persistence | ✅ Complete |
| Phase 9 | Answer Quality & Grounding | ✅ Complete |

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| End-to-end latency | <1.5s | ~1.2s |
| Question detection | <10ms | ~5ms |
| RAG retrieval | <200ms | ~150ms |
| First LLM token | <500ms | ~400ms (cached) |
| Story recall | <1s | ~300ms |

---

## Contributing

See [AGENTS.md](AGENTS.md) for AI-assisted development guidelines.

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Tauri](https://tauri.app/) - Desktop framework
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Local STT
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice activity detection
- [ChromaDB](https://www.trychroma.com/) - Vector store
- [Zustand](https://github.com/pmndrs/zustand) - State management
