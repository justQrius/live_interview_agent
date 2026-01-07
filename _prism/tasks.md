# Live Interview Agent - Task Tracking

**Created**: 2026-01-05
**Status**: Phase 1 Complete (19/20), Phase 2 In Progress (4/13)
**Architecture**: 
- Phase 1: `_prism/architecture/architecture.md`
- Phase 2: `_prism/architecture/architecture-phase2.md`
**PRD**:
- Phase 1: `_prism/planning/prd.md`
- Phase 2: `_prism/planning/prd-phase2.md`

---

## Epic: Live Interview Agent MVP

Status: open
Priority: P1
Created: 2026-01-05

---

## Implementation Stories (Build Sequence)

### Phase 1: Foundation

- [x] **Story 1.1**: Tauri Project Setup (ID: STORY-001) ✅ COMPLETED 2026-01-06
  - Initialize Tauri app with React + TypeScript + Tailwind CSS
  - Configure Vite, directory structure
  - Dependencies: None
  - Deliverable: `npm run tauri dev` launches empty app
  - **Completed**: Tauri 2.9.6, React 19.2.3, TypeScript 5.9.3, Vite 7.3.0, Tailwind 3.4.19, Zustand 4.5.7

- [x] **Story 1.2**: Python Sidecar Setup (ID: STORY-002) ✅ COMPLETED 2026-01-06
  - Create `sidecar/` Python project structure
  - Setup virtual environment and dependencies
  - Create WebSocket server skeleton
  - Dependencies: None (can run parallel with 1.1)
  - Deliverable: Standalone Python server runs on port 8765
  - **Completed**: Python 3.12, websockets 15.0.1, pytest 9.0.2, message protocol with 9 message types, 17 tests passing

- [x] **Story 1.3**: WebSocket Communication (ID: STORY-003) ✅ COMPLETED 2026-01-06
  - Implement WebSocket client in React UI
  - Implement JSON message protocol
  - Test bidirectional messaging
  - Dependencies: STORY-001, STORY-002
  - Deliverable: UI can send/receive messages to/from sidecar
  - **Completed**: useWebSocket hook, sessionStore API key support, 8 integration tests, 29 React tests, 25 Python tests

- [x] **Story 1.4**: Config Store - API Keys (ID: STORY-004) ✅ COMPLETED 2026-01-06
  - Implement `keyring.rs` in Tauri (OS keychain integration)
  - Create Tauri commands: `get_api_key`, `set_api_key`
  - Build UI settings screen for API key input
  - Dependencies: STORY-001
  - Deliverable: API key stored securely, retrieved on app start
  - **Completed**: Rust keyring integration (Windows/macOS/Linux), Tauri commands (get/set/delete/has_api_key), SettingsPanel UI, 23 React tests + 9 Rust tests

### Phase 2: Audio Pipeline

- [x] **Story 2.1**: Audio Capture Module (ID: STORY-005) ✅ COMPLETED 2026-01-06
  - Implement platform-specific audio capture (Windows/macOS/Linux)
  - Create circular buffer (5-second capacity)
  - Stream 500ms audio chunks via WebSocket
  - Dependencies: STORY-003
  - Deliverable: Raw audio captured and streamable
  - **Completed**: Platform-specific backends (pyaudiowpatch/sounddevice), CircularBuffer class (80k samples), async stream generator (500ms chunks), 35 tests passing

- [x] **Story 2.2**: Silero VAD Integration (ID: STORY-006) ✅ COMPLETED 2026-01-06
  - Integrate Silero VAD v4 model
  - Implement speech segment detection (512 samples, 0.5 threshold)
  - Filter silence from audio stream
  - Dependencies: STORY-005
  - Deliverable: Only speech segments passed downstream
  - **Completed**: VADProcessor class with Silero VAD v4, 512-sample sliding window (32ms), 0.5 threshold, 3-frame smoothing, SpeechSegment dataclass, thread-safe, 29 tests passing

- [x] **Story 2.3**: Voice Calibration + Diarization (ID: STORY-007) ✅ COMPLETED 2026-01-06
  - Build calibration modal in UI (5-10s voice sample)
  - Implement ECAPA-TDNN speaker embedding in Python
  - Save/load voice profiles to disk (Currently in-memory for session)
  - Classify "User" vs "Interviewer" (>0.75 cosine similarity)
  - Dependencies: STORY-006, STORY-003
  - Deliverable: Accurate speaker classification
  - **Completed**: SpeechBrain ECAPA-TDNN integration, React CalibrationModal with AudioContext capture, WebSocket calibration flow, full test coverage.

