# Story 031: Browser VAD Integration

## Description
Integrate `@ricky0123/vad-react` into the React frontend to perform Voice Activity Detection (VAD) in the browser. This allows filtering silence from microphone input before transmitting audio to the backend, reducing WebSocket traffic and server load.

## Rationale
Sending continuous audio streams (including silence) consumes bandwidth and CPU on the backend. By filtering silence at the source (Browser), we significantly improve efficiency and reduce latency for the relevant speech segments.

## Requirements
1.  **Dependencies**: Install `@ricky0123/vad-react` and `onnxruntime-web`.
2.  **Assets**: Bundle ONNX VAD model and WASM runtime files in `public/assets/vad/` to ensure offline capability.
3.  **Hook**: Implement `src/ui/hooks/useVADFilter.ts` wrapper hook.
    -   Expose `start`, `stop`, `listening`, `userSpeaking`.
    -   Handle `onSpeechStart` and `onSpeechEnd` callbacks.
4.  **Security**: Update Tauri CSP to allow `wasm-eval`.
5.  **Integration**: (Part of Story 033, but prep here) The hook should be ready to replace or augment the current audio source.

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Component: `useVADFilter`
```typescript
import { useMicVAD } from "@ricky0123/vad-react"

export const useVADFilter = (options: VADFilterOptions) => {
  // Implementation wrapping useMicVAD
  // configured to use local assets
}
```

## Acceptance Criteria
- [ ] Dependencies installed.
- [ ] VAD assets (ONNX/WASM) present in `public/assets/vad/`.
- [ ] `useVADFilter` hook implemented and compiling.
- [ ] Tauri CSP updated.
- [ ] Basic test/demo component confirms VAD triggers (optional but good for verification).

## Tasks
1. [ ] Install npm packages.
2. [ ] Copy `silero_vad.onnx` and `ort-wasm-simd.wasm` (etc) to `public/`.
3. [ ] Create `src/ui/hooks/useVADFilter.ts`.
4. [ ] Update `src-tauri/tauri.conf.json`.
5. [ ] Verify build.
