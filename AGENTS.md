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
# ALWAYS run with -m flag from sidecar directory to ensure correct package resolution
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

# Phase 7 Streaming STT tests
cd sidecar && pytest tests/test_streaming_stt.py tests/test_utterance_accumulation.py

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
│       │   ├── AccumulatingIndicator.tsx  # Phase 6: Shows buffering state
│       │   ├── AnswerDisplay.tsx
│       │   ├── CoachingPanel.tsx         # Phase 4: Coaching container
│       │   ├── ConsistencyPanel.tsx      # Phase 4: Claim tracking
│       │   ├── DocumentTypeSelector.tsx
│       │   ├── EnhanceButton.tsx         # Relocated to Answer Header
│       │   ├── PreparationButton.tsx
│       │   ├── PreparationSummary.tsx
│       │   ├── SettingsModal.tsx         # New overlay settings
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
│       ├── classification/ # question_detector.py, query_reformulator.py, question_splitter.py, utterance_accumulator.py
│       ├── coaching/       # Phase 4: story_recaller.py, structure_suggester.py, consistency_tracker.py
│       ├── context/        # manager.py, enhanced_manager.py, chunker.py, gemini_cache.py, file_uploader.py
│       ├── extraction/     # Phase 4: pipeline.py, fact_extractor.py, story_extractor.py, summarizer.py
│       ├── memory/         # Phase 4: store.py, models.py
│       ├── playbook/       # Phase 4: assembler.py, question_generator.py, answer_drafter.py
│       ├── providers/      
│       │   ├── stt/        # LocalWhisper (primary), Gemini (fallback), Deepgram Streaming
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
| `INFER_DOCUMENT_TYPES` | Infer types for uploaded files | `{files: [{name, snippet, ...}]}` |
| `CALIBRATE_VOICE` | Voice calibration | `{audioData}` |
| `MANUAL_QUESTION` | Manual question input | `{question}` |
| `PREPARE_INTERVIEW` | Request preparation | `{}` |
| `ENHANCE_ANSWER` | Request answer enhancement | `{enhancementType, originalQuestion, originalAnswer}` |
| `LIST_SESSIONS` | List past sessions | `{limit, offset}` |
| `LOAD_SESSION` | Load session data | `{sessionId}` |
| `EXPORT_SESSION` | Export session | `{sessionId, format}` |
| `DELETE_SESSION` | Delete session | `{sessionId}` |

### Preferences Object (START_SESSION)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sttProvider` | string | `"auto"` | STT provider: `"auto"`, `"local_whisper"`, `"gemini"` |
| `llmProvider` | string | `"auto"` | LLM provider: `"auto"`, `"gemini"`, `"openai"`, `"anthropic"` |
| `whisperModelSize` | string | `"large-v3-turbo"` | Local Whisper model: `"large-v3-turbo"`, `"distil-large-v3"`, `"medium"`, `"small"` |
| `streamingSttProvider` | string | `"disabled"` | Streaming STT: `"disabled"`, `"auto"`, `"deepgram"`, `"deepgram_flux"` |
| `extendedThinking` | boolean | `false` | Enable high reasoning mode (GPT-5/Claude 4) |
| `searchEnabled` | boolean | `true` | Enable Google Search grounding |

### Server → Client Messages

