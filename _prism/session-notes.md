# Session Notes - Live Interview Agent

## Session: 2026-01-08 - Critical Bug Fix: Windows Keyring Failure

### COMPLETED TODAY

**Bug Fix #1: Start button disabled after API key configuration**
- Root cause: API key state not syncing when keys saved/deleted in ProviderSettings
- Implemented event-based synchronization using `apiKeyChanged` custom event
- Fixed SessionControls to use `hasPrimaryKey` instead of undefined `apiKey` variable
- Commit: `07d1ffe` - "fix: start button now enables immediately after API key save/delete"

**Bug Fix #2: Windows Credential Manager not persisting API keys** ⭐ CRITICAL
- Root cause: `keyring` crate reports success but Windows Credential Manager is intermittent
- Discovered via debug panel showing `exists: false` immediately after `Save successful`
- Terminal logs showed: "OS keyring verification successful!" but then retrieve failed
- **Final solution**: Store to fallback FIRST (guaranteed), then OS keyring (best-effort)
- Storage location: `%APPDATA%\live_interview_agent\api_keys.json`
- Commits:
  - `768540e` - Added debug panel and comprehensive logging
  - `aa359e5` - Implemented fallback storage mechanism
  - `ff3542d`, `6d2c7b0` - Enhanced logging to diagnose the issue
  - `81b455b` - **FIX**: Fallback-first strategy (reliable storage)

### TECHNICAL DETAILS

**Event Flow:**
1. User saves/deletes API key in ProviderSettings
2. `window.dispatchEvent(new CustomEvent('apiKeyChanged', { detail: { provider } }))`
3. SettingsPanel listens → re-syncs API key to store
4. SessionControls listens → re-checks `hasPrimaryKey` state
5. Button enables/disables correctly ✅

**Files Changed:**
- `src/ui/components/ProviderSettings.tsx` - Dispatch events on save/delete
- `src/ui/components/SettingsPanel.tsx` - Listen and re-sync API key
- `src/ui/components/SessionControls.tsx` - Listen and re-check key existence + fix button logic

---

## Session: 2026-01-07 - Stories 026/027/029/030/031 Complete

### COMPLETED TODAY

1. **Story 026: Groq STT Provider - COMPLETE**
   - Implemented `GroqSTTProvider` (whisper-large-v3, ~300ms latency)

2. **Story 027: Deepgram STT Provider - COMPLETE**
   - Implemented `DeepgramSTTProvider` (nova-2)

3. **Story 029: OpenAI LLM Provider - COMPLETE**
   - Implemented `OpenAILLMProvider` (gpt-4o)

4. **Story 030: Anthropic LLM Provider - COMPLETE**
   - Implemented `AnthropicLLMProvider` (claude-3-5-sonnet)

5. **Story 031: Browser VAD Integration - COMPLETE**
   - Installed `@ricky0123/vad-react` and `onnxruntime-web`
   - Copied assets to `public/assets/vad/` (model + runtime)
   - Created `src/ui/hooks/useVADFilter.ts`
   - Updated `tauri.conf.json` CSP for WASM support
   - Created passing unit tests for the hook

### KEY IMPLEMENTATION DETAILS

**Browser VAD:**
- Uses local assets in `public/assets/vad/` to ensure offline capability (and reliable loading in Tauri).
- Configured to filter non-speech frames in the browser.
- Actual WebSocket integration (sending only speech) is deferred to **Story 033** (Integration), as it requires modifying the main loop.

### CURRENT STATE

- **Phase 1**: 19/20 stories complete (STORY-020 E2E Testing remains)
- **Phase 2**: 10/13 stories complete
  - ... (All providers done)
  - STORY-031 ✅ Browser VAD Integration

### NEXT STEPS

1. **STORY-032**: Provider Configuration UI
   - Add UI components to select providers and enter API keys.
   - Update `sessionStore` to persist these preferences.

2. **STORY-033**: Server Integration + E2E Testing
   - Stitch everything together.
   - Update `server.py` to use `ProviderFactory`.
   - Update `useWebSocket.ts` to send provider config on start.
   - Implement the VAD filtering logic in the audio capture loop (or switch to browser audio source).
