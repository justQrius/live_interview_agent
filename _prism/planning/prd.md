# PRD: Live Interview Agent

## Problem Statement

Job seekers invest significant time preparing for interviews using AI tools, but must memorize answers since they cannot access these tools during live interviews. This creates inefficiency, anxiety, and limits their ability to provide well-researched, contextual responses. The Live Interview Agent solves this by providing a real-time AI assistant that listens to interviews and surfaces intelligent, contextual answers instantly, enabling candidates to respond confidently with accurate information drawn from their resume, research, and preparation materials.

**User Pain Points:**
- Memorization burden leads to incomplete or inaccurate recall under pressure
- Unable to reference preparation materials during live interviews
- Missing opportunities to highlight relevant experience from their background
- Stress from trying to remember all prepared answers
- No support system during the most critical career moments

**Business Impact:**
- Improves interview success rates for job seekers
- Reduces preparation anxiety and time investment
- Enables better utilization of existing preparation work
- Creates competitive advantage in technical and non-technical interviews

## Goals

- Deliver contextual interview answers in under 5 seconds end-to-end latency
- Achieve seamless system audio capture and real-time transcription (2-3 seconds)
- Provide accurate speaker diarization to distinguish user from interviewer(s)
- Enable users to load and retrieve context (resume, job descriptions, Q&As) in under 1 second
- Maintain invisibility during screen sharing to avoid detection
- Ensure simple setup process completable in under 5 minutes
- Support cross-platform usage (Windows, macOS, Linux) with consistent experience
- Deliver stable 2-hour interview sessions without crashes or freezes

## Non-Goals

- Multi-provider LLM/STT switching (future enhancement)
- Answer history logging or session playback (future enhancement)
- Custom prompt tuning UI (future enhancement)
- Analytics or performance tracking dashboards (future enhancement)
- Recording or playback of interview sessions (privacy/legal concerns)
- Mobile application support (desktop-focused MVP)
- Non-English language support (English-only MVP)
- Integration with job boards or ATS systems (out of scope)
- Automated interview scheduling or calendar integration

## User Personas

### Primary Persona: Tech Job Seeker - Sarah

- **Description**: 28-year-old software engineer with 4 years experience, preparing for senior engineer roles at FAANG companies
- **Technical Proficiency**: High - comfortable with command-line tools, understands APIs and local applications
- **Needs**:
  - Quick, accurate answers during technical and behavioral interviews
  - Ability to reference specific projects from resume
  - Support during system design and coding discussions
  - Confidence boost from having intelligent backup
- **Pain Points**:
  - Struggles to remember all STAR method examples under pressure
  - Forgets specific technical details about past projects
  - Anxious about behavioral questions with multiple interviewers
  - Concerned about screen sharing revealing assistance tools
- **Environment**: Uses Windows laptop, interviews via Zoom/Google Meet, typically has 4-6 interviews per role

### Secondary Persona: Career Changer - Marcus

- **Description**: 35-year-old transitioning from finance to product management, completing PM bootcamp
- **Technical Proficiency**: Medium - comfortable with desktop apps, less familiar with technical setup
- **Needs**:
  - Help articulating transferable skills from finance background
  - Guidance on product management frameworks (RICE, AARRR, etc.)
  - Support recalling case study details from bootcamp
  - Simple, non-technical setup process
- **Pain Points**:
  - Imposter syndrome in new field
  - Limited PM-specific experience to reference
  - Must rely heavily on preparation materials
  - Worried about technical setup complexity
- **Environment**: Uses macOS, interviews via Zoom, typically has 3-4 interviews per role

### Tertiary Persona: Entry-Level Candidate - Priya

- **Description**: 22-year-old recent CS graduate applying for first full-time role
- **Technical Proficiency**: Medium-high - strong programming skills, less experience with system tools
- **Needs**:
  - Assistance with company research and culture fit questions
  - Help connecting academic projects to real-world applications
  - Support for technical interviews (algorithms, data structures)
  - Quick setup with minimal configuration
- **Pain Points**:
  - Limited professional experience to reference
  - Nervous about first professional interviews
  - Overwhelmed by different company cultures and values
  - Wants to focus on interview, not tool management