- [ ] **Story 2.4**: Gemini STT Integration (ID: STORY-008)

- [x] **Story 2.4**: Gemini STT Integration (ID: STORY-008) ✅ COMPLETED 2026-01-06
  - Implement Gemini STT client in Python
  - Connect VAD output → STT input
  - Send transcriptions with speaker labels to UI
  - Dependencies: STORY-006, STORY-004 (needs API key)
  - Deliverable: Live transcription displayed in UI
  - **Completed**: GeminiSTT class with google-generativeai, PCM-to-WAV conversion, SidecarServer integration with speaker verification, 6 new tests passed.

### Phase 3: RAG + Context

- [x] **Story 3.1**: Context Manager (ID: STORY-009) ✅ COMPLETED 2026-01-06
  - Implement document parsers (PDF via pypdf, DOCX, TXT, URL)
  - Build chunking logic (500 tokens, 50 token overlap)
  - Create context upload UI with file picker
  - Dependencies: STORY-003
  - Deliverable: Users can upload files, see preview
  - **Completed**: Parsers (PDF/DOCX/TXT), Character-based Chunker (2000 chars ~ 500 tokens), ContextManager, Server integration for UPLOAD_CONTEXT, 7 tests passing.


- [x] **Story 3.2**: ChromaDB + Embeddings (ID: STORY-010) ✅ COMPLETED 2026-01-06
  - Initialize ChromaDB persistent storage (~/.live_interview_agent/chroma/)
  - Integrate Gemini Embeddings API (text-embedding-004)
  - Implement embed_chunks and store_in_db
  - Dependencies: STORY-009, STORY-004 (needs API key)
  - Deliverable: Documents chunked and stored in vector DB
  - **Completed**: GeminiEmbeddingFunction with text-embedding-004, VectorStore with ChromaDB persistence, Server integration for adding/clearing chunks, ContextManager updated to return chunks. 9 tests passed.

- [x] **Story 3.3**: RAG Engine (ID: STORY-011) ✅ COMPLETED 2026-01-06
  - Implement similarity search (top-5 retrieval)
  - Build query embedding → retrieval pipeline
  - Implement confidence scoring (high/medium/low based on similarity)
  - Dependencies: STORY-010
  - Deliverable: Given question, retrieve relevant chunks
  - **Completed**: RAGEngine implemented with confidence scoring (High < 0.3, Medium < 0.5), integrated into server loop for manual questions. 5 tests passed.

### Phase 4: LLM + Answer Generation

- [x] **Story 4.1**: Gemini LLM Integration (ID: STORY-012) ✅ COMPLETED 2026-01-06
  - Implement Gemini LLM client with streaming (gemini-1.5-flash)
  - Build prompt template with context injection
  - Connect RAG retrieval → LLM generation
  - Dependencies: STORY-011, STORY-004
  - Deliverable: Streaming answers generated
  - **Completed**: GeminiLLM class with streaming, integration with RAG Engine and Server, 5 unit tests + 2 integration tests passing.


- [x] **Story 4.2**: Answer Display UI (ID: STORY-013) ✅ COMPLETED 2026-01-06
  - Build streaming answer display component
  - Implement word-by-word typing effect
  - Show confidence indicators (high/medium/low badges)
  - Dependencies: STORY-012, STORY-003
  - Deliverable: Answers stream smoothly to UI
  - **Completed**: AnswerDisplay component implemented with auto-scroll, confidence badges, and store integration. 5 unit tests passing.


- [x] **Story 4.3**: Full Pipeline Integration (ID: STORY-014) ✅ COMPLETED 2026-01-06
  - Connect: audio → VAD → STT → diarization → RAG → LLM → UI
  - Filter "User" speech (only process "Interviewer" questions)
  - Test end-to-end latency (<5 seconds)
  - Dependencies: STORY-008, STORY-012, STORY-007
  - Deliverable: Complete interview assistant workflow
  - **Completed**: Full pipeline implemented with `_process_speech_segment`, `_identify_speaker`, `_generate_answer_for_question`. 7 integration tests passing.

### Phase 5: Advanced Features

- [x] **Story 5.1**: Screen Invisibility (ID: STORY-015) ✅ COMPLETED 2026-01-06
  - Implement platform-specific window flags (DWM/NSWindow/X11)
  - Create Tauri command `toggle_screen_invisibility`
  - Add UI toggle button
  - Test on each OS with screen sharing tools
  - Dependencies: STORY-001
  - Deliverable: App invisible in screen shares
  - **Completed**: Windows (SetWindowDisplayAffinity), macOS (NSWindow.sharingType), Linux (warning fallback). SettingsPanel toggle connected to Tauri command. 11 Rust tests, 27 React tests for settings.

