# Story 021: Model Pre-warming Infrastructure

## Description
Implement a model pre-warming mechanism to load heavy ML models (Silero VAD, ECAPA-TDNN) at application startup instead of session start. This will significantly reduce the "cold start" latency when a user begins their first interview session.

## Rationale
Currently, models are loaded lazily when the session starts, causing a 2-5 second delay. By loading them in the background during app startup, we can achieve near-instant session starts (<1s).

## Requirements
1. **ModelWarmer Module**: Create `sidecar/src/warmup.py` implementing the `ModelWarmer` singleton class.
2. **Background Loading**: Models must load in a background thread to avoid blocking the main application loop.
3. **Singleton Pattern**: Ensure only one instance of models exists in memory.
4. **Integration**: Update `server.py` to initialize pre-warming on startup and use pre-warmed models during session initialization.
5. **Error Handling**: Gracefully handle model loading failures and report status.

## Architecture
Reference: `_prism/architecture/architecture-phase2.md` (Section 3)

### Class Structure
```python
@dataclass
class PrewarmedModels:
    vad_processor: Optional[object]
    speaker_recognizer: Optional[object]
    is_ready: bool
    error: Optional[str]

class ModelWarmer:
    # Singleton implementation
    def start_warming(self) -> None: ...
    def wait_for_ready(self, timeout: float) -> bool: ...
```

## Acceptance Criteria
- [x] `sidecar/src/warmup.py` created and implemented.
- [x] `server.py` updated to start warming on startup.
- [x] `server.py` updated to use pre-warmed models in `SessionManager`.
- [x] Unit tests for `ModelWarmer` created (`sidecar/tests/test_warmup.py`).
- [x] Session start time is < 1 second.
- [x] Application startup is not blocked by model loading.

## Tasks
1. [x] Create `sidecar/src/warmup.py`
2. [x] Create unit tests `sidecar/tests/test_warmup.py`
3. [x] Refactor `server.py` to integrate `ModelWarmer`
4. [x] Verify performance improvement
