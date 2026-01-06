# Session Notes - Live Interview Agent

## Session: 2026-01-05 - Planning Phase

### What Was Accomplished

1. **Spec Discovery Complete**
   - Gathered requirements through structured Q&A
   - Identified problem: Real-time interview assistance (no memorization needed)
   - Defined target users: Tech industry job seekers
   - Established constraints: Gemini models, cross-platform, API costs acceptable

2. **Edge Cases Analyzed**
   - 12 edge cases identified with solutions
   - Key challenges: audio quality, panel interviews, screen invisibility, API failures

3. **Spec Document Created**
   - Location: `_prism/discovery/spec.md`
   - User approved

4. **PRD Document Created**
   - Location: `_prism/planning/prd.md`
   - 15 functional requirements (10 must-have, 3 should-have, 2 could-have)
   - 11 non-functional requirements
   - 3 user personas
   - 13 edge cases documented
   - User approved

5. **Task Tracking Setup**
   - Beads CLI unavailable (hangs on Windows/MINGW64)
   - Using `_prism/tasks.md` as fallback
   - All requirements tracked with IDs

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider (MVP) | Gemini | User preference |
| STT Provider (MVP) | Gemini | User preference, consistency |
| Audio Capture | System audio (speaker) | Platform-agnostic approach |
| Multi-provider | Deferred to future | MVP simplicity |
| Language Support | English only (MVP) | Scope control |

---

## Session: 2026-01-05 - Solution Phase

### What Was Accomplished

1. **Technical Decisions Made** (User Q&A)
   - UI Framework: **Tauri** (Rust + WebView) - lightweight, ~10MB bundle
   - Embeddings: **Gemini Embeddings API** - consistent ecosystem
   - Voice Calibration: **Mandatory** at session start
   - Distribution: **Standalone executable**
   - VAD: **Silero VAD** - high accuracy, PyTorch-based
   - Vector DB: **ChromaDB** - Python-native, persistent
   - Streaming Display: **Word-by-word** - better readability
   - Audio Capture: **Platform-specific native APIs** - best quality

2. **Architecture Designed**
   - Sidecar pattern: Tauri app + Python sidecar
   - IPC: WebSocket on localhost:8765
   - Location: `_prism/architecture/architecture.md`
   - User approved

3. **Implementation Stories Created**
   - 20 stories across 6 phases
   - Dependencies mapped
   - Requirements coverage verified
   - Location: `_prism/tasks.md`

4. **CLAUDE.md Updated**
   - Tech stack documented
   - Conventions established
   - Project structure defined
   - Anti-patterns listed

### Architecture Summary

```
┌─────────────────────┐    WebSocket    ┌─────────────────────┐
│  Tauri (Rust + UI)  │◄───────────────►│   Python Sidecar    │
│  - React frontend   │  localhost:8765 │  - Audio capture    │
│  - Window manager   │                 │  - Silero VAD       │
│  - Keyring (API key)│                 │  - Gemini STT/LLM   │
└─────────────────────┘                 │  - ChromaDB RAG     │
                                        └─────────────────────┘
```

### Build Sequence (Phases)

1. **Foundation**: Tauri setup, Python sidecar, WebSocket IPC, API key storage
2. **Audio Pipeline**: Capture, VAD, calibration, STT
3. **RAG + Context**: Document parsing, ChromaDB, retrieval
4. **LLM + Answers**: Gemini LLM, streaming display, full pipeline
5. **Advanced**: Screen invisibility, session controls, noise reduction
6. **Packaging**: PyInstaller bundling, platform installers, E2E testing

---

## Session: 2026-01-06 - Implementation Phase (Story 001)

### What Was Accomplished

1. **Story 001: Tauri Project Setup - COMPLETE**
   - Initialized Tauri 2.9.6 application with React 19.2.3 + TypeScript 5.9.3
   - Added Tailwind CSS 3.4.19 with PostCSS and Autoprefixer
   - Configured Vite 7.3.0 as build tool
   - Added Zustand 4.5.7 for state management
   - Created full directory structure per architecture spec