| Type | Description | Data |
|------|-------------|------|
| `TRANSCRIPTION` | Final transcription | `{speaker, text, timestamp, confidence}` |
| `INTERIM_TRANSCRIPTION` | Partial transcription | `{text, timestamp, speaker}` |
| `ANSWER_START` | Answer generation started | `{}` |
| `ANSWER_CHUNK` | Streaming answer chunk | `{chunk, complete, confidence}` |
| `ERROR` | Error occurred | `{message, code}` |
| `STATUS` | Status update | `{state}` |
| `DOCUMENT_TYPE_SUGGESTIONS` | Document classification results | `{suggestions: [{filename, type, confidence, reasoning}]}` |
| `PREPARATION_READY` | Preparation complete | `{summary}` |
| `EXTRACTION_PROGRESS` | Extraction progress | `{stage, progress, message}` |
| `EXTRACTION_COMPLETE` | Extraction done | `{documentId, filename, success, summary}` |
| `STORY_SUGGESTION` | Story recall | `{storyId, title, situation, relevanceScore, suggestedOpening, keyMetrics, tags}` |
| `STRUCTURE_SUGGESTION` | Answer structure hint | `{name, sections, tips}` |
| `CONSISTENCY_WARNING` | Contradiction detected | `{contradictions}` |
| `ENHANCED_ANSWER_START` | Enhancement started | `{enhancementType, originalQuestion}` |
| `ENHANCED_ANSWER_CHUNK` | Enhanced answer chunk | `{chunk, complete}` |
| `ENHANCED_ANSWER_COMPLETE` | Enhancement done | `{enhancementType, success}` |
| `ACCUMULATING` | Buffering multi-segment question | `{speaker, bufferPreview, segmentCount, durationSeconds}` |
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
| Phase 6 | Utterance Accumulation | - | ✅ Complete |
| Phase 7 | Streaming STT & Semantic Endpointing | - | ✅ Complete |

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

### Query Reformulator (`sidecar/src/classification/query_reformulator.py`)
- **TopicStack**: Tracks topics across all conversation turns
- **Multi-turn Anaphora**: Resolves "that project", "the first topic" across N turns
- **LLM Fallback**: Async reformulation when templates fail
- **3-Tier Architecture**: Template (<5ms) → TopicStack (<20ms) → LLM (~150ms)

## Key Phase 5 Features

### Gemini Integration
- **Context Caching** (`gemini_cache.py`): 2-hour TTL cache for reduced latency
- **File Uploader** (`file_uploader.py`): Direct Gemini File API integration
- **Search Grounding** (`gemini_search.py`): Real-time web search for company/interviewer research
- **Gemini Embeddings** (`gemini_embeddings.py`): Native embedding function
- **Retry Logic**: Exponential backoff for 503/429 errors with configurable max retries
- **Model Fallback**: Automatic fallback to alternative models when primary unavailable

### Enhanced RAG (`sidecar/src/rag/enhanced_engine.py`)
- Child-to-parent expansion (512 → 2048 chars)
- Question-type aware retrieval prioritization
- Sub-question aggregation for multi-part questions
- Prepared Q&A answer prioritization

### Answer Enhancement
- 5 enhancement types via `ENHANCE_ANSWER` message
- Streaming enhanced response via `ENHANCED_ANSWER_CHUNK`

### Privacy & Session Management
- Session isolation: Clear memory, cache, and context on session stop
- Context preservation: Resume context across session restarts
- Secure API key storage via OS keychain

## Key Phase 6 Features

### Utterance Accumulation (`sidecar/src/classification/`)
Solves the problem of multi-segment questions being split by VAD silence detection.

- **UtteranceAccumulator** (`utterance_accumulator.py`): Orchestrates per-speaker buffering
- **CompletenessDetector** (`completeness_detector.py`): 4-tier semantic completeness detection
- **AccumulatorModels** (`accumulator_models.py`): Data classes for config, buffers, and results

### 4-Tier Completeness Detection
1. **Tier 1 - Punctuation** (<1ms): Checks for terminal punctuation (., ?, !)
2. **Tier 2 - Syntax** (<5ms): Regex patterns for complete sentence structures
3. **Tier 3 - Timing** (<1ms): Hard timeout (5s) and soft timeout (2s) checks
4. **Tier 4 - LLM** (~150ms): Async semantic completeness check for ambiguous cases

### Configuration (Environment Variables)
```bash
ACCUMULATOR_ENABLED=true           # Feature flag
ACCUMULATOR_MERGE_GAP_MS=500       # Max gap between segments to merge
ACCUMULATOR_SOFT_TIMEOUT_MS=2000   # Soft timeout before LLM check
ACCUMULATOR_HARD_TIMEOUT_MS=5000   # Hard timeout, force finalize
ACCUMULATOR_MAX_CHARACTERS=2000    # Max buffer size
ACCUMULATOR_USE_LLM_FALLBACK=true  # Enable Tier 4 LLM check
```

