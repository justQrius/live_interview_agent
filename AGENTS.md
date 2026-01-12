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
python -m src.server
```

### Run Tests
```bash
# React UI tests
npm run test

# Rust tests
cd src-tauri && cargo test

# Python tests
cd sidecar && pytest

# Phase 3 Classification tests
cd sidecar && pytest tests/test_question_detector.py tests/test_query_reformulator.py tests/test_question_splitter.py

# Phase 4 Memory & Extraction tests
cd sidecar && pytest tests/test_memory_store.py tests/test_extraction_pipeline.py tests/test_coaching.py

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
- **Import Convention**: Always use `src.` prefix (e.g., `from src.audio.vad import VADProcessor`)
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
┌─────────────────────┐    WebSocket    ┌─────────────────────────────────────┐
│  Tauri (Rust + UI)  │◄───────────────►│         Python Sidecar              │
│  - React frontend   │  localhost:8765 │  - Provider Factory (STT/LLM)       │
│  - Browser VAD      │                 │  - Enhanced RAG Engine              │
│  - Keyring (Keys)   │                 │  - Memory Store (SQLite)            │
│  - Coaching UI      │                 │  - Extraction Pipeline              │
└─────────────────────┘                 │  - Coaching Engine                  │
                                        │  - Gemini Cache & Grounding         │
                                        └─────────────────────────────────────┘
```

## Project Structure

```
live_interview_agent/
├── src/                    # React UI (TypeScript)
│   └── ui/
│       ├── hooks/          # useWebSocket.ts, useVADFilter.ts
│       ├── components/     
│       │   ├── AnswerDisplay.tsx
│       │   ├── CoachingPanel.tsx         # Phase 4: Coaching container
│       │   ├── ConsistencyPanel.tsx      # Phase 4: Claim tracking
│       │   ├── DocumentTypeSelector.tsx
│       │   ├── PreparationButton.tsx
│       │   ├── PreparationSummary.tsx
│       │   ├── StorySuggestionCard.tsx   # Phase 4: STAR story recall
│       │   ├── StructureHintCard.tsx     # Phase 4: Answer frameworks
│       │   └── ...
│       └── store/          # sessionStore.ts
├── src-tauri/             # Tauri backend (Rust)
│   └── src/
│       ├── commands/       # config.rs (Multi-key support)
│       └── utils/          # keyring.rs
├── sidecar/               # Python sidecar
│   └── src/
│       ├── server.py       # WebSocket server
│       ├── warmup.py       # Model pre-warming
│       ├── protocol.py     # IPC message definitions
│       ├── audio/          # capture.py, vad.py, diarization.py, noise_reduction.py
│       ├── classification/ # question_detector.py, query_reformulator.py, question_splitter.py
│       ├── coaching/       # Phase 4: story_recaller.py, structure_suggester.py, consistency_tracker.py
│       ├── context/        # manager.py, enhanced_manager.py, chunker.py, gemini_cache.py, file_uploader.py
│       ├── extraction/     # Phase 4: pipeline.py, fact_extractor.py, story_extractor.py, summarizer.py
│       ├── memory/         # Phase 4: store.py, models.py
│       ├── playbook/       # Phase 4: assembler.py, question_generator.py, answer_drafter.py
│       ├── providers/      
│       │   ├── stt/        # Groq, Deepgram, OpenAI, Gemini
│       │   ├── llm/        # OpenAI, Anthropic, Gemini, gemini_search.py
│       │   └── factory.py  # Provider instantiation logic
│       ├── rag/            # engine.py, enhanced_engine.py, speculative.py, gemini_embeddings.py
│       └── storage/        # session_store.py, exporter.py
└── _prism/                # SDLC artifacts
    ├── planning/           # PRDs (prd.md, prd-phase2.md, prd-phase3.md, prd-phase4.md)
    ├── architecture/       # Architecture docs
    └── verification/       # E2E reports