2. **Files Created**
   - Frontend: `src/ui/App.tsx`, components (SessionControls, AnswerDisplay, ContextLoader, CalibrationModal, SettingsPanel)
   - Store: `src/ui/store/sessionStore.ts` with full SessionState types matching architecture
   - Hooks: `src/ui/hooks/useWebSocket.ts` with message handling and auto-reconnect
   - Backend: `src-tauri/src/commands/` (config.rs, window.rs, sidecar.rs) - placeholders
   - Utils: `src-tauri/src/utils/` (keyring.rs, platform.rs) - placeholders

3. **Verification Passed**
   - `npm run build` - Success
   - `cargo check` - Success (3 dead_code warnings expected for placeholder utils)
   - `npm run tauri:dev` - Compiles and launches successfully

4. **Post-Implementation Fixes**
   - Fixed `useWebSocket.isConnected` to use `useState` for proper re-renders
   - Connected all components to Zustand store:
     - SessionControls: status, isConnected indicator, button states
     - AnswerDisplay: currentTranscription, currentAnswer with confidence badges
     - SettingsPanel: isScreenInvisible toggle

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tauri Version | v2 (2.9.6) | Latest stable, better API than v1.5 |
| React Version | v19.2.3 | Latest stable |
| WebSocket Reconnect | 5-second retry | Balance between responsiveness and not flooding |

---

## Context for Next Session

- **Project**: Live Interview Agent - AI assistant for real-time interview support
- **Phase**: Implementation - Story 001 Complete
- **Key Files**:
  - PRD: `_prism/planning/prd.md`
  - Architecture: `_prism/architecture/architecture.md`
  - Tasks: `_prism/tasks.md`
  - Conventions: `CLAUDE.md`

### Project Structure Created
```
live_interview_agent/
├── src/
│   ├── main.tsx
│   ├── index.css
│   └── ui/
│       ├── App.tsx
│       ├── components/ (5 components)
│       ├── store/sessionStore.ts
│       └── hooks/useWebSocket.ts
├── src-tauri/
│   └── src/
│       ├── lib.rs, main.rs
│       ├── commands/ (config, window, sidecar)
│       └── utils/ (keyring, platform)
└── _prism/
```

### Next Steps

1. ~~**STORY-002**: Python Sidecar Setup - Create WebSocket server on port 8765~~ ✅ COMPLETE
2. **STORY-003**: WebSocket Communication - Test bidirectional messaging (both dependencies now complete)
3. **STORY-004**: Config Store - Implement keyring for API key storage (depends only on STORY-001)

---

## Session: 2026-01-06 - Implementation Phase (Story 002)

### What Was Accomplished

1. **Story 002: Python Sidecar Setup - COMPLETE**
   - Created `sidecar/` directory structure per architecture spec
   - Setup virtual environment with Python 3.12
   - Created WebSocket server on localhost:8765 using modern websockets 15.0.1 API
   - Implemented full message protocol matching architecture specification

2. **Files Created**
   - `sidecar/src/server.py` - Async WebSocket server with message routing
   - `sidecar/src/protocol.py` - Message types, enums, and helper functions
   - `sidecar/requirements.txt` - All dependencies for full sidecar
   - `sidecar/pytest.ini` - Pytest configuration with asyncio mode
   - `sidecar/tests/test_server.py` - 17 tests covering protocol and server
   - `sidecar/src/__init__.py` and module `__init__.py` files

3. **Message Protocol Implemented**
   - 9 message types: START_SESSION, STOP_SESSION, UPLOAD_CONTEXT, CALIBRATE_VOICE, MANUAL_QUESTION, TRANSCRIPTION, ANSWER_CHUNK, ERROR, STATUS
   - SessionStatus enum: idle, listening, processing, calibrating
   - ConfidenceLevel enum: high, medium, low
   - Speaker enum: User, Interviewer
   - JSON serialization/deserialization with type safety

4. **Verification Passed**
   - All 17 pytest tests passing
   - Server starts and listens on port 8765 (verified with timeout test)
   - Handles invalid JSON gracefully
   - Handles unknown message types gracefully
   - Bidirectional messaging works

5. **Code Review Completed**
   - Reviewer agent identified 3 minor issues (all fixed)
   - Fixed: wait_closed() API usage in server stop method
   - Fixed: Added security comment for API key handling
   - Fixed: Made test more robust for websockets version compatibility

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| websockets version | 15.0.1 | Latest stable, modern asyncio.server API |
| Test framework | pytest-asyncio | Native async support, simple fixtures |
| Server architecture | Single async class | Simple, testable, matches architecture |