- [x] **Story 5.2**: Session Controls (ID: STORY-016) ✅ COMPLETED 2026-01-06
  - Implement Start/Stop session logic
  - Clear session data (transcripts, answers) on stop
  - Add manual question input fallback (text box)
  - Dependencies: STORY-014
  - Deliverable: Users can control session lifecycle
  - **Completed**: SessionControls with Start/Stop buttons, confirmation dialog, manual question textarea, transcription history in sessionStore and AnswerDisplay. 30 new React tests, all 234 tests passing.

- [x] **Story 5.3**: Noise Reduction (Optional) (ID: STORY-017) ✅ COMPLETED 2026-01-06
  - Integrate `noisereduce` library
  - Apply preprocessing before STT (after VAD detection)
  - Test accuracy improvement
  - Dependencies: STORY-005
  - Deliverable: Improved STT accuracy in noisy conditions
  - **Completed**: NoiseReducer class with configurable options (stationary/non-stationary, aggressiveness), integrated in server pipeline (VAD → NoiseReducer → STT), 42 tests passing (31 unit + 11 integration), <100ms latency, NoiseReducerError exception class for consistency, comprehensive documentation in sidecar/docs/noise_reduction.md

### Phase 6: Packaging + Distribution

- [x] **Story 6.1**: PyInstaller Bundling (ID: STORY-018) ✅ COMPLETED 2026-01-06
  - Create PyInstaller spec file
  - Bundle Python sidecar into single executable
  - Configure Tauri to include sidecar in resources
  - Dependencies: All sidecar stories (STORY-002 through STORY-012)
  - Deliverable: Self-contained sidecar executable
  - **Completed**: Created sidecar.spec with hidden imports for torch/speechbrain/chromadb/google-generativeai, build.py script for cross-platform builds, updated Tauri config with externalBin, implemented full sidecar.rs with process management (start/stop/is_running). 16 new bundling tests (13 pass, 3 skip until build runs), 14 Rust tests, 100 React tests all passing.

- [x] **Story 6.2**: Platform Installers (ID: STORY-019) COMPLETED 2026-01-06
  - Configure Tauri bundler (MSI, DMG, AppImage)
  - Test installation on clean VMs
  - Verify app launches and functions
  - Dependencies: STORY-018, All UI stories
  - Deliverable: Platform-specific installers
  - **Completed**: Updated tauri.conf.json with full bundle configuration for Windows (MSI/NSIS with WebView2 bootstrapper, WiX upgrade code), macOS (DMG with window size, minimum system 10.15), Linux (AppImage with media framework, deb/rpm with dependencies). Created build-installer.py script for automated cross-platform builds. Added MIT LICENSE file. 30 installer config tests passing.

- [ ] **Story 6.3**: End-to-End Testing (ID: STORY-020)
  - 2-hour stability test (no crashes)
  - Resource usage validation (<500MB RAM, <30% CPU)
  - Latency testing (P50 <3s, P95 <5s)
  - Screen invisibility verification
  - Dependencies: STORY-019
  - Deliverable: MVP meets all NFRs

---

## Phase 2: Optimizations & Multi-Provider Support

### Phase 2.1: Foundation

- [x] **Story 2.1**: Model Pre-warming Infrastructure (ID: STORY-021) ✅ COMPLETED 2026-01-06
  - Create `sidecar/src/warmup.py` with ModelWarmer class
  - Load Silero VAD and ECAPA-TDNN at sidecar startup
  - Background thread loading with ready signal
  - Dependencies: None
  - Deliverable: Models pre-loaded, cold start <1s
  - **Completed**: ModelWarmer class implemented, integrated into server.py startup.

- [x] **Story 2.2**: Provider Base Interfaces (ID: STORY-022) ✅ COMPLETED 2026-01-06
  - Create `sidecar/src/providers/base.py`
  - Define STTProvider, LLMProvider, EmbeddingProvider ABCs
  - Define ProviderType enum and result dataclasses
  - Dependencies: None
  - Deliverable: Abstract interfaces for all providers
  - **Completed**: Base interfaces and dataclasses implemented.

