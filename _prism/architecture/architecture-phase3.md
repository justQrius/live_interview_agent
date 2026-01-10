# Architecture: Phase 3 - Intelligent Interview Agent Enhancements

**Version**: 1.0
**Date**: 2026-01-09
**Status**: Draft - Pending Approval
**PRD Reference**: `_prism/planning/prd-phase3.md`

---

## Overview

Phase 3 introduces five major subsystems to make the interview agent more intelligent and useful:

1. **Question Detection Pipeline** - Cascaded classification to distinguish questions from statements
2. **Enhanced Context System** - Multi-document support with intelligent retrieval
3. **Query Reformulation** - Follow-up question resolution and expansion
4. **Question Splitting** - Compound question detection and handling
5. **Session Persistence** - SQLite-based history storage and retrieval

**Key Design Principles**:
- **Latency-first**: Question detection must add <10ms to the pipeline
- **Graceful degradation**: Each tier fails safely to the next
- **Backward compatible**: Existing sessions continue to work
- **Local-only storage**: No cloud dependencies for persistence

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TAURI APP (Frontend)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Document   │  │  Session    │  │  History    │  │  Enhanced Session   │ │
│  │  Uploader   │  │  Controls   │  │  Viewer     │  │      Store          │ │
│  │  (6 types)  │  │             │  │             │  │  (Zustand + IPC)    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                     │           │
└─────────┼────────────────┼────────────────┼─────────────────────┼───────────┘
          │                │                │                     │
          │  WebSocket (ws://localhost:8765)                      │
          ▼                ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PYTHON SIDECAR                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    QUESTION PROCESSING PIPELINE                         │ │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌────────────┐  │ │
│  │  │  Question   │──►│   Query     │──►│  Question   │──►│  Enhanced  │  │ │
│  │  │  Detector   │   │ Reformulator│   │  Splitter   │   │    RAG     │  │ │
│  │  │ (Cascaded)  │   │ (Follow-up) │   │ (Multi-Q)   │   │  Engine    │  │ │
│  │  └─────────────┘   └─────────────┘   └─────────────┘   └────────────┘  │ │
│  │       │                                                       │         │ │
│  │       │ is_question=false                                     │         │ │
│  │       └──────────────► Skip LLM generation                    │         │ │
│  └────────────────────────────────────────────────────────────────┼────────┘ │
│                                                                   │          │
│  ┌────────────────────────────────────────────────────────────────┼────────┐ │
│  │                    CONTEXT MANAGEMENT                          ▼        │ │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────┐   │ │
│  │  │ Enhanced Context│   │  Hierarchical   │   │   Metadata-Driven   │   │ │
│  │  │     Manager     │──►│    Chunker      │──►│   Vector Store      │   │ │
│  │  │  (6 doc types)  │   │ (parent/child)  │   │    (ChromaDB)       │   │ │
│  │  └─────────────────┘   └─────────────────┘   └─────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    SESSION PERSISTENCE                                  │ │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────┐   │ │
│  │  │  Session Store  │──►│    SQLite DB    │──►│  Export Utilities   │   │ │
│  │  │   (Python)      │   │ ~/.live_agent/  │   │  (JSON/MD/TXT)      │   │ │
│  │  └─────────────────┘   └─────────────────┘   └─────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Question Detector

**Responsibility**: Determine if interviewer speech is an actionable question requiring an answer.

**Location**: `sidecar/src/classification/question_detector.py`

**Dependencies**: None (standalone, no ML models required for Tier 1)

**Interface**:
```python
class QuestionDetector:
    def is_actionable_question(
        self, 
        text: str, 
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[bool, float, str]:
        """
        Returns: (is_question, confidence, classification_type)
        
        Types: 'interview_question', 'follow_up', 'clarification', 
               'small_talk', 'statement', 'acknowledgment'
        """
```

**Design: Cascaded Classification**

```
┌─────────────────────────────────────────────────────────────────┐
│                   QUESTION DETECTION CASCADE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: "That's interesting, tell me more about your Python"    │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TIER 1: Rule-Based Pattern Matching                     │   │
│  │  Latency: <2ms | Accuracy: 65-75%                        │   │
│  │                                                          │   │
│  │  ✓ Check question mark (?)                               │   │
│  │  ✓ Check WH-words (what, how, why, when, where, who)     │   │
│  │  ✓ Check interview patterns (tell me about, describe)    │   │
│  │  ✓ Check acknowledgment patterns (okay, great, thanks)   │   │
│  │                                                          │   │
│  │  Result: OBVIOUS_QUESTION | OBVIOUS_STATEMENT | UNCLEAR  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          │ UNCLEAR (confidence < 0.8)            │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TIER 2: Context-Aware Heuristics                        │   │
│  │  Latency: 5-10ms | Accuracy: 80-85%                      │   │
│  │                                                          │   │
│  │  ✓ Analyze conversation flow                             │   │
│  │  ✓ Check if previous turn was an answer                  │   │
│  │  ✓ Detect topic transitions                              │   │
│  │                                                          │   │
│  │  Result: QUESTION | STATEMENT | UNCLEAR                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          │ UNCLEAR (confidence < 0.7)            │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TIER 3: LLM Classification (Optional, Configurable)     │   │
│  │  Latency: 150-300ms | Accuracy: 92-97%                   │   │
│  │                                                          │   │
│  │  Few-shot prompt to classify ambiguous cases             │   │
│  │  Only invoked for <5% of inputs                          │   │
│  │                                                          │   │
│  │  Result: QUESTION | STATEMENT                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Pattern Library**:
```python
INTERVIEW_QUESTION_PATTERNS = [
    r"^tell me about",
    r"^describe (a |your )",
    r"^explain (how|what|why)",
    r"^what (is|are|was|were|do|did|would|have)",
    r"^how (do|did|would|have|can|could)",
    r"^why (do|did|would|have)",
    r"^can you (tell|describe|explain|walk)",
    r"^walk me through",
    r"^give me an example",
    r"^have you (ever|had)",
]

STATEMENT_PATTERNS = [
    r"^(okay|ok|alright|sure|great|perfect|excellent|good|nice)",
    r"^(thank you|thanks)",
    r"^(i see|i understand|got it|makes sense)",
    r"^(let me|let's|we'll|we will)",
    r"^(that's|that is) (good|great|interesting|helpful)",
    r"^(moving on|next|now)",
    r"^(so basically|in other words)",
]
```

---

### 2. Enhanced Context Manager

**Responsibility**: Process and manage multiple document types with rich metadata.

**Location**: `sidecar/src/context/enhanced_manager.py`

**Dependencies**: `context/chunker.py`, `context/parsers.py`, `rag/store.py`

**Interface**:
```python
class DocumentType(Enum):
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INDUSTRY_RESEARCH = "industry_research"
    SAMPLE_QA = "sample_qa"
    CUSTOM = "custom"

class EnhancedContextManager:
    async def process_file(
        self, 
        filename: str, 
        content_b64: str,
        document_type: DocumentType
    ) -> List[EnhancedChunk]
    
    async def prepare_for_interview(self) -> str
    
    def get_chunks_by_type(self, doc_type: DocumentType) -> List[EnhancedChunk]
```

**Enhanced Chunk Structure**:
```python
@dataclass
class EnhancedChunk:
    id: str
    text: str
    document_type: DocumentType
    section: str  # "experience", "skills", "requirements", "about", etc.
    relevance_tags: List[str]  # ["python", "leadership", "aws"]
    parent_chunk_id: Optional[str]  # For hierarchical retrieval
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
```

**Hierarchical Chunking Strategy**:
```
Document (full text)
    │
    ├── Parent Chunk 1 (2048 chars) ─── For context delivery
    │       │
    │       ├── Child Chunk 1a (512 chars) ─── For retrieval precision
    │       └── Child Chunk 1b (512 chars)
    │
    └── Parent Chunk 2 (2048 chars)
            │
            ├── Child Chunk 2a (512 chars)
            └── Child Chunk 2b (512 chars)
```

---

### 3. Query Reformulator

**Responsibility**: Expand follow-up questions into standalone, answerable queries.

**Location**: `sidecar/src/classification/query_reformulator.py`

**Dependencies**: `classification/question_detector.py`

**Interface**:
```python
class QueryReformulator:
    def reformulate_if_needed(
        self, 
        current_question: str,
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[str, bool]:
        """
        Returns: (reformulated_question, was_reformulated)
        """
```

**Reformulation Patterns**:
```python
FOLLOW_UP_INDICATORS = [
    r"^(what about|how about)",
    r"^(and|also|what else)",
    r"^(can you|could you) (elaborate|expand|explain more)",
    r"^(tell me more|go on|continue)",
    r"(that|this|it|those|these)\?*$",  # Ends with pronoun
]

EXPANSION_TEMPLATES = {
    r"^what about (.+)\?*$": "What is your experience with {match} in relation to {prev_topic}?",
    r"^how about (.+)\?*$": "How do you handle {match} based on your experience with {prev_topic}?",
    r"^(can you|could you) elaborate\?*$": "Can you elaborate on {prev_topic}?",
    r"^(and|what about) (the )?results?\?*$": "What were the results of {prev_topic}?",
    r"^tell me more\?*$": "Tell me more about {prev_topic}.",
}
```

---

### 4. Question Splitter

**Responsibility**: Detect and split compound questions into individual answerable units.

**Location**: `sidecar/src/classification/question_splitter.py`

**Dependencies**: None

**Interface**:
```python
class QuestionSplitter:
    def split_questions(self, text: str) -> List[str]:
        """
        Split compound questions into individual questions.
        Returns original text as single-item list if not compound.
        """
```

**Splitting Strategy**:
```python
COMPOUND_INDICATORS = [
    r"\band\b.*(what|how|why|when|where|tell|describe)",
    r"\?.*\?",  # Multiple question marks
    r"(first|second|also|additionally).*(what|how|tell)",
    r"(one|another|other) (thing|question)",
]

# Split on conjunctions that precede question words
SPLIT_PATTERN = r"\s+(and|also|additionally)\s+(?=(what|how|why|when|where|can|could|tell|describe))"
```

---

### 5. Enhanced RAG Engine

**Responsibility**: Retrieve context with document-type-aware filtering and hierarchical expansion.

**Location**: `sidecar/src/rag/enhanced_engine.py`

**Dependencies**: `rag/store.py`, `context/enhanced_manager.py`

**Interface**:
```python
class EnhancedRAGEngine:
    def retrieve_for_question(
        self, 
        question: str, 
        question_type: str,
        sub_questions: List[str] = None,
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve context with question-type-aware filtering.
        """
    
    def retrieve_with_parent_expansion(
        self,
        query: str,
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve child chunks, then expand to parent chunks for full context.
        """
```

**Question-Type to Document-Type Mapping**:
```python
DOC_PRIORITY_BY_QUESTION_TYPE = {
    "behavioral": [DocumentType.RESUME, DocumentType.SAMPLE_QA],
    "technical": [DocumentType.RESUME, DocumentType.JOB_DESCRIPTION],
    "motivation": [DocumentType.COMPANY_INFO, DocumentType.JOB_DESCRIPTION, DocumentType.INDUSTRY_RESEARCH],
    "intro": [DocumentType.RESUME],
    "weakness": [DocumentType.SAMPLE_QA, DocumentType.RESUME],
    "general": [DocumentType.RESUME, DocumentType.JOB_DESCRIPTION],
}
```

---

### 6. Session History Store

**Responsibility**: Persist session data to local SQLite database with CRUD operations.

**Location**: `sidecar/src/storage/session_store.py`

**Dependencies**: Python `sqlite3` (stdlib)

**Interface**:
```python
class SessionHistoryStore:
    def __init__(self, db_path: str = None)
    
    # Session lifecycle
    def create_session(self, context_files: List[str]) -> str  # Returns session_id
    def end_session(self, session_id: str) -> None
    
    # Recording
    def add_transcription(self, session_id: str, speaker: str, text: str, timestamp: float, confidence: float) -> None
    def add_answer(self, session_id: str, question: str, answer: str, confidence: str, latency_ms: int) -> None
    
    # Retrieval
    def get_session(self, session_id: str) -> SessionData
    def list_sessions(self, limit: int = 50) -> List[SessionSummary]
    
    # Export
    def export_session(self, session_id: str, format: str = "json") -> str
    
    # Management
    def delete_session(self, session_id: str) -> None
```

**Database Schema**:
```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    context_files TEXT,  -- JSON array of filenames
    metadata TEXT        -- JSON object for extensibility
);

-- Transcriptions table
CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    speaker TEXT NOT NULL,  -- 'User' or 'Interviewer'
    text TEXT NOT NULL,
    timestamp REAL NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Answers table
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence TEXT,  -- 'high', 'medium', 'low'
    rag_chunks TEXT,  -- JSON array of chunk IDs used
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_transcriptions_session ON transcriptions(session_id);
CREATE INDEX idx_answers_session ON answers(session_id);
CREATE INDEX idx_sessions_started ON sessions(started_at DESC);
```

**Storage Location**: `~/.live_interview_agent/sessions.db`

---

## Data Flow

### Question Processing Flow

```
Interviewer Speech
        │
        ▼
┌───────────────────┐
│ QuestionDetector  │──── is_question=false ────► Log only, no answer
│  .is_actionable() │
└───────────────────┘
        │ is_question=true
        ▼
┌───────────────────┐
│ QueryReformulator │──── Expand follow-ups
│  .reformulate()   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ QuestionSplitter  │──── Split compound questions
│  .split()         │
└───────────────────┘
        │
        ▼ [q1, q2, ...]
┌───────────────────┐
│ EnhancedRAGEngine │──── Retrieve for each sub-question
│  .retrieve()      │──── Filter by question type
└───────────────────┘──── Expand to parent chunks
        │
        ▼ [context_chunks]
┌───────────────────┐
│ LLM Provider      │──── Generate unified answer
│  .generate()      │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ SessionStore      │──── Persist Q&A
│  .add_answer()    │
└───────────────────┘
```

---

## WebSocket Protocol Extensions

### New Message Types

```python
class MessageType(Enum):
    # Existing...
    
    # Session Persistence (FR-5)
    SAVE_SESSION = "SAVE_SESSION"
    LOAD_SESSION = "LOAD_SESSION"
    LIST_SESSIONS = "LIST_SESSIONS"
    EXPORT_SESSION = "EXPORT_SESSION"
    DELETE_SESSION = "DELETE_SESSION"
    SESSION_LIST = "SESSION_LIST"      # Response
    SESSION_DATA = "SESSION_DATA"      # Response
    SESSION_EXPORT = "SESSION_EXPORT"  # Response
    
    # Context Enhancement (FR-2)
    PREPARE_INTERVIEW = "PREPARE_INTERVIEW"
    PREPARATION_READY = "PREPARATION_READY"
```

### Enhanced UPLOAD_CONTEXT Message

```json
{
  "type": "UPLOAD_CONTEXT",
  "data": {
    "files": [
      {
        "name": "resume.pdf",
        "content": "<base64>",
        "documentType": "resume"
      },
      {
        "name": "job_description.txt",
        "content": "<base64>",
        "documentType": "job_description"
      }
    ]
  }
}
```

---

## Frontend Changes

### Enhanced Session Store

```typescript
// src/ui/store/sessionStore.ts additions

export type DocumentType = 
  | 'resume' 
  | 'job_description' 
  | 'company_info' 
  | 'industry_research' 
  | 'sample_qa' 
  | 'custom';

export interface ContextFile {
  id: string;
  name: string;
  type: DocumentType;  // Enhanced from 4 to 6 types
  size: number;
  uploadDate: number;
  preview: string;
  processingStatus: 'pending' | 'processing' | 'ready' | 'error';
}

export interface SessionSummary {
  id: string;
  startedAt: number;
  endedAt: number | null;
  duration: number;
  contextFiles: string[];
  transcriptionCount: number;
  answerCount: number;
}

export interface SessionState {
  // Existing fields...
  
  // New: Session persistence
  currentSessionId: string | null;
  savedSessions: SessionSummary[];
  isHistoryOpen: boolean;
  
  // New: Preparation
  preparationStatus: 'not_started' | 'preparing' | 'ready';
  preparationSummary: string | null;
  
  // New actions
  saveCurrentSession: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  listSessions: () => Promise<void>;
  exportSession: (sessionId: string, format: 'json' | 'md' | 'txt') => Promise<string>;
  deleteSession: (sessionId: string) => Promise<void>;
  startPreparation: () => Promise<void>;
  setHistoryOpen: (open: boolean) => void;
}
```

### New UI Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `DocumentTypeSelector` | `src/ui/components/DocumentTypeSelector.tsx` | Dropdown for document type selection |
| `HistoryPanel` | `src/ui/components/HistoryPanel.tsx` | List and manage saved sessions |
| `SessionViewer` | `src/ui/components/SessionViewer.tsx` | Read-only view of past session |
| `PreparationButton` | `src/ui/components/PreparationButton.tsx` | Trigger pre-interview preparation |
| `PreparationSummary` | `src/ui/components/PreparationSummary.tsx` | Display preparation briefing |

---

## Build Sequence (Stories)

### Phase 3A: Foundation

| Story | Name | Dependencies | Effort |
|-------|------|--------------|--------|
| STORY-034 | Question Detector - Rule-Based Tier | None | 1 day |
| STORY-035 | Question Detector - Context-Aware Tier | STORY-034 | 0.5 days |
| STORY-036 | Question Detector - Server Integration | STORY-035 | 0.5 days |
| STORY-037 | Session Store - SQLite Schema & CRUD | None | 1 day |
| STORY-038 | Session Store - Server Integration | STORY-037 | 0.5 days |
| STORY-039 | Session Store - WebSocket Protocol | STORY-038 | 0.5 days |
| STORY-040 | History Panel UI | STORY-039 | 1 day |
| STORY-041 | Session Export Utilities | STORY-037 | 0.5 days |

### Phase 3B: Enhanced Context

| Story | Name | Dependencies | Effort |
|-------|------|--------------|--------|
| STORY-042 | Enhanced Context Manager - Multi-Type | None | 1 day |
| STORY-043 | Hierarchical Chunker | STORY-042 | 0.5 days |
| STORY-044 | Metadata-Driven Vector Store | STORY-043 | 1 day |
| STORY-045 | Enhanced RAG Engine | STORY-044 | 1 day |
| STORY-046 | Document Type Selector UI | STORY-042 | 0.5 days |
| STORY-047 | Pre-Interview Preparation | STORY-045 | 1 day |
| STORY-048 | Preparation Summary UI | STORY-047 | 0.5 days |

### Phase 3C: Conversational Intelligence

| Story | Name | Dependencies | Effort |
|-------|------|--------------|--------|
| STORY-049 | Query Reformulator | STORY-036 | 1 day |
| STORY-050 | Question Splitter | STORY-036 | 0.5 days |
| STORY-051 | Pipeline Integration | STORY-049, STORY-050 | 1 day |
| STORY-052 | End-to-End Testing | All above | 1 day |

**Total Effort**: ~14 days

---

## Trade-offs

| Decision | Alternative | Why Chosen |
|----------|-------------|------------|
| SQLite for persistence | JSON files | Queryable, transactional, standard |
| Rule-based Tier 1 | ML-only classification | Sub-2ms latency requirement |
| Hierarchical chunking | Flat chunking | Better precision + context balance |
| Local storage only | Cloud sync | Privacy requirement, no dependencies |
| 6 document types | Unlimited types | Structured metadata, predictable retrieval |

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Question detection false negatives (miss real questions) | High | Medium | Conservative thresholds, user can trigger manual question |
| ChromaDB metadata filtering performance | Medium | Low | Benchmark with 10+ documents, add index if needed |
| SQLite concurrent access issues | Medium | Low | Single writer, multiple readers pattern |
| LLM Tier 3 latency impact | Medium | Low | Make Tier 3 optional, disabled by default |
| Hierarchical chunking complexity | Medium | Medium | Thorough testing, fallback to flat chunking |

---

## Configuration

```python
# sidecar/src/config/phase3.py

class Phase3Config:
    # Question Detection
    QUESTION_CONFIDENCE_THRESHOLD: float = 0.7
    ENABLE_LLM_CLASSIFICATION_TIER: bool = False  # Off by default
    LLM_CLASSIFICATION_TIMEOUT_MS: int = 300
    
    # Context Engineering
    PARENT_CHUNK_SIZE: int = 2048
    CHILD_CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 100
    MAX_DOCUMENTS: int = 20
    
    # Follow-up Handling
    CONVERSATION_CONTEXT_TURNS: int = 5
    
    # Session Persistence
    SESSION_DB_PATH: str = "~/.live_interview_agent/sessions.db"
    MAX_SESSIONS_STORED: int = 100
    AUTO_SAVE_ENABLED: bool = True
```

---

## Approval

- [ ] Architecture reviewed
- [ ] Trade-offs acceptable
- [ ] Build sequence approved
- [ ] Ready for Implementation phase

**Approved by**: ___________________ **Date**: ___________