### Project Structure Updated
```
live_interview_agent/
├── sidecar/
│   ├── venv/                  # Virtual environment
│   ├── src/
│   │   ├── __init__.py
│   │   ├── server.py          # WebSocket server
│   │   ├── protocol.py        # Message types
│   │   ├── audio/             # Future: capture, vad, diarization
│   │   ├── stt/               # Future: Gemini STT
│   │   ├── context/           # Future: document parsing
│   │   ├── rag/               # Future: ChromaDB
│   │   └── llm/               # Future: Gemini LLM
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_server.py     # 17 tests
│   ├── requirements.txt
│   └── pytest.ini
└── ... (Tauri app from STORY-001)
```

### Next Steps

1. ~~**STORY-003**: WebSocket Communication - Connect React UI to Python sidecar~~ ✅ COMPLETE
2. **STORY-004**: Config Store - Implement keyring for API key storage

---

## Session: 2026-01-06 - Implementation Phase (Story 003)

### What Was Accomplished

1. **Story 003: WebSocket Communication - COMPLETE**
   - Updated `useWebSocket` hook with proper reconnection logic (fixed memory leak)
   - Added `apiKey` state to sessionStore with security warnings
   - Updated `SessionControls` to require API key before starting session
   - Updated `SettingsPanel` to save API key to store (dev mode only)
   - Added Vitest and testing-library for React tests
   - Created comprehensive test suites

2. **Files Modified**
   - `src/ui/store/sessionStore.ts` - Added apiKey state with security JSDoc
   - `src/ui/hooks/useWebSocket.ts` - Fixed reconnection memory leak with mountedRef
   - `src/ui/components/SessionControls.tsx` - Added API key validation and prod warning
   - `src/ui/components/SettingsPanel.tsx` - Integrated with store, updated messaging

3. **Files Created**
   - `src/test/setup.ts` - Vitest setup file
   - `src/ui/store/sessionStore.test.ts` - 14 store tests
   - `src/ui/hooks/useWebSocket.test.ts` - 15 protocol tests
   - `sidecar/tests/test_integration.py` - 8 bidirectional messaging integration tests

4. **Configuration Updated**
   - `package.json` - Added test scripts and testing dependencies
   - `vite.config.ts` - Added Vitest configuration
   - `tsconfig.json` - Added vite/client and vitest/globals types

5. **Tests Added**
   - **React (29 tests)**:
     - Session store: status, apiKey, transcription, answer, context files, clearSession
     - WebSocket protocol: message serialization, parsing, connection lifecycle
   - **Python (8 new integration tests, 25 total)**:
     - Full session lifecycle
     - Manual question flow
     - API key validation
     - Voice calibration flow
     - Context upload
     - Multiple clients
     - Rapid message exchange
     - Message format validation

6. **Code Review Issues Fixed**
   - Critical: Added security warnings for plaintext API key storage (dev-only)
   - Important: Fixed WebSocket reconnection memory leak with mountedRef
   - Minor: Updated misleading keychain message in SettingsPanel

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API key storage | In-memory (dev only) | Placeholder until STORY-004 keychain |
| WebSocket reconnection | 5s with mountedRef guard | Prevents memory leaks on unmount |
| Test framework | Vitest + @testing-library | Integrates with Vite, good DX |
| Security approach | Warnings + prod check | Balance dev convenience with security awareness |

### Test Summary

| Layer | Tests | Status |
|-------|-------|--------|
| React Store | 14 | ✅ Passing |
| WebSocket Protocol | 15 | ✅ Passing |
| Python Protocol | 11 | ✅ Passing |
| Python Server | 6 | ✅ Passing |
| Integration | 8 | ✅ Passing |
| **Total** | **54** | **✅ All Passing** |

### Next Steps

1. **STORY-004**: Config Store - API Keys (implement Rust keyring for secure storage)
2. **STORY-005**: Audio Capture Module (depends on STORY-003)

---

## Session: 2026-01-06 - Implementation Phase (Story 004)

### What Was Accomplished

