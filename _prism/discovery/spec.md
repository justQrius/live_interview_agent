# Live Interview Agent - Specification Document

**Version**: 1.0
**Date**: 2026-01-05
**Status**: Draft - Pending Approval

---

## 1. Problem Statement

### The Problem
Job seekers can use AI assistants to research and prepare for interviews, but they must memorize answers, which is inefficient and stressful. During live interviews, candidates often forget key points, struggle to articulate prepared responses, or fail to connect their experience to specific questions.

### Why It Matters
- Interview anxiety causes candidates to underperform despite thorough preparation
- Memorization is unreliable under pressure
- Real-time assistance could level the playing field
- Prepared context (resume, job details, Q&As) goes underutilized during actual interviews

### The Solution
An AI-powered desktop agent that listens to live job interviews in real-time, understands the context, and surfaces intelligent, relevant answers as text for the candidate to read and verbalize.

---

## 2. User Personas

### Primary Persona: Tech Job Seeker
- **Industry**: Technology (software engineering, data science, product, design, etc.)
- **Experience Level**: Any (junior to senior)
- **Technical Proficiency**: Varies (both technical and non-technical roles)
- **Interview Format**: Phone calls and video calls (Zoom, Teams, Google Meet)
- **Key Need**: Easy setup, minimal technical configuration required

### User Characteristics
- Comfortable with basic desktop applications
- Has prepared interview materials (resume, job description, research)
- Conducts interviews via computer audio (phone or video call)
- May be sharing screen during technical interviews

---

## 3. Discovery Q&A Summary

| Topic | User Input |
|-------|------------|
| **Problem** | Need real-time AI assistance during interviews; memorization is inefficient |
| **Target Users** | Tech industry job seekers, any level, easy setup required |
| **Interview Formats** | Phone and video calls only (Zoom, Teams, Meet, phone) |
| **Audio Approach** | Listen to system audio/speaker (platform-agnostic) |
| **Response Time** | Few seconds acceptable |
| **Accuracy** | High - must leverage all context effectively |
| **Tech Stack** | Modern, battle-tested, best fit for requirements |
| **LLM (MVP)** | Gemini models |
| **STT (MVP)** | Gemini speech-to-text |
| **Budget** | API costs acceptable |
| **Privacy** | LLM APIs okay; everything else local |
| **Screen Share** | Must be invisible/undetectable |

---

## 4. Edge Cases & Handling

| ID | Edge Case | Solution |
|----|-----------|----------|
| EC-1 | Poor audio quality/noise/accents | Noise reduction preprocessing, confidence indicators, manual input fallback |
| EC-2 | Panel interviews (3+ speakers) | Voice calibration at start; classify as "user" vs "everyone else" |
| EC-3 | Rapid follow-up questions | Interrupt-and-replace model; streaming responses; visual queue indicator |
| EC-4 | Off-topic/unexpected questions | Graceful degradation; RAG + LLM general knowledge; confidence badges |
| EC-5 | Long silence | VAD-based processing; "Listening..." indicator; low resource mode |
| EC-6 | Context overload | Size limits per content type; efficient RAG chunking; upload warnings |
| EC-7 | Network/API failure | Retry logic; response caching; graceful UI error states |
| EC-8 | Detecting user vs interviewer | Voice calibration; speaker diarization; never answer own speech |
| EC-9 | Statements vs questions | LLM evaluates if response needed; priority styling for "maybe relevant" |
| EC-10 | Screen share invisibility | OS-level capture exclusion APIs (Windows WDA, macOS sharingType) |
| EC-11 | Session management | Manual start/stop; auto-pause after 5min silence; persist through disconnections |
| EC-12 | Interview language | English only for MVP |

---

## 5. Requirements

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | System audio capture | Must-Have | Agent captures all audio from system speakers regardless of source application |
| FR-2 | Real-time speech-to-text | Must-Have | Audio transcribed to text within 2-3 seconds using Gemini STT |
| FR-3 | Speaker diarization | Must-Have | Distinguishes user voice from interviewer(s) after calibration |
| FR-4 | Context loading | Must-Have | User can upload resume, job description, company info, and Q&As |
| FR-5 | RAG-based retrieval | Must-Have | Relevant context retrieved in <1 second based on question |
| FR-6 | LLM answer generation | Must-Have | Gemini generates contextual answers within 3-5 seconds |
| FR-7 | Real-time text display | Must-Have | Answers displayed as readable text immediately as generated (streaming) |
| FR-8 | Screen share invisibility | Must-Have | Window excluded from screen capture/recording |
| FR-9 | Voice calibration | Must-Have | User speaks test phrase at session start to identify their voice |
| FR-10 | Session controls | Must-Have | Clear Start/Stop interview session controls |
| FR-11 | Confidence indicators | Should-Have | Show whether answer is from context vs general knowledge |
| FR-12 | Manual question input | Should-Have | User can type a question if audio capture fails |