- **Environment**: Uses Linux or Windows, interviews via various platforms, high volume of applications

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | System Audio Capture | Must Have | System can capture all audio from speakers/headphones on Windows, macOS, and Linux without requiring virtual audio cables or complex routing |
| FR-2 | Real-Time Speech-to-Text | Must Have | Audio is transcribed to text using Gemini STT API within 2-3 seconds of speech completion, with >90% accuracy for clear English speech |
| FR-3 | Speaker Diarization | Must Have | After voice calibration, system distinguishes user's voice from interviewer(s) with >85% accuracy, labeling transcripts as "User" or "Interviewer" |
| FR-4 | Context Loading | Must Have | Users can upload resume (PDF/DOCX), job description (text/URL), company info (text/URL), and Q&A documents (text/markdown). Total context up to 50MB accepted. |
| FR-5 | RAG-based Context Retrieval | Must Have | Given interviewer question, system retrieves top 3-5 most relevant context chunks in <1 second using vector similarity search |
| FR-6 | LLM Answer Generation | Must Have | Gemini generates contextual answer incorporating retrieved context within 3-5 seconds, formatted for easy reading |
| FR-7 | Real-Time Text Display | Must Have | Answers stream to UI as generated, with smooth typing effect. User can read partial answers before completion. |
| FR-8 | Screen Share Invisibility | Must Have | Application window is excluded from screen capture on Windows (DWM), macOS (kCGWindowListOptionOnScreenOnly), and Linux (Wayland/X11 exclusion). Verified via test screen shares. |
| FR-9 | Voice Calibration | Must Have | At session start, user speaks 5-10 second test phrase. System creates voice profile to identify user in subsequent audio. Can recalibrate mid-session if needed. |
| FR-10 | Session Controls | Must Have | UI has clearly labeled Start/Stop buttons. Start button initializes audio capture and begins transcription. Stop button halts all processing and clears temporary data. |
| FR-11 | Confidence Indicators | Should Have | Answers display confidence badge: "High Confidence" (answer from uploaded context), "Medium Confidence" (partial context match), "Low Confidence" (general knowledge only) |
| FR-12 | Manual Question Input | Should Have | If audio fails or unclear, user can type question into text box. System processes typed question identically to transcribed audio. |
| FR-13 | Noise Reduction | Should Have | Audio preprocessing applies noise reduction filter before STT to improve accuracy in non-ideal conditions (background noise, poor microphone) |
| FR-14 | Context Preview | Could Have | UI shows loaded context files with preview (first 200 chars). User can remove or replace files before session start. |
| FR-15 | Answer History (Session Only) | Could Have | During active session, user can scroll back to view previous questions and answers. Cleared when session stops. |

## Non-Functional Requirements

| ID | Requirement | Priority | Metric | Rationale |
|----|-------------|----------|--------|-----------|
| NFR-1 | End-to-End Latency | Must Have | <5 seconds from question completion to answer display start | User must receive answers while question context is fresh. Longer delays make tool impractical. |
| NFR-2 | Audio Processing Delay | Must Have | <500ms delay in audio pipeline (capture → preprocessing → STT) | Real-time transcription requires minimal buffering. Longer delays cause lag and missed speech. |
| NFR-3 | Resource Usage | Must Have | <500MB RAM, <10% CPU at idle, <30% CPU during active processing | Lightweight footprint ensures compatibility with interview video calls (Zoom, Meet) on user's machine. |
| NFR-4 | Cross-Platform Compatibility | Must Have | Identical feature set on Windows 10+, macOS 11+, Ubuntu 20.04+ | Users interview on various operating systems. Consistent experience required. |
| NFR-5 | Setup Time | Must Have | <5 minutes from download to first session start (including API key configuration) | Reduces barrier to entry. Users preparing for interviews have limited time. |
| NFR-6 | Session Stability | Must Have | Zero crashes during 2-hour continuous sessions (P99) | Interview sessions typically last 30-60 minutes. Tool must be reliable during critical moments. |
| NFR-7 | UI Responsiveness | Must Have | UI never freezes. All operations <100ms response time except LLM (which streams). | Frozen UI causes panic during interviews. Smooth experience essential for user confidence. |
| NFR-8 | API Cost Efficiency | Should Have | <$0.50 per 1-hour interview session (Gemini STT + LLM costs) | Makes tool economically viable for frequent users. MVP targets individual job seekers, not enterprises. |
| NFR-9 | Context Chunk Retrieval Accuracy | Should Have | Top 3 retrieved chunks contain answer-relevant information >80% of the time | RAG effectiveness depends on retrieval precision. Low accuracy produces irrelevant answers. |
| NFR-10 | Security | Should Have | API keys stored encrypted locally. No interview content sent to third parties except Gemini API. | Protects user privacy and sensitive interview content. |
| NFR-11 | Accessibility | Could Have | UI supports keyboard navigation and screen readers (WCAG 2.1 AA) | Ensures tool usable by candidates with disabilities. |

## Edge Cases and Handling