1. **Story 004: Config Store - API Keys - COMPLETE**
   - Implemented Rust keyring integration for secure API key storage
   - Uses OS-native keychains: Windows Credential Manager, macOS Keychain, Linux Secret Service
   - Created Tauri commands: `get_api_key`, `set_api_key`, `delete_api_key`, `has_api_key`
   - Updated SettingsPanel UI with save/update/delete functionality
   - Comprehensive test coverage

2. **Files Modified**
   - `src-tauri/Cargo.toml` - Added `keyring`, `thiserror`, `serial_test` dependencies
   - `src-tauri/src/utils/mod.rs` - Added keyring module export
   - `src-tauri/src/utils/keyring.rs` - Keyring wrapper with store/retrieve/delete functions
   - `src-tauri/src/commands/config.rs` - Tauri commands for API key management
   - `src-tauri/src/lib.rs` - Registered commands in Tauri builder
   - `src/ui/components/SettingsPanel.tsx` - UI for managing API key with Tauri invoke calls
   - `src/ui/components/SettingsPanel.test.tsx` - 23 React tests
   - `src/test/setup.ts` - Added `@testing-library/jest-dom/vitest` import
   - `package.json` - Added `@testing-library/user-event`, `@testing-library/jest-dom`

3. **Tests Added**
   - **React (23 tests in SettingsPanel.test.tsx)**:
     - Initial loading state
     - API key status check on mount
     - Save/update API key flow
     - Delete API key flow
     - Error handling
     - Screen invisibility toggle
     - Form validation
   - **Rust (9 tests)**:
     - 6 serial keyring tests in `src-tauri/src/utils/keyring.rs`
     - 3 command tests in `src-tauri/src/commands/config.rs`

4. **Verification Passed**
   - React tests: 52 passed ✅
   - Rust tests: 9 passed ✅
   - Cargo check: Compiles ✅

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Keyring crate | v2+ | Stable, cross-platform OS keychain access |
| Test execution | Serial tests | Keyring tests share credential entry |
| Error handling | thiserror | Idiomatic Rust error types |
| Graceful failures | Skip in sandboxed env | CI/sandboxed environments may not have keyring access |

### Test Summary (All Stories to Date)

| Layer | Tests | Status |
|-------|-------|--------|
| React Components | 52 | ✅ Passing |
| Rust Commands | 9 | ✅ Passing |
| Python Protocol | 11 | ✅ Passing |
| Python Server | 6 | ✅ Passing |
| Integration | 8 | ✅ Passing |
| **Total** | **86** | **✅ All Passing** |

### Next Steps

1. ~~**STORY-005**: Audio Capture Module - Platform-specific audio capture~~ ✅ COMPLETE
2. **STORY-006**: Silero VAD Integration (depends on STORY-005 ✅)

---

## Session: 2026-01-06 - Implementation Phase (Story 005)

### What Was Accomplished

1. **Story 005: Audio Capture Module - COMPLETE**
   - Created platform-specific audio capture with WASAPI loopback (Windows) and sounddevice (macOS/Linux)
   - Implemented thread-safe CircularBuffer with 5-second capacity (80,000 samples at 16kHz)
   - Added async audio stream generator yielding 500ms chunks (8,000 samples)
   - Full async lifecycle management with context manager support
   - Comprehensive error handling for device access and permission errors

2. **Files Created**
   - `sidecar/src/audio/capture.py` - Main audio capture module (~486 lines)
     - `CircularBuffer` class - Thread-safe ring buffer with numpy arrays
     - `AudioCapture` class - Platform-specific capture with async interface
     - Helper functions: `samples_to_bytes`, `bytes_to_samples`, `get_platform_backend`
   - `sidecar/tests/test_audio_capture.py` - 35 tests covering all functionality
   - `sidecar/src/audio/__init__.py` - Updated with all exports

3. **Audio Configuration**
   - Sample rate: 16kHz
   - Channels: 1 (mono)
   - Format: 16-bit PCM (int16)
   - Chunk size: 500ms (8,000 samples)
   - Buffer capacity: 5 seconds (80,000 samples)

