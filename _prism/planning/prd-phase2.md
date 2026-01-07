# PRD: Live Interview Agent - Phase 2 Optimizations

## Problem Statement

The MVP (Phase 1) of Live Interview Agent is functional but has performance gaps compared to competitors like Pluely:

**Current Bottlenecks:**
- **Cold Start Latency**: ML models (Silero VAD, ECAPA-TDNN) load at session start, adding 2-5 seconds delay
- **Single Provider Lock-in**: Gemini-only implementation limits flexibility and creates rate limit risks (15 req/min free tier)
- **Sequential Pipeline**: Audio processing is serial (VAD → NoiseReduce → STT), adding cumulative latency
- **WebSocket Overhead**: All audio flows through Python sidecar, even silence (~20ms IPC overhead per chunk)

**Competitive Analysis (Pluely):**

| Aspect | Pluely | Our MVP | Gap |
|--------|--------|---------|-----|
| Bundle Size | ~10MB | ~150-300MB | PyTorch overhead |
| Startup Time | <100ms | 2-5s | Model loading |
| VAD Location | Browser (ONNX) | Python (PyTorch) | IPC overhead |
| STT Providers | 3 (Whisper, Groq, Deepgram) | 1 (Gemini) | Flexibility |
| E2E Latency | ~1.5s | ~1.85s | ~350ms gap |

**Our Unique Advantages to Preserve:**
- ✅ RAG Context (Pluely lacks this)
- ✅ Speaker Diarization (Pluely lacks this)

## Goals

### Primary Goals
- Reduce end-to-end latency from ~1.85s to <1.5s (P50)
- Reduce cold start time from 2-5s to <1s
- Add multi-provider support for STT (Groq, Deepgram, OpenAI) and LLM (OpenAI, Anthropic)
- Implement browser-side VAD pre-filter to reduce WebSocket traffic by ~70%

### Secondary Goals
- Improve rate limit resilience through provider fallback
- Enable user choice of preferred providers
- Reduce CPU usage during silence periods

## Non-Goals

- Rust audio capture rewrite (deferred to Phase 3)
- Mobile application support
- Local/offline LLM support (Ollama)
- Real-time provider cost tracking
- Answer caching/history persistence

## User Personas

*Same as Phase 1 PRD - no changes to target users*

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-P2-1 | Model Pre-warming | Must Have | Silero VAD and ECAPA-TDNN models load within 3 seconds of app startup, before session starts. First session has no additional model loading delay. |
| FR-P2-2 | Provider Abstraction Layer | Must Have | STT and LLM modules implement abstract interfaces. New providers can be added by implementing interface without modifying server.py. |
| FR-P2-3 | Groq STT Provider | Must Have | Groq Whisper API integrated as STT option. Transcription latency <400ms. Supports same audio format as Gemini (16kHz PCM). |
| FR-P2-4 | Deepgram STT Provider | Must Have | Deepgram Nova-2 API integrated as STT option. Supports streaming transcription. |
| FR-P2-5 | OpenAI Whisper STT Provider | Must Have | OpenAI Whisper API integrated as STT option. Supports same audio format as others. |
| FR-P2-6 | OpenAI LLM Provider | Must Have | OpenAI GPT-4o/GPT-4o-mini integrated as LLM option. Streaming responses. Same prompt template compatibility. |
| FR-P2-7 | Anthropic LLM Provider | Must Have | Anthropic Claude 3.5 Sonnet integrated as LLM option. Streaming responses. Same prompt template compatibility. |
| FR-P2-8 | Browser-side VAD Pre-filter | Must Have | @ricky0123/vad-react integrated in React UI. Only speech segments sent to Python sidecar. Reduces WebSocket messages by >60%. |
| FR-P2-9 | Provider Configuration UI | Should Have | Settings panel allows selection of STT and LLM providers. API keys stored per-provider in OS keychain. |
| FR-P2-10 | Provider Fallback | Should Have | If primary provider fails (rate limit, error), automatically retry with fallback provider. User notified of fallback. |
| FR-P2-11 | Parallel Audio Processing | Should Have | VAD and noise reduction run concurrently where possible. Reduces pipeline latency by ~15ms. |

## Non-Functional Requirements

| ID | Requirement | Priority | Metric | Rationale |
|----|-------------|----------|--------|-----------|
| NFR-P2-1 | Cold Start Time | Must Have | <1 second from app launch to "Ready" state | Eliminates model loading delay at session start |
| NFR-P2-2 | E2E Latency (P50) | Must Have | <1.5 seconds | Matches competitor performance |
| NFR-P2-3 | E2E Latency (P95) | Must Have | <3 seconds | Maintains reliability under load |
| NFR-P2-4 | Provider Switch Time | Should Have | <100ms | Seamless fallback experience |
| NFR-P2-5 | Browser VAD Overhead | Should Have | <5ms per 30ms frame | Minimal UI thread impact |
| NFR-P2-6 | WebSocket Traffic Reduction | Should Have | >60% reduction during silence | Reduces IPC overhead |

## Success Metrics

### Primary Metrics
- **E2E Latency (P50)**: <1.5 seconds (down from ~1.85s)
- **Cold Start Time**: <1 second (down from 2-5s)
- **Provider Availability**: 99.9% uptime with fallback (up from single-provider risk)

### Secondary Metrics
- **WebSocket Messages**: 60% reduction during silence periods
- **CPU Usage (Silence)**: <3% (down from ~5%)
- **Provider Switch Success Rate**: >95% on first fallback attempt

## Dependencies

### New External Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| @ricky0123/vad-react | npm package | Browser-side VAD |
| onnxruntime-web | npm package | ONNX runtime for browser VAD |
| groq | Python package | Groq API client |
| deepgram-sdk | Python package | Deepgram API client |
| openai | Python package | OpenAI API client |
| anthropic | Python package | Anthropic API client |

### API Key Requirements

| Provider | Key Name | Rate Limits (Free Tier) |
|----------|----------|------------------------|
| Groq | GROQ_API_KEY | 30 req/min |
| Deepgram | DEEPGRAM_API_KEY | 100 hrs/month |
| OpenAI | OPENAI_API_KEY | Varies by plan |
| Anthropic | ANTHROPIC_API_KEY | Varies by plan |

## Open Questions

- [x] Which STT providers to support? → All: Groq, Deepgram, OpenAI
- [x] Which LLM providers to support? → OpenAI, Anthropic
- [x] Browser VAD priority? → Phase 2 (immediate)
- [ ] Default provider order for fallback? (Suggest: Groq → Deepgram → OpenAI → Gemini for STT)
- [ ] Should provider selection persist across sessions? (Suggest: Yes, save in config)
- [ ] Timeout threshold before fallback? (Suggest: 5 seconds)

## Timeline

**Estimated Duration**: 2 weeks (10 working days)

| Week | Focus | Stories |
|------|-------|---------|
| Week 1 | Foundation + Providers | STORY-021 to STORY-027 |
| Week 2 | Browser VAD + Integration | STORY-028 to STORY-033 |

---

**Document Status**: Approved
**Created**: 2026-01-06
**Last Updated**: 2026-01-06
**Owner**: Product (AI Agent)
**Approved By**: User

**Next Step**: Proceed to Phase 2 Architecture implementation.