- [x] **Story 2.3**: Provider Factory (ID: STORY-023) ✅ COMPLETED 2026-01-07
  - Create `sidecar/src/providers/factory.py`
  - Implement ProviderFactory with fallback chains
  - Add ProviderConfig for multi-key management
  - Dependencies: STORY-022
  - Deliverable: Factory creates providers with fallback
  - **Completed**: ProviderConfig dataclass with from_dict(), has_api_key(), get_api_key() methods. ProviderFactory with STT/LLM fallback chains (Groq→Deepgram→OpenAI→Gemini for STT, OpenAI→Anthropic→Gemini for LLM), provider caching, status reporting. ProviderType enum, ProviderError exception. 38 provider tests passing.

### Phase 2.2: Provider Refactoring

- [x] **Story 2.4**: Refactor Gemini STT to Provider (ID: STORY-024) ✅ COMPLETED 2026-01-07
  - Move `stt/gemini_stt.py` to `providers/stt/gemini.py`
  - Implement STTProvider interface
  - Update server.py imports
  - Dependencies: STORY-022
  - Deliverable: Gemini STT works via provider interface
  - **Completed**: Created `providers/stt/gemini.py` with GeminiSTTProvider implementing STTProvider interface. Returns TranscriptionResult from transcribe(). Updated server.py to use new provider. 16 new provider tests + updated existing tests. 247 tests passing.

- [x] **Story 2.5**: Refactor Gemini LLM to Provider (ID: STORY-025) ✅ COMPLETED 2026-01-07
  - Move `llm/gemini_llm.py` to `providers/llm/gemini.py`
  - Implement LLMProvider interface
  - Update server.py imports
  - Dependencies: STORY-022
  - Deliverable: Gemini LLM works via provider interface
  - **Completed**: Created `providers/llm/gemini.py` with GeminiLLMProvider implementing LLMProvider interface. Provides both `generate_response(prompt, context, history)` and backwards-compatible `generate_answer(question, context_chunks)`. Updated server.py to use new provider. 20 new provider tests + updated existing tests. 267 tests passing.

### Phase 2.3: New STT Providers

- [x] **Story 2.6**: Groq STT Provider (ID: STORY-026) ✅ COMPLETED 2026-01-07
  - Create `providers/stt/groq.py`
  - Integrate `groq` Python package
  - Implement Whisper-large-v3 transcription
  - Dependencies: STORY-023
  - Deliverable: Groq STT available as option
  - **Completed**: Implemented GroqSTTProvider with asyncio.to_thread for non-blocking API calls. Integrated groq package. Verified with unit tests mocking the API.

- [x] **Story 2.7**: Deepgram STT Provider (ID: STORY-027) ✅ COMPLETED 2026-01-07
  - Create `providers/stt/deepgram.py`
  - Integrate `deepgram-sdk` Python package
  - Implement Nova-2 transcription
  - Dependencies: STORY-023
  - Deliverable: Deepgram STT available as option
  - **Completed**: Implemented `DeepgramSTTProvider` with `deepgram-sdk`. Verified via unit tests.

- [ ] **Story 2.8**: OpenAI Whisper STT Provider (ID: STORY-028)
  - Create `providers/stt/openai.py`
  - Integrate `openai` Python package for Whisper
  - Implement Whisper-1 transcription
  - Dependencies: STORY-023
  - Deliverable: OpenAI Whisper STT available as option

### Phase 2.4: New LLM Providers

- [x] **Story 2.9**: OpenAI LLM Provider (ID: STORY-029) ✅ COMPLETED 2026-01-07
  - Create `providers/llm/openai.py`
  - Integrate `openai` Python package for GPT-4o
  - Implement streaming with same prompt template
  - Dependencies: STORY-023
  - Deliverable: OpenAI GPT-4o available as LLM option
  - **Completed**: Implemented `OpenAILLMProvider` using `openai` async client. Verified with unit tests.

- [ ] **Story 2.10**: Anthropic LLM Provider (ID: STORY-030)
  - Create `providers/llm/anthropic.py`
  - Integrate `anthropic` Python package
  - Implement Claude 3.5 Sonnet streaming
  - Dependencies: STORY-023
  - Deliverable: Anthropic Claude available as LLM option

### Phase 2.5: Browser VAD & UI

- [ ] **Story 2.11**: Browser VAD Integration (ID: STORY-031)
  - Add `@ricky0123/vad-react` and `onnxruntime-web` to package.json
  - Create `src/ui/hooks/useVADFilter.ts`
  - Update Tauri CSP for WASM
  - Bundle ONNX assets in public folder
  - Modify WebSocket to send speech-only segments
  - Dependencies: None
  - Deliverable: Browser filters silence, 60%+ WebSocket reduction