| Edge Case | Impact | Mitigation Strategy | Acceptance Criteria |
|-----------|--------|---------------------|---------------------|
| Poor audio quality (noise, low volume) | STT accuracy drops, incorrect transcription | Apply noise reduction preprocessing. Display low-confidence indicator. Provide manual question input fallback. | STT accuracy >70% with moderate background noise. Manual input always available. |
| Heavy accents (interviewer or user) | STT misinterprets speech | Use Gemini STT's accent support. Display transcription to user for verification. Allow manual correction before answer generation. | User can see transcription and manually retry if inaccurate. |
| Panel interviews (3+ speakers) | Diarization cannot distinguish all speakers | Classify as "User" vs "Interviewer(s)" (binary). Focus on detecting user to filter out their speech from questions. | User voice correctly identified >85% of the time. All other speakers treated as interviewers. |
| Rapid follow-up questions | Previous answer still generating when new question arrives | Interrupt current LLM stream, queue new question, display "Interrupted - answering new question" indicator. | New answer starts within 1 second of new question detection. Old answer cleared or archived. |
| Off-topic questions (unrelated to context) | RAG returns low-relevance chunks | LLM uses general knowledge when confidence <50%. Display "Low Confidence - General Knowledge" badge. | User aware answer is not from their context. Answer still helpful. |
| Long silence (5+ minutes) | Continuous processing wastes resources | Voice Activity Detection (VAD) reduces processing after 30 seconds of silence. Resume on speech detection. | CPU usage <5% during silence. Resume within 500ms of new speech. |
| Context overload (100+ pages) | RAG retrieval slows down, memory bloat | Enforce 50MB total context limit. Chunk documents into 500-token segments. Use efficient vector DB (FAISS/Chroma). | Retrieval stays <1 second even with max context. UI warns if limit exceeded. |
| API failure (Gemini STT/LLM down) | Tool becomes non-functional | Implement exponential backoff retry (3 attempts). Cache last successful response. Display error state with "Retry" button. | User sees clear error message. Can retry manually. Doesn't crash. |
| API rate limiting | Throttled requests delay responses | Monitor rate limits. Queue requests if near limit. Display "Rate limited - retrying in Xs" message. | User informed of delay. Requests eventually succeed. |
| Screen invisibility fails (OS bug) | Tool visible in screen share, user detected | Test on each OS before release. Provide manual minimize/hide hotkey (Ctrl+Shift+H). Document fallback procedure. | Invisibility works >95% of the time. User has manual fallback. |
| Network connectivity loss | API calls fail, tool unusable | Detect connectivity before API calls. Display "Offline - check connection" error. Retry when connection restored. | User informed immediately. Tool recovers automatically when online. |
| Very long questions (3+ minutes) | Transcription buffer overflows | Stream transcription in 30-second chunks. Concatenate for full question. Handle partial question context. | Questions up to 5 minutes transcribed successfully. |
| Simultaneous speech (user and interviewer) | Diarization confused, unclear who asked question | Detect overlapping speech. Prioritize interviewer audio for question detection. Display "Multiple speakers - unclear question" warning. | User can retry with manual input if unclear. |

## Success Metrics

### Primary Metrics (MVP Launch)

- **Response Latency (P50)**: <3 seconds end-to-end (question completion → answer display start)
- **Response Latency (P95)**: <5 seconds end-to-end
- **STT Accuracy**: >90% word error rate (WER) for clear English speech
- **Speaker Diarization Accuracy**: >85% correct user vs interviewer classification
- **Session Stability**: <1% crash rate during 2-hour sessions
- **Setup Success Rate**: >95% of users complete setup in <5 minutes
- **Cross-Platform Parity**: All core features (FR-1 to FR-10) work on Windows, macOS, Linux

### Secondary Metrics (Post-Launch)

- **User Satisfaction**: >4.0/5 average rating on ease of use
- **Context Retrieval Precision**: >80% of answers incorporate relevant context from uploaded materials
- **API Cost Per Session**: <$0.50 per 1-hour session
- **Screen Invisibility Success**: >95% success rate across OS versions
- **Manual Fallback Usage**: <10% of questions require manual input (indicates good audio quality handling)

### Qualitative Success Indicators

- Users report increased confidence during interviews
- Users successfully complete interviews without detection
- Setup process requires no technical support requests
- Tool "disappears" during use (low cognitive load)

## Dependencies

### External Dependencies

