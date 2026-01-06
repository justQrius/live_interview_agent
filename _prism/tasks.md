# Live Interview Agent - Task Tracking

**Created**: 2026-01-05
**Status**: Solution Complete - Ready for Implementation
**Architecture**: `_prism/architecture/architecture.md`

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


- [ ] **Story 3.2**: ChromaDB + Embeddings (ID: STORY-010)
  - Initialize ChromaDB persistent storage (~/.live_interview_agent/chroma/)
  - Integrate Gemini Embeddings API (text-embedding-004)
  - Implement embed_chunks and store_in_db
  - Dependencies: STORY-009, STORY-004 (needs API key)
  - Deliverable: Documents chunked and stored in vector DB

- [ ] **Story 3.3**: RAG Engine (ID: STORY-011)
  - Implement similarity search (top-5 retrieval)
  - Build query embedding → retrieval pipeline
  - Implement confidence scoring (high/medium/low based on similarity)
  - Dependencies: STORY-010
  - Deliverable: Given question, retrieve relevant chunks

### Phase 4: LLM + Answer Generation

- [ ] **Story 4.1**: Gemini LLM Integration (ID: STORY-012)
  - Implement Gemini LLM client with streaming (gemini-1.5-flash)
  - Build prompt template with context injection
  - Connect RAG retrieval → LLM generation
  - Dependencies: STORY-011, STORY-004
  - Deliverable: Streaming answers generated

- [ ] **Story 4.2**: Answer Display UI (ID: STORY-013)
  - Build streaming answer display component
  - Implement word-by-word typing effect
  - Show confidence indicators (high/medium/low badges)
  - Dependencies: STORY-012, STORY-003
  - Deliverable: Answers stream smoothly to UI

- [ ] **Story 4.3**: Full Pipeline Integration (ID: STORY-014)
  - Connect: audio → VAD → STT → diarization → RAG → LLM → UI
  - Filter "User" speech (only process "Interviewer" questions)
  - Test end-to-end latency (<5 seconds)
  - Dependencies: STORY-008, STORY-012, STORY-007
  - Deliverable: Complete interview assistant workflow

### Phase 5: Advanced Features

- [ ] **Story 5.1**: Screen Invisibility (ID: STORY-015)
  - Implement platform-specific window flags (DWM/NSWindow/X11)
  - Create Tauri command `toggle_screen_invisibility`
  - Add UI toggle button
  - Test on each OS with screen sharing tools
  - Dependencies: STORY-001
  - Deliverable: App invisible in screen shares

- [ ] **Story 5.2**: Session Controls (ID: STORY-016)
  - Implement Start/Stop session logic
  - Clear session data (transcripts, answers) on stop
  - Add manual question input fallback (text box)
  - Dependencies: STORY-014
  - Deliverable: Users can control session lifecycle

- [ ] **Story 5.3**: Noise Reduction (Optional) (ID: STORY-017)
  - Integrate `noisereduce` library
  - Apply preprocessing before STT
  - Test accuracy improvement
  - Dependencies: STORY-005
  - Deliverable: Improved STT accuracy in noisy conditions

### Phase 6: Packaging + Distribution

- [ ] **Story 6.1**: PyInstaller Bundling (ID: STORY-018)
  - Create PyInstaller spec file
  - Bundle Python sidecar into single executable
  - Configure Tauri to include sidecar in resources
  - Dependencies: All sidecar stories (STORY-002 through STORY-012)
  - Deliverable: Self-contained sidecar executable

- [ ] **Story 6.2**: Platform Installers (ID: STORY-019)
  - Configure Tauri bundler (MSI, DMG, AppImage)
  - Test installation on clean VMs
  - Verify app launches and functions
  - Dependencies: STORY-018, All UI stories
  - Deliverable: Platform-specific installers

- [ ] **Story 6.3**: End-to-End Testing (ID: STORY-020)
  - 2-hour stability test (no crashes)
  - Resource usage validation (<500MB RAM, <30% CPU)
  - Latency testing (P50 <3s, P95 <5s)
  - Screen invisibility verification
  - Dependencies: STORY-019
  - Deliverable: MVP meets all NFRs

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