- [ ] **Story 2.12**: Provider Configuration UI (ID: STORY-032)
  - Create `src/ui/components/ProviderSettings.tsx`
  - Add multi-provider API key inputs to SettingsPanel
  - Store keys per-provider in OS keychain
  - Add provider preference dropdowns (STT/LLM)
  - Dependencies: STORY-023 through STORY-030
  - Deliverable: Users can configure and select providers

### Phase 2.6: Integration

- [ ] **Story 2.13**: Server Integration + E2E Testing (ID: STORY-033)
  - Update `server.py` to use ProviderFactory
  - Update `protocol.py` with provider config messages
  - Integration tests for all providers
  - Latency benchmarking (target: P50 <1.5s)
  - Dependencies: All above
  - Deliverable: Full Phase 2 integration, all tests passing

---

## Phase 2 Story Dependencies

```
                    STORY-021 (Pre-warming)
                           |
    +----------------------+----------------------+
    |                                              |
STORY-022 (Interfaces)                      STORY-031 (Browser VAD)
    |                                              |
    v                                              |
STORY-023 (Factory)                                |
    |                                              |
    +------+------+------+------+                  |
    |      |      |      |      |                  |
    v      v      v      v      v                  |
  024    025    026    029    027                  |
(Gemini (Gemini (Groq (OpenAI (Deepgram           |
  STT)   LLM)   STT)   LLM)   STT)                |
                  |      |      |                  |
                  v      v      v                  |
                028    030                         |
             (OpenAI (Anthropic                    |
              STT)    LLM)                         |
                  |      |                         |
                  +------+-------------------------+
                         |
                         v
                  STORY-032 (Provider UI)
                         |
                         v
                  STORY-033 (Integration)
```

---

## Story Dependencies (Critical Path)

```
STORY-001 ──┬──> STORY-003 ──> STORY-005 ──> STORY-006 ──> STORY-007 ──┐
            │                                            │               │
            └──> STORY-004 ──────────────────────────────┴───────────────┤
                                                                         │
STORY-002 ──────────────────────────────────────────────────────────────┘
                                                                         │
            ┌────────────────────────────────────────────────────────────┘
            │
            v
STORY-008 ──> STORY-009 ──> STORY-010 ──> STORY-011 ──> STORY-012 ──> STORY-013
                                                                         │
                                                                         v
STORY-014 ──> STORY-016 ──> STORY-018 ──> STORY-019 ──> STORY-020
```

---

## Requirements Coverage

### Must-Have Requirements

| Requirement | Stories |
|-------------|---------|
| FR-1: System Audio Capture | STORY-005 |
| FR-2: Real-Time STT | STORY-008 |
| FR-3: Speaker Diarization | STORY-007 |
| FR-4: Context Loading | STORY-009 |
| FR-5: RAG Retrieval | STORY-011 |
| FR-6: LLM Answer Generation | STORY-012 |
| FR-7: Real-Time Display | STORY-013 |
| FR-8: Screen Invisibility | STORY-015 |
| FR-9: Voice Calibration | STORY-007 |
| FR-10: Session Controls | STORY-016 |

### Should-Have Requirements

| Requirement | Stories |
|-------------|---------|
| FR-11: Confidence Indicators | STORY-013 |
| FR-12: Manual Question Input | STORY-016 |
| FR-13: Noise Reduction | STORY-017 |

### NFRs

| NFR | Verified In |
|-----|-------------|
| NFR-1: <5s Latency | STORY-020 |
| NFR-2: <500ms Audio Delay | STORY-005 |
| NFR-3: Resource Usage | STORY-020 |
| NFR-4: Cross-Platform | STORY-019 |
| NFR-5: <5 min Setup | STORY-019 |
| NFR-6: Session Stability | STORY-020 |
| NFR-7: UI Responsiveness | STORY-013 |
| NFR-8: API Cost | STORY-020 |
| NFR-9: Retrieval Accuracy | STORY-011 |
| NFR-10: Security | STORY-004 |

---

## Phase Progress

- [x] Planning Phase - PRD approved 2026-01-05
- [x] Solution Phase - Architecture approved 2026-01-05
- [ ] Implementation Phase - TDD development
- [ ] Verification Phase - Testing & documentation

---

## Notes

- Architecture: Tauri (Rust + React) + Python Sidecar via WebSocket
- Using Gemini models for STT, LLM, and embeddings
- Beads CLI unavailable - using this file for tracking
- Next step: `/prism-implement STORY-005` for Audio Capture Module (depends on STORY-003, now complete)
