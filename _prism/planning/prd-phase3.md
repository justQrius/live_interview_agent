# PRD: Phase 3 - Intelligent Interview Agent Enhancements

**Version**: 1.0
**Date**: 2026-01-09
**Author**: Prism PM Agent
**Status**: Draft - Pending Approval

---

## Problem Statement

The Live Interview Agent currently has significant limitations that reduce its effectiveness as an interview assistant:

1. **Over-triggering**: The agent treats ALL interviewer speech as questions requiring answers. Statements like "That's interesting" or "Let me tell you about the role" trigger unnecessary answer generation, creating noise and confusion.

2. **Limited Context**: Only resumes can be uploaded. Users cannot provide job descriptions, company information, or sample Q&A to prepare the agent, resulting in generic answers that don't align with specific opportunities.

3. **Poor Follow-up Handling**: The agent cannot understand follow-up questions like "What about Python?" or "Can you elaborate?" - these require context from previous exchanges to answer properly.

4. **Single Question Focus**: Compound questions like "Tell me about your experience with React and how do you handle testing?" are answered as a single unit, often missing one component.

5. **No Session Persistence**: All conversation history is lost when the session ends. Users cannot review past interviews, track improvement, or analyze patterns.

**Business Impact**: These limitations reduce user confidence in the product, leading to abandoned sessions and missed interview opportunities. Users report feeling the agent is "too eager" and "not intelligent enough" to understand conversational nuance.

---

## Goals

| ID | Goal | Success Metric | Priority |
|----|------|----------------|----------|
| G1 | Reduce false-positive question detection | <15% false triggers (currently ~40%) | Must Have |
| G2 | Enable multi-document context preparation | Support 5+ document types with intelligent retrieval | Must Have |
| G3 | Handle follow-up questions naturally | 70%+ follow-up questions resolved correctly | Should Have |
| G4 | Support compound questions | 80%+ multi-part questions fully addressed | Should Have |
| G5 | Persist and analyze session history | 100% session data available for post-interview review | Must Have |

---

## Non-Goals

- **Real-time coaching/feedback during interviews** - Out of scope for Phase 3
- **Video analysis or facial recognition** - Not planned
- **Third-party calendar integration** - Future phase
- **Mobile app support** - Desktop focus only
- **Offline mode** - Requires internet connection
- **Multi-language interview support** - English only for now

---

## User Personas

### Primary Persona: Active Job Seeker (Alex)

- **Description**: Software engineer with 3-5 years experience, actively interviewing at multiple companies
- **Needs**: 
  - Quick preparation before each interview
  - Relevant answers tailored to specific company/role
  - Review of past interview performance
- **Pain Points**:
  - Agent answers when interviewer is just explaining things
  - Can't upload job description to get targeted answers
  - Loses all context when restarting the app

### Secondary Persona: Career Coach (Morgan)

- **Description**: Professional coach helping clients prepare for interviews
- **Needs**:
  - Review client interview sessions
  - Identify patterns and areas for improvement
  - Prepare custom Q&A for specific roles
- **Pain Points**:
  - No way to save and review session transcripts
  - Can't pre-load sample questions and ideal answers
  - Limited customization for different interview types

---

## Functional Requirements

### FR-1: Intelligent Question Detection

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1.1 | System MUST distinguish questions from statements | Must Have | Rule-based detection catches >80% obvious questions in <2ms |
| FR-1.2 | System MUST classify question types | Must Have | Correctly classifies: interview_question, follow_up, clarification, small_talk, statement, acknowledgment |
| FR-1.3 | System MUST NOT trigger answers for non-questions | Must Have | False positive rate <15% on standard interview transcript dataset |
| FR-1.4 | System SHOULD use conversation context for ambiguous cases | Should Have | Context-aware classification for pronouns and references |
| FR-1.5 | System SHOULD provide confidence scores | Should Have | Confidence threshold configurable (default: 0.7) |

### FR-2: Multi-Document Context Engineering

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-2.1 | System MUST support multiple document types | Must Have | resume, job_description, company_info, industry_research, sample_qa, custom |
| FR-2.2 | System MUST tag documents with metadata | Must Have | Document type, section labels, relevance tags stored |
| FR-2.3 | System MUST retrieve context based on question type | Must Have | Behavioral questions prioritize resume; motivation questions prioritize company info |
| FR-2.4 | System SHOULD support pre-interview preparation | Should Have | "Prepare" button generates briefing summary from all documents |
| FR-2.5 | System SHOULD support hierarchical chunking | Should Have | Parent chunks (2048 chars) for context, child chunks (512 chars) for retrieval |
| FR-2.6 | UI MUST show document type selection on upload | Must Have | Dropdown with 6 document type options |

### FR-3: Follow-up Question Handling

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-3.1 | System MUST detect follow-up questions | Must Have | Detects "What about X?", "Can you elaborate?", "And the results?" |
| FR-3.2 | System MUST resolve pronouns/references | Must Have | "it", "that", "this" linked to previous topic |
| FR-3.3 | System MUST expand follow-ups into standalone questions | Must Have | "What about Python?" → "What is your experience with Python?" |
| FR-3.4 | System SHOULD use last 3-5 conversation turns for context | Should Have | Configurable context window |