4. **Tests Added**
   - TestCircularBuffer: 8 tests (creation, read/write, overflow, thread safety, clear)
   - TestPlatformDetection: 3 tests (Windows/macOS/Linux backend selection)
   - TestAudioCaptureConstants: 7 tests (all audio format constants)
   - TestAudioCaptureClass: 7 tests (creation, state, lifecycle)
   - TestAudioStream: 4 tests (async iterator, bytes output, chunk size)
   - TestAudioCaptureErrorHandling: 2 tests (device/permission errors)
   - TestAudioChunkConversion: 2 tests (samples↔bytes)
   - TestAudioCaptureLifecycle: 2 tests (full lifecycle, context manager)

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Thread-safe buffer | `threading.Lock` | Audio callbacks run in separate threads from async code |
| Resampling method | Linear interpolation | Avoids scipy dependency; sufficient for speech |
| Polling interval | 50ms | Balance between responsiveness and CPU usage |
| Runtime imports | Platform libs at runtime | Graceful errors if platform library unavailable |

### Test Summary (All Stories to Date)

| Layer | Tests | Status |
|-------|-------|--------|
| React Components | 52 | ✅ Passing |
| Rust Commands | 9 | ✅ Passing |
| Python Audio | 35 | ✅ Passing |
| Python Protocol | 11 | ✅ Passing |
| Python Server | 6 | ✅ Passing |
| Integration | 8 | ✅ Passing |
| **Total** | **121** | **✅ All Passing** |

### Next Steps

1. **STORY-006**: Silero VAD Integration - Voice Activity Detection (depends on STORY-005 ✅)
2. **STORY-007**: Voice Calibration + Diarization (depends on STORY-006)

---

## Context for Next Session

- **Project**: Live Interview Agent - AI assistant for real-time interview support
- **Phase**: Implementation - Stories 001-005 Complete (5/20)
- **Foundation Phase**: ✅ COMPLETE (all 4 stories done)
- **Audio Pipeline Phase**: 25% (1/4 stories done)

### Key Files
- PRD: `_prism/planning/prd.md`
- Architecture: `_prism/architecture/architecture.md`
- Tasks: `_prism/tasks.md`
- Conventions: `AGENTS.md`
- Audio Capture: `sidecar/src/audio/capture.py`

### Implementation Progress
```
Phase 1: Foundation    [████████████████] 100% (4/4 stories)
Phase 2: Audio Pipeline [████████        ]  50% (2/4 stories)
Phase 3: RAG + Context  [                ]   0% (0/3 stories)
Phase 4: LLM + Answers  [                ]   0% (0/3 stories)
Phase 5: Advanced       [                ]   0% (0/3 stories)
Phase 6: Packaging      [                ]   0% (0/3 stories)
```

### Ready for Next Session
- STORY-007: Voice Calibration + Diarization (unblocked, depends on STORY-006 ✅)
- Continue Phase 2: Audio Pipeline

---

## Session: 2026-01-06 - Implementation Phase (Story 006)

### What Was Accomplished

1. **Story 006: Silero VAD Integration - COMPLETE**
   - Integrated Silero VAD v4 model via `silero_vad` package
   - Implemented VADProcessor class with 512-sample sliding window (32ms at 16kHz)
   - Speech probability threshold: 0.5
   - Smoothing: requires 3 consecutive frames for speech start/end
   - Thread-safe operation with threading.Lock
   - SpeechSegment dataclass with audio, start_time, end_time, confidence fields

2. **Files Created**
   - `sidecar/src/audio/vad.py` - VADProcessor class (~300 lines)
     - `SpeechSegment` dataclass
     - `VADModelError` exception
     - `DEFAULT_VAD_THRESHOLD`, `DEFAULT_VAD_WINDOW_SIZE` constants
   - `sidecar/tests/test_vad.py` - 29 tests covering all functionality

3. **Files Modified**
   - `sidecar/src/audio/__init__.py` - Added VAD module exports

4. **Tests Added (29 new tests)**
   - TestSpeechSegmentDataclass: 3 tests (structure, creation, types)
   - TestVADProcessorInitialization: 5 tests (defaults, model loading, sample rate)
   - TestVADThresholdConfiguration: 3 tests (validation, range)
   - TestVADWindowSize: 2 tests (512 samples = 32ms)
   - TestVADProcessChunk: 5 tests (returns, silence filtering, speech detection, times, confidence)
   - TestVADEmptyInput: 2 tests (empty bytes, short audio)
   - TestVADReset: 2 tests (state clearing, session reset)
   - TestVADContinuousSpeech: 1 test (multi-chunk tracking)
   - TestVADIntegrationWithAudioModule: 2 tests (sample rate, exports)
   - TestVADConstants: 2 tests (threshold, window size)
   - TestVADModelLoading: 2 tests (error handling)