```

## IPC Protocol (WebSocket)

Port: `localhost:8765`

### Client → Server Messages

| Type | Description | Data |
|------|-------------|------|
| `START_SESSION` | Start interview session | `{apiKeys, preferences}` |
| `STOP_SESSION` | End session | `{}` |
| `UPLOAD_CONTEXT` | Upload documents | `{files: [{name, content, documentType}]}` |
| `CALIBRATE_VOICE` | Voice calibration | `{audioData}` |
| `MANUAL_QUESTION` | Manual question input | `{question}` |
| `PREPARE_INTERVIEW` | Request preparation | `{}` |
| `ENHANCE_ANSWER` | Request answer enhancement | `{enhancementType, originalQuestion, originalAnswer}` |
| `LIST_SESSIONS` | List past sessions | `{limit, offset}` |
| `LOAD_SESSION` | Load session data | `{sessionId}` |
| `EXPORT_SESSION` | Export session | `{sessionId, format}` |
| `DELETE_SESSION` | Delete session | `{sessionId}` |

### Server → Client Messages

| Type | Description | Data |
|------|-------------|------|
| `TRANSCRIPTION` | Final transcription | `{speaker, text, timestamp, confidence}` |
| `INTERIM_TRANSCRIPTION` | Partial transcription | `{text, timestamp, speaker}` |
| `ANSWER_START` | Answer generation started | `{}` |
| `ANSWER_CHUNK` | Streaming answer chunk | `{chunk, complete, confidence}` |
| `ERROR` | Error occurred | `{message, code}` |
| `STATUS` | Status update | `{state}` |
| `PREPARATION_READY` | Preparation complete | `{summary}` |
| `EXTRACTION_PROGRESS` | Extraction progress | `{stage, progress, message}` |
| `EXTRACTION_COMPLETE` | Extraction done | `{documentId, filename, success, summary}` |
| `STORY_SUGGESTION` | Story recall | `{storyId, title, situation, relevanceScore, suggestedOpening, keyMetrics, tags}` |
| `STRUCTURE_SUGGESTION` | Answer structure hint | `{name, sections, tips}` |
| `CONSISTENCY_WARNING` | Contradiction detected | `{contradictions}` |
| `ENHANCED_ANSWER_START` | Enhancement started | `{enhancementType, originalQuestion}` |
| `ENHANCED_ANSWER_CHUNK` | Enhanced answer chunk | `{chunk, complete}` |
| `ENHANCED_ANSWER_COMPLETE` | Enhancement done | `{enhancementType, success}` |
| `SESSION_LIST` | Session list response | `{sessions, total, hasMore}` |
| `SESSION_DATA` | Session data response | `{...sessionData}` |
| `SESSION_EXPORT` | Export content | `{content, format}` |
| `SESSION_DELETED` | Deletion confirmation | `{sessionId, success}` |

### Enhancement Types

| Type | Description |
|------|-------------|
| `add_detail` | Re-query RAG with higher limit, add more context |
| `make_specific` | Add metrics, examples, specifics |
| `suggest_star` | Reformat as STAR story |
| `adjust_tone` | Rewrite with different tone (confident/humble) |
| `shorten` | Compress to key points |

## Prism SDLC

This project uses the Prism SDLC framework.

| Phase | Description | Stories | Status |
|-------|-------------|---------|--------|
| Phase 1 | MVP Foundation | 20/20 | ✅ Complete |
| Phase 2 | Multi-Provider & Optimization | 13/13 | ✅ Complete |
| Phase 3 | Intelligence Pipeline | 19/19 | ✅ Complete |
| Phase 4 | Interview Coach Evolution | - | 🟡 Implemented |
| Phase 5 | Gemini Integration | - | 🟡 Implemented |

### Key Documents
- Phase 2 PRD: `_prism/planning/prd-phase2.md`
- Phase 2 Architecture: `_prism/architecture/architecture-phase2.md`
- Phase 4 PRD: `_prism/planning/prd-phase4.md`
- Phase 4 Architecture: `_prism/architecture/architecture-phase4.md`
- Verification Report: `_prism/verification/e2e_report.md`

## Key Phase 4 Features

### Memory Store (`sidecar/src/memory/`)
- SQLite-based persistent storage for candidate data
- Stores skills, timeline, achievements, STAR stories
- Candidate profile injection (~1000 tokens) into every LLM prompt

### Extraction Pipeline (`sidecar/src/extraction/`)
- Multi-stage: Summarize → Extract Facts → Extract Stories → Generate Profile
- Automatic STAR story identification (8-12 stories)
- Progress streaming to UI

### Coaching Engine (`sidecar/src/coaching/`)
- **Story Recaller**: Embedding similarity matching for relevant stories (<1s)
- **Structure Suggester**: STAR, PREP, Pyramid framework recommendations
- **Consistency Tracker**: Claim logging and contradiction detection

## Key Phase 5 Features

### Gemini Integration
- **Context Caching** (`gemini_cache.py`): 2-hour TTL cache for reduced latency
- **File Uploader** (`file_uploader.py`): Direct Gemini File API integration
- **Search Grounding** (`gemini_search.py`): Real-time web search for company/interviewer research
- **Gemini Embeddings** (`gemini_embeddings.py`): Native embedding function

### Enhanced RAG (`sidecar/src/rag/enhanced_engine.py`)
- Child-to-parent expansion (512 → 2048 chars)
- Question-type aware retrieval prioritization
- Sub-question aggregation for multi-part questions

### Answer Enhancement
- 5 enhancement types via `ENHANCE_ANSWER` message
- Streaming enhanced response via `ENHANCED_ANSWER_CHUNK`
