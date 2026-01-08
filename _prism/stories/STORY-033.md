# Story 033: Server Integration & End-to-End Testing

## Description
Final integration of Phase 2 features. Update the Python sidecar server to utilize the `ProviderFactory` and `ModelWarmer`, update the WebSocket protocol to transmit multi-provider configuration, and perform end-to-end testing of the complete system.

## Rationale
We have built all the individual components (Providers, Factory, Warmer, UI, Config), but they are not yet fully wired together in the main execution loop. This story connects the dots.

## Requirements

### Backend (Python)
1.  **Server Update**: Update `sidecar/src/server.py` to:
    -   Initialize `ModelWarmer` on startup (already done in Story 021, verifying integration).
    -   Initialize `ProviderFactory` with config received from client.
    -   Handle the updated `START_SESSION` payload (containing all API keys and preferences).
    -   Use `ProviderFactory.get_stt_provider()` and `get_llm_provider()` to dynamically select providers.
2.  **Protocol Update**: Verify `sidecar/src/protocol.py` (if separate) or message handling logic supports the new `START_SESSION` structure.

### Frontend (React)
1.  **WebSocket Update**: Update `src/ui/hooks/useWebSocket.ts` to send the full configuration payload (all keys + preferences) when starting a session. Currently, it likely only sends `apiKey`.

### Testing
1.  **Integration Tests**: Update `sidecar/tests/test_integration.py` to test the full flow with different providers.
2.  **E2E Verification**: Manual or automated check that switching providers actually changes the backend behavior (e.g., check logs for "Using Groq STT").

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Data Flow
1.  User clicks "Start Session".
2.  Frontend retrieves all keys + prefs from `sessionStore` / `localStorage`.
3.  Frontend sends `START_SESSION` with `{ apiKeys: {...}, preferences: {...} }`.
4.  Backend `SidecarServer` creates `ProviderConfig`.
5.  Backend initializes `ProviderFactory` with config.
6.  Backend loop uses `factory.get_stt_provider()` for transcription.
7.  Backend loop uses `factory.get_llm_provider()` for answers.

## Acceptance Criteria
- [ ] `START_SESSION` message includes all configured API keys and preferences.
- [ ] Python server correctly parses this configuration.
- [ ] Server uses the selected provider (e.g., Groq if preferred, Gemini if default).
- [ ] Fallback logic works (if primary fails, secondary is used - *verified via unit tests, but good to have integration check*).
- [ ] End-to-end latency meets targets (check logs/metrics).

## Tasks
1.  [ ] Update `src/ui/hooks/useWebSocket.ts`.
2.  [ ] Update `sidecar/src/server.py`.
3.  [ ] Update `sidecar/src/protocol.py` (if applicable).
4.  [ ] Update/Add integration tests in `sidecar/tests/`.
5.  [ ] Run full system check.