5. **Code Review Completed**
   - Reviewer approved with confidence 88%
   - Fixed: Removed redundant SAMPLE_RATE constant, now imports from audio.capture

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Class name | VADProcessor | Follows established pattern in codebase |
| Async interface | process_chunk is async | Consistency with audio pipeline |
| Model loading | On instantiation | Fail-fast if model unavailable |
| SAMPLE_RATE | Import from capture.py | Single source of truth |

### Test Summary (All Stories to Date)

| Layer | Tests | Status |
|-------|-------|--------|
| React Components | 52 | ✅ Passing |
| Rust Commands | 9 | ✅ Passing |
| Python VAD | 29 | ✅ Passing |
| Python Audio | 35 | ✅ Passing |
| Python Protocol | 11 | ✅ Passing |
| Python Server | 6 | ✅ Passing |
| Integration | 8 | ✅ Passing |
| **Total** | **150** | **✅ All Passing** |

### Next Steps

1. **STORY-007**: Voice Calibration + Diarization (depends on STORY-006 ✅)
2. **STORY-008**: Gemini STT Integration (depends on STORY-006 ✅, STORY-004 ✅)

---

## Context for Next Session

- **Project**: Live Interview Agent - AI assistant for real-time interview support
- **Phase**: Implementation - Stories 001-006 Complete (6/20)
- **Foundation Phase**: ✅ COMPLETE (all 4 stories done)
- **Audio Pipeline Phase**: 50% (2/4 stories done)

### Key Files
- PRD: `_prism/planning/prd.md`
- Architecture: `_prism/architecture/architecture.md`
- Tasks: `_prism/tasks.md`
- Conventions: `AGENTS.md`
- VAD Module: `sidecar/src/audio/vad.py`

### Implementation Progress
```
Phase 1: Foundation    [████████████████] 100% (4/4 stories)
Phase 2: Audio Pipeline [████████        ]  50% (2/4 stories)
Phase 3: RAG + Context  [                ]   0% (0/3 stories)
Phase 4: LLM + Answers  [                ]   0% (0/3 stories)
Phase 5: Advanced       [                ]   0% (0/3 stories)
Phase 6: Packaging      [                ]   0% (0/3 stories)
```

### Ready for Next Session
- STORY-007: Voice Calibration + Diarization (unblocked, depends on STORY-006 ✅)
- STORY-008: Gemini STT Integration (unblocked, depends on STORY-006 ✅, STORY-004 ✅)
- Continue Phase 2: Audio Pipeline

## Session: 2026-01-06 - Implementation Phase (Story 007)

### What Was Accomplished

1. **Story 007: Voice Calibration + Diarization - COMPLETE**
   - Implemented `SpeakerRecognizer` class using SpeechBrain ECAPA-TDNN
   - Created `CalibrationModal` UI with 5-second countdown and audio capture
   - Implemented client-side audio capture (16kHz mono int16) using AudioContext
   - Handled `CALIBRATE_VOICE` message in Python sidecar
   - Fixed `speechbrain` compatibility issue by downgrading `huggingface-hub` to 0.24.7

2. **Files Created/Modified**
   - `sidecar/src/audio/diarization.py` - Speaker recognition logic
   - `sidecar/tests/test_diarization.py` - Unit tests
   - `sidecar/tests/test_server_calibration.py` - Integration tests
   - `src/ui/components/CalibrationModal.tsx` - React UI for calibration
   - `src/ui/components/CalibrationModal.test.tsx` - UI tests
   - `sidecar/requirements.txt` - Added speechbrain, torchaudio, huggingface-hub constraint

3. **Key Decisions**
   - **Audio Capture**: UI captures mic for calibration (guarantees User voice), while Python captures system audio for main session.
   - **Compatibility**: Pinned `huggingface-hub<0.25.0` to support `speechbrain 1.0.3`.
   - **Model**: Used `speechbrain/spkrec-ecapa-voxceleb`.

### Next Steps

1. **STORY-008**: Gemini STT Integration - Implement Google Gemini STT
2. **STORY-009**: Context Manager - Document parsing
