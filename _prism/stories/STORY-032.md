# Story 032: Provider Configuration UI & Storage

## Description
Implement the UI and backend storage for managing multiple AI provider API keys and preferences. This allows users to configure Groq, Deepgram, OpenAI, and Anthropic keys securely and select their preferred providers.

## Rationale
To enable the multi-provider features built in previous stories, users need a way to input their API keys securely and choose which provider to use. The current config system only supports a single "Gemini" key.

## Requirements

### Backend (Rust)
1.  **Refactor Keyring**: Update `src-tauri/src/utils/keyring.rs` to support dynamic key names (e.g., "gemini_api_key", "openai_api_key").
2.  **Update Commands**: Update `src-tauri/src/commands/config.rs` to accept a `provider` argument.
    -   `get_api_key(provider: String) -> Result<String, String>`
    -   `set_api_key(provider: String, key: String) -> Result<(), String>`
    -   `delete_api_key(provider: String) -> Result<(), String>`
    -   `has_api_key(provider: String) -> bool` (Update return type if needed)

### Frontend (React)
1.  **Update API**: Update `src/ui/store/configStore.ts` (or equivalent) to call the updated Tauri commands.
2.  **ProviderSettings Component**: Create `src/ui/components/ProviderSettings.tsx`.
    -   List all providers (Gemini, Groq, Deepgram, OpenAI, Anthropic).
    -   Input field for each API key (masked).
    -   "Save" button for each (or global).
    -   Validation status (check if key exists).
3.  **Preferences**: Add dropdowns for:
    -   **Preferred STT Provider**: [Auto, Groq, Deepgram, OpenAI, Gemini]
    -   **Preferred LLM Provider**: [Auto, OpenAI, Anthropic, Gemini]
4.  **Session Store**: Update `sessionStore.ts` to persist these preferences (localStorage is fine for preferences, Keychain for keys).
5.  **Integration**: Add `ProviderSettings` to the `SettingsPanel`.

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Data Flow
UI -> Tauri Command (`set_api_key("openai", "sk-...")`) -> Rust Keyring -> OS Keychain

## Acceptance Criteria
- [ ] Rust backend supports storing/retrieving keys for any provider.
- [ ] `ProviderSettings` UI allows entering keys for all supported providers.
- [ ] Preferences (STT/LLM choice) are saved and persist across reloads.
- [ ] Keys are stored securely in OS keychain.
- [ ] Backward compatibility: Existing Gemini key is preserved (migrated or accessed via "gemini" provider name).

## Tasks
1.  [ ] Refactor `src-tauri/src/utils/keyring.rs`.
2.  [ ] Update `src-tauri/src/commands/config.rs`.
3.  [ ] Update React Tauri interface types.
4.  [ ] Create `src/ui/components/ProviderSettings.tsx`.
5.  [ ] Integrate into `SettingsPanel.tsx`.
6.  [ ] Update `sessionStore.ts` for preferences.
