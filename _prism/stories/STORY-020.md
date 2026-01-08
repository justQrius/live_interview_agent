# Story 020: End-to-End System Verification (Phase 1 + 2)

## Description
Perform comprehensive end-to-end (E2E) testing of the entire Live Interview Agent system, validating both Phase 1 (Core) and Phase 2 (Optimization) features. This ensures the system meets all functional and non-functional requirements before final release.

## Rationale
With the addition of Phase 2 features (multi-provider, browser VAD, optimizations), the testing scope has expanded significantly beyond the original MVP requirements. We need to verify that all components work together seamlessly and meet the stricter performance targets.

## Scope

### Phase 1 Verification (MVP)
1.  **Core Stability**: 2-hour session stability check (no crashes/memory leaks).
2.  **Resource Usage**: RAM usage < 500MB, CPU usage < 30% during active use.
3.  **Basic Functionality**: Audio capture -> Transcription -> Answer Generation -> Display.
4.  **Security**: API keys stored securely in OS keychain.
5.  **Screen Invisibility**: App is invisible to screen sharing tools (manual check).

### Phase 2 Verification (Optimizations)
1.  **Latency**:
    -   Cold start time < 1s.
    -   E2E latency (P50) < 1.5s (using fast providers like Groq).
2.  **Multi-Provider**:
    -   Verify STT switching (Gemini <-> Groq <-> Deepgram).
    -   Verify LLM switching (Gemini <-> OpenAI <-> Anthropic).
    -   Verify persistence of provider preferences.
3.  **Browser VAD**:
    -   Verify silence filtering reduces WebSocket traffic (check logs/network).
    -   Verify offline asset loading works.

## Acceptance Criteria
-   [ ] **Stability**: System runs for >1 hour with continuous audio input without crashing.
-   **Performance**:
    -   [ ] App launches to "Ready" state in < 1 second (after initial setup).
    -   [ ] Transcription appears in < 500ms (using Groq).
    -   [ ] Answer streaming starts in < 1.5s (using fast LLM).
-   **Functionality**:
    -   [ ] Can switch STT providers and see results continue.
    -   [ ] Can switch LLM providers and see answers continue.
    -   [ ] Settings persist across restarts.
-   **Resource Efficiency**:
    -   [ ] Idle CPU usage < 5%.
    -   [ ] Active CPU usage < 30% (Python + Renderer).

## Tasks
1.  [ ] **Automated Integration Test**: Update `sidecar/tests/test_full_pipeline.py` or create `test_e2e_scenarios.py` to simulate a full session with provider switching.
2.  [ ] **Latency Benchmark**: Create a script or test mode to measure timestamp deltas (Audio Input -> STT Result -> LLM First Token).
3.  [ ] **Manual Verification Protocol**: Perform a structured manual test:
    -   Launch app.
    -   Configure keys for all providers.
    -   Select Groq (STT) + OpenAI (LLM).
    -   Start session.
    -   Speak a test question ("Tell me about Python decorators").
    -   Verify transcription speed and accuracy.
    -   Verify answer quality and speed.
    -   Stop session.
    -   Change providers to Deepgram + Anthropic.
    -   Repeat.
4.  [ ] **Report**: Document findings in `_prism/verification/e2e_report.md`.

## Deliverables
-   Updated test suite.
-   Verification report with pass/fail status for each criteria.