| Dependency | Type | Criticality | Notes |
|------------|------|-------------|-------|
| Google Gemini API | Cloud Service | Critical | Required for STT and LLM. No fallback in MVP. |
| Gemini API Key | User-Provided | Critical | Users must obtain their own API key. Setup docs must guide this. |
| System Audio Drivers | OS-Level | Critical | Platform-specific: Windows (WASAPI), macOS (Core Audio), Linux (PulseAudio/ALSA) |
| Screen Capture APIs | OS-Level | Critical | Platform-specific: Windows (DWM), macOS (CGWindowList), Linux (Wayland/X11) |

### Internal Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Vector Database (FAISS/Chroma) | Library | Required for RAG-based retrieval. Local embedding generation. |
| Audio Processing Library | Library | For noise reduction, VAD, format conversion. |
| Embedding Model | Local/API | For context chunking and similarity search. Consider Gemini embeddings or local model. |
| Cross-Platform UI Framework | Library | Electron, Tauri, or similar for consistent cross-platform UI. |

### Technical Stack (To Be Finalized in Solution Design)

- **Language**: To be determined (TypeScript/Node.js, Python, Rust candidates)
- **UI Framework**: To be determined (Electron, Tauri candidates)
- **Vector DB**: FAISS or ChromaDB (local)
- **Audio Processing**: Platform-specific libraries + noise reduction (e.g., RNNoise)

## Technical Constraints

1. **Gemini API Only (MVP)**: All LLM and STT calls must use Gemini. No multi-provider support in MVP.
2. **Local Processing**: Everything except Gemini API calls runs locally. No cloud servers for audio/context.
3. **Cross-Platform**: Must work identically on Windows, macOS, and Linux with single codebase where possible.
4. **Resource Limits**: Must coexist with video conferencing software (Zoom/Meet) without degrading performance.
5. **Privacy**: No logging of interview content to disk or external servers (except Gemini API in transit).

## Security & Privacy Considerations

1. **API Key Storage**: Encrypt API keys at rest using OS keychain (Windows Credential Manager, macOS Keychain, Linux Secret Service)
2. **Data Retention**: Clear all session data (transcripts, answers) on session stop. No persistent storage of interview content.
3. **Context Files**: Store uploaded context locally. Delete when user removes from app.
4. **Network Traffic**: All API calls over HTTPS. No plaintext transmission.
5. **Screen Invisibility**: Critical privacy feature. Must test thoroughly on each OS version.

## Open Questions

- [ ] **Embedding Model Choice**: Use Gemini Embeddings API or local model (e.g., Sentence-BERT)? Trade-off: API cost/latency vs local resource usage.
- [ ] **UI Framework**: Electron (mature, heavier) vs Tauri (lighter, Rust-based) vs native framework? Impact on bundle size and performance.
- [ ] **Audio Calibration UX**: Should calibration be mandatory at session start or optional with fallback to basic diarization?
- [ ] **Voice Activity Detection (VAD) Library**: WebRTC VAD, Silero VAD, or custom? Need balance of accuracy and performance.
- [ ] **Context File Parsing**: How to handle complex resume formats (multi-column PDFs, tables)? May need OCR or specialized PDF parsing.
- [ ] **Streaming Answer Display**: Character-by-character streaming or word-by-word? Impact on readability and perceived speed.
- [ ] **Hotkey Support**: Should app support global hotkeys for start/stop/minimize while in background?
- [ ] **Confidence Threshold Tuning**: What similarity score threshold distinguishes High/Medium/Low confidence? Requires experimentation.
- [ ] **Testing Strategy for Screen Invisibility**: How to automate testing of screen capture exclusion across OS versions?
- [ ] **Packaging & Distribution**: Standalone executable, installer, or app store? Impact on setup time goal.

## Timeline & Phasing

### MVP (Phase 1) - Target: 6-8 weeks
**Must Have**: FR-1 to FR-10, NFR-1 to NFR-7

Core functionality for single-user interviews with basic audio quality.

### Enhanced MVP (Phase 2) - Target: +2-3 weeks
**Should Have**: FR-11 to FR-13, NFR-8 to NFR-10

Improved reliability and confidence indicators.

### Future Enhancements (Phase 3+) - Post-MVP
**Could Have**: FR-14, FR-15, NFR-11, multi-provider support, analytics, answer history, mobile app

## Appendix: Related Documents

- **Specification**: `_prism/discovery/spec.md` (if created during discovery)
- **Architecture Design**: `_prism/design/architecture.md` (to be created in `/prism-solution`)
- **Test Plan**: `_prism/testing/test-plan.md` (to be created in `/prism-verify`)

---

**Document Status**: Draft v1.0
**Created**: 2026-01-05
**Last Updated**: 2026-01-05
**Owner**: Product (AI Agent)
**Reviewers**: User (awaiting approval)

**Next Step**: Proceed to `/prism-solution` for architecture and solution design after PRD approval.
