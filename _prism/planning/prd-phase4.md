# PRD: Phase 4 - Interview Coach Evolution

**Version**: 1.0
**Date**: 2026-01-10
**Author**: Prism PM Agent
**Status**: Draft - Pending Approval

---

## Executive Summary

Phase 4 transforms the Live Interview Agent from a **reactive answer generator** into a **proactive interview coach** that truly helps users get the job. This phase addresses five critical architectural gaps identified through deep analysis:

1. **Interview Playbook**: Comprehensive pre-interview preparation with 20+ tailored questions
2. **Persistent Memory Architecture**: LLM "learns" and remembers the user's complete profile
3. **Enhanced Question Detection**: LLM fallback for ambiguous cases
4. **Continuous-Feel Transcription**: Speculative processing and streaming improvements
5. **User-Centric Coaching**: Real-time story recall, answer coaching, consistency tracking

---

## Problem Statement

### Current State Analysis

| Component | Current Behavior | User Impact |
|-----------|------------------|-------------|
| **Preparation** | 15-bullet summary from first 5 chunks | User feels unprepared, generic advice |
| **Context Memory** | LLM sees only 5 RAG chunks per question | No persistent understanding of who user is |
| **Question Detection** | Rule-based only (Tier 1+2) | Misses ~15% of ambiguous questions |
| **Transcription UX** | Segmented, post-hoc processing | Feels laggy, no interim feedback |
| **Coaching** | None - just answer generation | No structure guidance, story recall, or consistency |

### User Pain Points (From Analysis)

1. **"The prep guide is minimal"** - User needs actionable playbook, not a summary
2. **"Agent doesn't know me"** - Every answer feels like starting fresh
3. **"Missed my question"** - Ambiguous questions not detected
4. **"Feels slow"** - No feedback during interviewer speech
5. **"I'm rambling"** - No guidance on answer structure or length

### Business Impact