### Non-Functional Requirements

| ID | Requirement | Priority | Metric |
|----|-------------|----------|--------|
| NFR-1 | Response latency | Must-Have | End-to-end < 5 seconds from question end to answer start |
| NFR-2 | Audio processing | Must-Have | Real-time processing with < 500ms delay |
| NFR-3 | Resource usage | Must-Have | < 500MB RAM, < 10% CPU during idle listening |
| NFR-4 | Cross-platform | Must-Have | Works on Windows, macOS, Linux |
| NFR-5 | Easy setup | Must-Have | User ready to use within 5 minutes of download |
| NFR-6 | Reliability | Must-Have | No crashes during 2-hour interview session |
| NFR-7 | UI responsiveness | Must-Have | UI never freezes; always shows current state |

---

## 6. MVP Scope

### In Scope (MVP)
- Desktop application (Windows, macOS, Linux)
- System audio capture
- Gemini speech-to-text
- Gemini LLM for answer generation
- Basic speaker diarization (user vs others)
- Context upload (resume, job desc, company info, Q&As)
- RAG-based context retrieval
- Simple text display UI
- Screen capture exclusion
- Session start/stop controls

### Out of Scope (Future)
- Multi-provider LLM switching (OpenAI, Anthropic)
- Multi-provider STT switching
- Answer history/logging
- Custom prompt tuning UI
- Analytics/performance tracking
- Interview recording/playback
- Mobile app
- Non-English languages
- In-person interview support

---

## 7. Technical Considerations

### Recommended Stack (To Be Validated in Solution Phase)

| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| Desktop Framework | Tauri or Electron | Cross-platform, modern, battle-tested |
| Backend Language | Python or Rust | Python for AI/ML ecosystem; Rust for Tauri |
| Audio Capture | OS-native APIs | System audio capture varies by OS |
| Speech-to-Text | Gemini API | User preference, good accuracy |
| LLM | Gemini API | User preference, multimodal capability |
| RAG | LangChain or LlamaIndex | Battle-tested, good Gemini integration |
| Vector Store | ChromaDB or FAISS | Local, lightweight, fast |
| UI | React or Svelte | Modern, component-based |

### Key Technical Challenges
1. **Cross-platform audio capture**: System audio capture differs significantly between Windows, macOS, and Linux
2. **Screen capture exclusion**: OS-specific APIs required (Windows WDA, macOS sharingType)
3. **Real-time processing**: Balancing latency with accuracy in STT and LLM
4. **Speaker diarization**: Accurate voice identification with minimal calibration

---

## 8. Testing Strategy

### Testing Approach
1. **Unit Tests**: Core logic (RAG, audio processing, API integration)
2. **Integration Tests**: End-to-end pipeline (audio → STT → RAG → LLM → display)
3. **Manual Testing**: Mock interviews with real users

### Test Scenarios
| Scenario | Description |
|----------|-------------|
| Happy path | Clear audio, single interviewer, questions match context |
| Poor audio | Background noise, accent, low volume |
| Panel interview | 2-3 interviewers, rapid switching |
| Off-topic questions | Questions outside prepared context |
| Long interview | 2-hour session, resource monitoring |
| Screen share | Verify invisibility during Zoom/Teams screen share |
| API failure | Simulate Gemini API outage mid-interview |

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Setup time | < 5 minutes from download to first session |
| Response latency | < 5 seconds end-to-end |
| Answer relevance | > 80% of answers rated "helpful" in user testing |
| Session stability | Zero crashes in 2-hour sessions |
| Screen invisibility | 100% undetectable during screen share |

---

## 10. Open Questions

1. **Audio capture licensing**: Are there legal considerations for capturing system audio?
2. **Gemini API rate limits**: What are the limits for real-time streaming use?
3. **Voice calibration UX**: How long should calibration take? (5 seconds? 10 seconds?)
4. **Context file formats**: Which formats to support? (PDF, DOCX, TXT, MD?)
5. **Desktop framework choice**: Tauri (smaller, Rust) vs Electron (larger, more mature)?

---

## Approval

- [ ] User approves this specification
- [ ] Ready to proceed to PRD creation