### Frontend Integration
- **AccumulatingIndicator** (`src/ui/components/AccumulatingIndicator.tsx`): Shows buffering state
- **AccumulatingState** in session store: Tracks speaker, preview, segment count, duration
- **ACCUMULATING** message type: Real-time updates from server during buffering

## Key Phase 7 Features (Gen 1 2026 Update)

### Streaming STT (`sidecar/src/providers/stt/`)
Real-time WebSocket-based speech-to-text with semantic endpointing for lower latency.

#### Provider Implementations (2026 Models)
| Provider | File | Model | Endpointing | Latency |
|----------|------|-------|-------------|---------|
| Deepgram | `deepgram_streaming.py` | `nova-3` | Acoustic (`utterance_end_ms`) | ~150ms |
| AssemblyAI | `assemblyai_streaming.py` | `best` (V3) | Semantic (`end_of_turn_confidence`) | ~256ms |
| OpenAI Realtime | `openai_realtime.py` | `gpt-realtime` (GA) | Semantic (`semantic_vad`) | ~250ms |

#### Core Components
- **StreamingSTTProvider** (`streaming_base.py`): Abstract base class for streaming providers
- **StreamingSession**: WebSocket session lifecycle management
- **StreamingSTTManager** (`streaming_manager.py`): Facade for easy integration
- **StreamingSTTCallbacks**: Event handlers for interim/final/end-of-turn events

#### Data Types
```python
# Interim transcription (partial)
InterimResult(text: str, is_final: bool, confidence: float)

# End of turn signal
EndOfTurnEvent(
    final_transcript: str,
    confidence: float,
    endpointing_type: EndpointingType,  # ACOUSTIC or SEMANTIC
    latency_ms: float
)
```

### Hybrid Endpointing Mode
The accumulator supports three endpointing modes via `ACCUMULATOR_ENDPOINTING_MODE`:

| Mode | Behavior |
|------|----------|
| `timing` | Use only timing-based detection (Tiers 1-4) |
| `streaming` | Use only streaming provider endpointing |
| `hybrid` (default) | Prefer streaming semantic endpointing, fall back to timing |

### Configuration (Environment Variables)
```bash
# Streaming STT
ASSEMBLYAI_API_KEY=xxx           # Required for AssemblyAI streaming (V3)
OPENAI_API_KEY=xxx               # Required for OpenAI Realtime (GA)

# Endpointing Mode
ACCUMULATOR_ENDPOINTING_MODE=hybrid   # timing, streaming, or hybrid
ACCUMULATOR_STREAMING_CONFIDENCE=0.7  # Min confidence for streaming endpoint
```

### Streaming Flow
```
Audio Chunk → StreamingSTTManager.send_audio()
                    ↓
           StreamingSession (WebSocket)
                    ↓
        ┌──────────┴──────────┐
        ↓                     ↓
  InterimResult          EndOfTurnEvent
  (partial text)         (turn complete)
        ↓                     ↓
  Broadcast to UI      Check Confidence
        ↓                     ↓
        ↓            ┌────────┴────────┐
        ↓            ↓                 ↓
        ↓       High (≥0.7)        Low (<0.7)
        ↓            ↓                 ↓
        ↓      Direct to          Accumulator
        ↓      RAG+LLM            add_segment
        └────────────┴─────────────────┘
                     ↓
              Question Detection
                     ↓
              Answer Generation
```

### Gen 1 2026 Model Support
- **LLM**: GPT-5.2, Claude 4 Opus, Gemini 3 Pro
- **STT**: Nova-3, Whisper V3 Turbo, Gemini 3 Flash
- **Reasoning**: "High Reasoning Mode" (Extended Thinking) toggle for complex logic tasks.

### Latency Benchmark
```bash
# Run benchmark (requires server running)
cd sidecar && python scripts/benchmark_latency.py

# Test specific mode
python scripts/benchmark_latency.py --mode hybrid --questions 10

# Dry run (no API calls)
python scripts/benchmark_latency.py --dry-run
```

### Expected Improvements
- **Batch STT**: ~800-1500ms first token latency
- **Streaming STT**: ~400-800ms first token latency
- **Hybrid Mode**: ~300-600ms first token latency (30-50% improvement)