- Users abandon the app mid-interview due to irrelevant answers
- Preparation feature underutilized (doesn't provide enough value)
- Competitive disadvantage vs coaching-focused alternatives
- User confidence not improved despite using the tool

---

## Goals

| ID | Goal | Success Metric | Priority |
|----|------|----------------|----------|
| G1 | Comprehensive interview preparation | User has 20+ tailored questions with suggested answers | Must Have |
| G2 | Persistent candidate understanding | LLM maintains consistent identity across all answers | Must Have |
| G3 | Near-zero question detection misses | <5% false negatives on ambiguous questions | Should Have |
| G4 | Real-time responsive UX | Interim transcripts visible within 500ms of speech | Should Have |
| G5 | Active coaching during interview | Story suggestions surface within 1s of question detection | Must Have |
| G6 | Answer consistency tracking | Zero contradictions in claims during interview | Should Have |

---

## Non-Goals

- **Voice synthesis / speaking for the user** - User speaks their own answers
- **Video analysis** - Audio-only for Phase 4
- **Mock interview mode with AI interviewer** - Future phase
- **Multi-language support** - English only
- **Mobile app** - Desktop focus
- **Calendar integration** - Future phase

---

## User Stories

### Epic 1: Interview Playbook

> As a job seeker, I want a comprehensive preparation guide tailored to my specific interview, so that I walk in confident and ready for any question.

**Acceptance Criteria:**
- System generates structured "Interview Playbook" document
- Playbook includes 20+ questions tailored to: role level, job requirements, company, interviewer context
- Each question has a suggested answer framework grounded in user's resume
- Playbook includes competency mapping (JD requirement → user evidence)
- Playbook includes STAR story bank with 8-12 tagged stories
- Playbook includes weakness/gap mitigation scripts
- Playbook includes 1-page "cheat sheet" summary
- Playbook available as downloadable PDF/Markdown

### Epic 2: Persistent Memory

> As a job seeker, I want the AI to truly understand my background and maintain that understanding throughout the interview, so that every answer is consistent and personalized.

**Acceptance Criteria:**
- System extracts structured data from documents on upload (skills, timeline, achievements, stories)
- System generates hierarchical summaries (document-level, section-level)
- System injects "Candidate Profile" (~1000 tokens) into every LLM prompt
- System tracks claims made during interview session
- System warns if user contradicts previous statements
- RAG retrieval enhanced with extracted facts, not just chunks

### Epic 3: Enhanced Question Detection

> As a job seeker, I want the system to never miss a real question, even when the interviewer phrases it awkwardly or indirectly.

**Acceptance Criteria:**
- Tier 3 LLM fallback triggers when Tier 1+2 confidence < 0.7
- Tier 3 uses fast model (gpt-4o-mini or equivalent) with <150ms latency
- System handles: interrupted questions, indirect questions, rhetorical-vs-real
- False negative rate < 5% on ambiguous question dataset
- System logs all Tier 3 invocations for analysis

### Epic 4: Continuous-Feel Transcription

> As a job seeker, I want to see what the interviewer is saying in real-time, so I don't feel like the system is frozen.

**Acceptance Criteria:**
- Interim transcript tokens stream to UI during speech
- Speculative RAG retrieval begins after first clause detected
- Speculative query formation starts before segment ends
- System merges segments when interviewer pauses briefly mid-question
- End-to-end perceived latency reduced from ~5s to ~2s

### Epic 5: Interview Coaching

> As a job seeker, I want real-time guidance on how to structure my answer and which stories to use, so I deliver polished responses without rambling.

**Acceptance Criteria:**
- When behavioral question detected, relevant STAR story surfaces within 1s
- Story display includes: situation summary, key metrics, opening line suggestion
- System suggests answer structure (STAR, Pyramid, thesis-evidence)
- System tracks answer length and suggests wrap-up after 90 seconds
- System shows "consistency panel" with claims made this session
- Practice mode available for pre-interview drilling

---

## Functional Requirements

### FR-1: Interview Playbook Generation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1.1 | System MUST generate 20+ tailored questions | Must Have | Questions based on: JD requirements, role level, company context, interviewer background |
| FR-1.2 | System MUST categorize questions by type | Must Have | Categories: behavioral, technical, motivation, situational, curveball |
| FR-1.3 | System MUST provide suggested answer for each question | Must Have | Answer grounded in resume, uses STAR/appropriate framework |
| FR-1.4 | System MUST map JD requirements to user evidence | Must Have | Table format: Requirement → Evidence → Metrics → Emphasis |
| FR-1.5 | System MUST extract STAR story candidates | Must Have | 8-12 stories with tags (leadership, conflict, scale, failure, etc.) |
| FR-1.6 | System MUST identify gaps/weaknesses | Must Have | Gap analysis with mitigation scripts |
| FR-1.7 | System MUST generate positioning statement | Must Have | 20s/60s/2min versions tailored to role |
| FR-1.8 | System MUST generate questions user should ask | Must Have | 5-10 high-signal questions |
| FR-1.9 | System MUST produce 1-page cheat sheet | Must Have | Printable summary for quick reference |
| FR-1.10 | System MUST support export (PDF, Markdown) | Should Have | Download button with format selection |
| FR-1.11 | System SHOULD consider interviewer context | Should Have | If hiring manager doc provided, tailor to their focus areas |

### FR-2: Persistent Memory Architecture

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-2.1 | System MUST extract structured data on upload | Must Have | Skills inventory, career timeline, achievement metrics |
| FR-2.2 | System MUST extract STAR story candidates | Must Have | Structured format: situation, task, action, result, metrics |
| FR-2.3 | System MUST generate document summaries | Must Have | Document-level (~200 words) and section-level (~50 words each) |
| FR-2.4 | System MUST create "Candidate Profile" | Must Have | Compact representation (~1000 tokens) for prompt injection |
| FR-2.5 | System MUST inject profile into every LLM call | Must Have | Profile appears in system prompt consistently |
| FR-2.6 | System MUST track session claims | Must Have | Log of factual claims made (years of experience, metrics cited) |
| FR-2.7 | System SHOULD warn on contradiction | Should Have | Alert if new claim conflicts with previous |
| FR-2.8 | System SHOULD support profile editing | Should Have | User can correct extracted information |

### FR-3: Enhanced Question Detection

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-3.1 | System MUST implement Tier 3 LLM fallback | Must Have | Triggers when confidence < 0.7 and text looks interrogative |
| FR-3.2 | System MUST use fast model for Tier 3 | Must Have | gpt-4o-mini, claude-haiku, or gemini-flash |
| FR-3.3 | Tier 3 latency MUST be < 150ms | Must Have | Measured P95 |
| FR-3.4 | System MUST run Tier 3 in parallel with speculative retrieval | Must Have | No additional latency on hot path |
| FR-3.5 | System MUST log all Tier 3 decisions | Should Have | For pattern analysis and threshold tuning |
| FR-3.6 | System SHOULD handle interrupted questions | Should Have | Detect and wait for completion |

### FR-4: Continuous-Feel Transcription

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-4.1 | System MUST stream interim transcripts to UI | Must Have | Partial text visible during speech |
| FR-4.2 | System MUST begin speculative retrieval early | Must Have | RAG query formed after first clause (~2s into speech) |
| FR-4.3 | System MUST support segment merging | Should Have | Brief pauses (<500ms) don't finalize segment |
| FR-4.4 | UI MUST show "listening" indicator with live text | Must Have | Visual feedback that system is active |
| FR-4.5 | System SHOULD pre-warm answer generation | Should Have | LLM context prepared before segment finalization |

### FR-5: Interview Coaching

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-5.1 | System MUST surface relevant STAR story on behavioral Q | Must Have | Story appears within 1s of question detection |
| FR-5.2 | Story display MUST include key elements | Must Have | Situation, key metrics, suggested opening line |
| FR-5.3 | System MUST suggest answer structure | Must Have | STAR for behavioral, Concept-Example-Tradeoff for technical |
| FR-5.4 | System SHOULD track answer duration | Should Have | Timer visible, gentle nudge at 90s |
| FR-5.5 | System SHOULD show consistency panel | Should Have | List of claims made this session |
| FR-5.6 | System SHOULD support practice mode | Should Have | Mock questions with timed answers and feedback |
| FR-5.7 | UI MUST show coaching hints prominently | Must Have | Hints visible alongside answer, not hidden |

---

## Non-Functional Requirements

| ID | Requirement | Priority | Metric |
|----|-------------|----------|--------|
| NFR-1 | Playbook generation time | Must Have | < 30 seconds for full playbook |
| NFR-2 | Memory extraction time | Must Have | < 10 seconds per document |
| NFR-3 | Tier 3 detection latency | Must Have | < 150ms P95 |
| NFR-4 | Interim transcript latency | Must Have | < 500ms from speech to display |
| NFR-5 | Story recall latency | Must Have | < 1s from question detection |
| NFR-6 | Profile size | Must Have | < 1500 tokens to fit in context |
| NFR-7 | Consistency check latency | Should Have | < 100ms (local comparison) |
| NFR-8 | Backward compatibility | Must Have | Existing sessions and documents work |

---

## Technical Approach (High-Level)

### Playbook Generation
- Multi-prompt LLM pipeline: question generation → answer drafting → story mapping
- Question templates by category (behavioral, technical, motivation, situational)
- JD requirement extraction via structured prompting
- Export via markdown-to-PDF library

### Persistent Memory
- On-upload extraction pipeline: parse → summarize → extract facts → extract stories
- Storage: JSON/SQLite for structured data alongside existing ChromaDB
- Profile template with placeholders filled from extracted data
- Session claim tracking via simple append-only log

### Enhanced Detection
- Tier 3 prompt: "Is this an interview question requiring an answer? YES/NO"
- Fast model selection based on available API keys
- Parallel execution with speculative retrieval

### Continuous-Feel Transcription
- Streaming STT (if provider supports) or interim callbacks
- Clause detection via simple heuristics (subject-verb detected)
- Segment merge logic in VAD processor

### Interview Coaching
- Story matching via embedding similarity between question and story bank
- Structure templates by question type
- Duration tracking in UI component
- Claims log with simple entity extraction

---

## Dependencies

| Dependency | Type | Impact | Mitigation |
|------------|------|--------|------------|
| Phase 3 complete | Internal | Required foundation | Already complete |
| Fast LLM model access | External | Required for Tier 3 | Multi-provider fallback |
| Streaming STT support | External | Required for FR-4 | Graceful degradation |
| PDF export library | External | Required for playbook | python-markdown + weasyprint |

---

## Implementation Phases

### Phase 4A: Interview Playbook (Priority 1)
**Effort**: 3-4 days
- FR-1.1 through FR-1.11
- Question generation, story extraction, competency mapping
- Export functionality

### Phase 4B: Persistent Memory (Priority 1)
**Effort**: 3-4 days
- FR-2.1 through FR-2.8
- Structured extraction, profile generation, claim tracking

### Phase 4C: Enhanced Detection (Priority 2)
**Effort**: 1-2 days
- FR-3.1 through FR-3.6
- Tier 3 implementation, parallel execution

### Phase 4D: Continuous-Feel Transcription (Priority 2)
**Effort**: 2-3 days
- FR-4.1 through FR-4.5
- Streaming, speculative retrieval, segment merging

### Phase 4E: Interview Coaching (Priority 3)
**Effort**: 2-3 days
- FR-5.1 through FR-5.7
- Story recall, structure hints, consistency panel

**Total Estimated Effort**: 11-16 days

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Preparation satisfaction | N/A (minimal usage) | >80% find playbook "very helpful" | Post-prep survey |
| Answer consistency | Unknown | Zero contradictions detected | Session analysis |
| Question detection accuracy | ~85% | >95% | Test dataset |
| Perceived latency | ~5s | <2s | User perception survey |
| Story usage rate | 0% (no stories extracted) | >50% of behavioral Qs use suggested story | Session analysis |
| Interview success rate | Unknown baseline | Track user-reported outcomes | Follow-up survey |

---

## Open Questions

- [ ] Should playbook be regenerated if new documents uploaded?
- [ ] How to handle conflicting information between documents?
- [ ] Should consistency warnings be visible or just logged?
- [ ] What's the maximum profile size before truncation?
- [ ] Should practice mode include AI-as-interviewer?
- [ ] How to handle multi-person panels (multiple interviewers)?

---

## Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Playbook generation too slow | User frustration | Medium | Progressive loading, background generation |
| Extracted facts incorrect | Wrong information in answers | Medium | User verification UI, confidence scoring |
| Tier 3 LLM adds noticeable latency | Slower response | Low | Parallel execution, fast model selection |
| Profile too large for context | Truncation issues | Low | Aggressive summarization, priority ordering |
| Streaming STT not available | No interim feedback | Medium | Graceful degradation to current behavior |

---

## Approval

- [ ] Product Owner approval
- [ ] Technical Lead approval
- [ ] Ready for Architecture phase

**Approved by**: ___________________ **Date**: ___________
