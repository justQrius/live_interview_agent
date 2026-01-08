# Project Learnings

This document captures learnings specific to the Live Interview Agent project.

## Technical Learnings

### API Key Storage (Windows)

**Critical Issue**: Windows Credential Manager + keyring crate is unreliable

**Symptoms**:
- `set_password()` returns Ok (success)
- Immediately calling `get_password()` fails with NoEntry error
- Verification immediately after save shows key doesn't exist

**Root Cause**:
- Windows Credential Manager may not persist credentials immediately
- Race conditions or caching issues in the keyring crate on Windows
- OS keyring returns success without actually committing to storage

**Solution - Fallback Strategy**:
```rust
// Store to guaranteed storage FIRST, then try best-effort secondary
pub fn store_api_key(key_name: &str, key: &str) -> Result<(), KeyringError> {
    // 1. Always store to JSON fallback (guaranteed to work)
    crate::utils::storage_fallback::store_key(key_name, key)?;
    
    // 2. Attempt OS keyring (nice to have, not critical)
    let entry = get_entry(key_name)?;
    match entry.set_password(key) {
        Ok(()) => Ok(()),
        Err(_) => Ok(()), // Already saved to fallback, so this is fine
    }
}
```

**Storage Location**: `%APPDATA%\live_interview_agent\api_keys.json`

**Date Discovered**: 2026-01-08
**Confidence**: 100%

---

### Audio Capture

**Note**: App captures microphone input, not system audio

For testing with YouTube videos:
- Requires virtual audio cable software (VB-Audio Virtual Cable, VoiceMeeter)
- Route YouTube output to virtual cable input
- Set app to listen to virtual cable as microphone source

**Date**: 2026-01-08
**Confidence**: 100%

---

### Speech-to-Text

<!-- Document learnings about STT accuracy, latency, provider quirks -->

---

### RAG Implementation

<!-- Document learnings about embedding, retrieval, context size -->

---

### Performance Optimization

**Debugging Tauri Desktop Apps**:
- Browser DevTools not easily accessible (F12 doesn't work like in browser)
- Solution: Combined logging approach
  - Rust `eprintln!()` logs appear in terminal where `npm run tauri dev` was executed
  - In-app debug panel overlay for React component state
  - Useful for debugging API key checks, WebSocket connections, audio capture

**Date**: 2026-01-08
**Confidence**: 95%

---

## Process Learnings

### What Worked Well

1. **Event-based state synchronization**
   - Used custom events to notify components when API keys change
   - Pattern: `window.dispatchEvent(new CustomEvent('apiKeyChanged', { detail: { provider } }))`
   - Avoids complex store subscription management
   - Explicit and traceable

2. **Multi-channel debugging approach**
   - Terminal logs for Rust backend
   - In-app debug panel for React frontend
   - Visual status indicators in UI (API Key Status line)
   - Faster diagnosis than guessing

### What To Improve

1. **Test keyring persistence immediately after save**
   - Don't assume `set_password()` means persistence succeeded
   - Always verify with a `get_password()` call

2. **Assume OS keyring can fail**
   - Never rely solely on OS-specific credential storage
   - Implement fallback from the start, not as a patch

---

## Patterns Discovered

### Reusable Patterns

**Pattern 1: Fallback-First Storage**
```rust
// Primary: Guaranteed storage (JSON file, encrypted)
// Secondary: Best-effort storage (OS keyring, more secure but flaky)
pub fn store_sensitive_data(key: &str, value: &str) -> Result<(), Error> {
    // Always succeed with primary
    primary_storage.store(key, value)?;
    
    // Try secondary, ignore failures
    if let Ok(entry) = get_os_entry(key) {
        let _ = entry.set_password(value);
    }
    Ok(())
}
```

**Pattern 2: Event-Based Cross-Component Communication**
```typescript
// Provider: Dispatch event after mutation
const handleSave = async () => {
    await invoke('set_api_key', { provider, key });
    window.dispatchEvent(new CustomEvent('apiKeyChanged', { detail: { provider } }));
};

// Consumer: Listen for event to refresh state
useEffect(() => {
    const handleApiKeyChange = () => {
        syncKeyFromBackend();
    };
    window.addEventListener('apiKeyChanged', handleApiKeyChange);
    return () => window.removeEventListener('apiKeyChanged', handleApiKeyChange);
}, []);
```

**Pattern 3: In-App Debug Panel for Desktop Apps**
```typescript
// Create floating console overlay
// Intercepts console.log/error/warn calls
// Displays recent logs in UI
// Essential because desktop apps don't have browser DevTools
```

---

### Anti-Patterns to Avoid

1. **DON'T trust OS keyring as single source of truth**
   - Always implement fallback storage
   - Test on Windows specifically (macOS/Linux keyring more reliable)

2. **DON'T assume set_password() means persistence succeeded**
   - Verify with get_password() immediately after
   - Check if returned value matches what was stored

3. **DON'T rely on browser DevTools for Tauri apps**
   - They don't work the same way
   - Implement in-app debugging from the start

4. **DON'T make users guess why a button is disabled**
   - Show status: "API Key Status: ✅ Found" or "❌ Not configured"
   - Display provider being checked

---

*Updated: 2026-01-08*