### FR-4: Multi-Question Support

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-4.1 | System MUST detect compound questions | Must Have | Identifies questions with "and", multiple question marks, list patterns |
| FR-4.2 | System MUST split compound questions | Must Have | "What's X and how do you Y?" → ["What's X?", "How do you Y?"] |
| FR-4.3 | System MUST aggregate context for all sub-questions | Must Have | RAG retrieval includes relevant chunks for each sub-question |
| FR-4.4 | System MUST generate cohesive multi-part answers | Must Have | Single answer addresses all sub-questions naturally |

### FR-5: Session Persistence

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-5.1 | System MUST save complete session history | Must Have | All transcriptions and answers stored with timestamps |
| FR-5.2 | System MUST prompt user to save on session end | Must Have | Optional save dialog with "Don't ask again" option |
| FR-5.3 | System MUST list saved sessions | Must Have | Session list with date, duration, document context |
| FR-5.4 | System MUST allow session replay/review | Must Have | Read-only view of past session transcripts and answers |
| FR-5.5 | System MUST support session export | Must Have | Export as JSON, Markdown, or plain text |
| FR-5.6 | System MUST support session deletion | Must Have | Delete individual sessions with confirmation |
| FR-5.7 | UI MUST show "History" tab/section | Must Have | Accessible from main navigation |

---

## Non-Functional Requirements

| ID | Requirement | Priority | Metric |
|----|-------------|----------|--------|
| NFR-1 | Question detection latency | Must Have | <10ms P95 for rule-based, <50ms P95 for ML-enhanced |
| NFR-2 | No degradation in answer generation latency | Must Have | <1.5s end-to-end maintained |
| NFR-3 | Session storage efficiency | Must Have | <5MB per 1-hour session |
| NFR-4 | Backward compatibility | Must Have | Existing sessions continue to work |
| NFR-5 | Privacy - local storage only | Must Have | All session data stored locally, never uploaded |
| NFR-6 | Performance with 10+ documents | Should Have | RAG retrieval <100ms with 10 documents |

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| False positive answer triggers | ~40% | <15% | Automated test suite + user feedback |
| Answer relevance score | 70% | 85% | User rating (thumbs up/down) |
| Session save rate | 0% | >60% | Analytics on save dialog actions |
| Follow-up resolution accuracy | 0% | 70% | Test dataset of follow-up scenarios |
| Multi-question coverage | ~50% | 90% | Automated multi-part question tests |

---

## Dependencies

| Dependency | Type | Impact | Mitigation |
|------------|------|--------|------------|
| Existing RAG infrastructure | Internal | Required for FR-2 | Already complete in Phase 1-2 |
| ChromaDB metadata support | Internal | Required for document type filtering | Verify current version supports filtering |
| SQLite or JSON storage | Internal | Required for FR-5 | Use Python stdlib sqlite3 |
| LLM provider availability | External | Required for preparation summaries | Graceful degradation if unavailable |

---

## Technical Approach (High-Level)

### Question Detection
- **Tier 1**: Rule-based pattern matching (<2ms)
- **Tier 2**: Lightweight ML classifier (optional, 20-50ms)
- **Tier 3**: LLM fallback for ambiguous cases (200ms)

### Context Engineering
- Hierarchical chunking with parent-child relationships
- Metadata-driven retrieval filtering
- Pre-interview preparation via LLM synthesis

### Session Persistence
- SQLite database in user home directory
- Three tables: sessions, transcriptions, answers
- Export utilities for common formats

---

## Open Questions

- [ ] Should we support importing sessions from external sources?
- [ ] Should preparation summaries be editable by the user?
- [ ] What is the maximum number of documents we should support?
- [ ] Should we add analytics/insights on session history (e.g., "You've improved X%")?
- [ ] Should question detection confidence be visible to users?

---

## Implementation Phases

### Phase 3A: Foundation (Priority 1)
1. FR-1: Question Detection (complete subsystem)
2. FR-5: Session Persistence (complete subsystem)

### Phase 3B: Enhanced Context (Priority 2)
3. FR-2: Multi-Document Context Engineering

### Phase 3C: Conversational Intelligence (Priority 3)
4. FR-3: Follow-up Question Handling
5. FR-4: Multi-Question Support

---

## Appendix: Research Summary

### Question Detection Approaches Evaluated
| Approach | Accuracy | Latency | Recommendation |
|----------|----------|---------|----------------|
| Rule-based patterns | 65-75% | <1ms | Use as Tier 1 |
| spaCy textcat | 85-92% | 20ms | Optional Tier 2 |
| LLM few-shot | 92-97% | 200ms | Fallback only |
| RASA DIET | 88-95% | 50ms | Overkill for this use case |

### Context Engineering Patterns Evaluated
| Pattern | Pros | Cons | Recommendation |
|---------|------|------|----------------|
| Hierarchical Parent-Child | Best precision+context | 2-3x storage | Recommended |
| Metadata-driven filtering | Cross-doc reasoning | Schema complexity | Recommended |
| Hybrid search (vector+keyword) | Handles rare terms | Dual index | Optional |

### Session Storage Options Evaluated
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| SQLite | Standard, queryable | Requires schema | Recommended |
| JSON files | Simple, portable | No querying | Alternative |
| IndexedDB (frontend) | Browser-native | Limited Python access | Not recommended |

---

## Approval

- [ ] Product Owner approval
- [ ] Technical Lead approval
- [ ] Ready for Architecture phase

**Approved by**: ___________________ **Date**: ___________
