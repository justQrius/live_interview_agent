# STORY-037: Session Store - SQLite Schema & CRUD

**Phase**: 3A (Foundation)
**Priority**: P1 - Must Have
**Effort**: 1 day
**Dependencies**: None

## Description

Create the SQLite-based session persistence layer. Implement the database schema and basic CRUD operations for sessions, transcriptions, and answers.

## Acceptance Criteria

- [ ] Create `SessionHistoryStore` class in `sidecar/src/storage/session_store.py`
- [ ] Implement SQLite schema with 3 tables: sessions, transcriptions, answers
- [ ] Database location: `~/.live_interview_agent/sessions.db`
- [ ] CRUD operations: create, read, update, delete for sessions
- [ ] Add transcription and answer recording methods
- [ ] Implement session listing with pagination
- [ ] Unit tests with in-memory SQLite
- [ ] Handle concurrent access safely

## Technical Details

### File Location
```
sidecar/src/storage/
├── __init__.py
└── session_store.py
```

### Database Schema

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    context_files TEXT,  -- JSON array
    metadata TEXT        -- JSON object
);

CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp REAL NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence TEXT,
    rag_chunks TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transcriptions_session ON transcriptions(session_id);
CREATE INDEX idx_answers_session ON answers(session_id);
CREATE INDEX idx_sessions_started ON sessions(started_at DESC);
```

### Interface

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class SessionSummary:
    id: str
    started_at: datetime
    ended_at: Optional[datetime]
    context_files: List[str]
    transcription_count: int
    answer_count: int

@dataclass
class SessionData:
    id: str
    started_at: datetime
    ended_at: Optional[datetime]
    context_files: List[str]
    transcriptions: List[dict]
    answers: List[dict]
    metadata: dict

class SessionHistoryStore:
    def __init__(self, db_path: str = None):
        """Initialize with optional custom path (for testing)."""
    
    def create_session(self, context_files: List[str] = None) -> str:
        """Create new session, return session_id."""
    
    def end_session(self, session_id: str) -> None:
        """Mark session as ended with timestamp."""
    
    def add_transcription(
        self, 
        session_id: str, 
        speaker: str, 
        text: str, 
        timestamp: float,
        confidence: float = None
    ) -> None:
        """Record a transcription."""
    
    def add_answer(
        self,
        session_id: str,
        question: str,
        answer: str,
        confidence: str = None,
        rag_chunks: List[str] = None,
        latency_ms: int = None
    ) -> None:
        """Record an answer."""
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get full session data."""
    
    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionSummary]:
        """List sessions with pagination."""
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and all related data."""
```

## Test Cases

1. **Create and retrieve session**: Create session, verify ID returned and retrievable
2. **Add transcriptions**: Add multiple transcriptions, verify order preserved
3. **Add answers**: Add answer with metadata, verify all fields stored
4. **List sessions**: Create 5 sessions, verify list returns newest first
5. **Delete cascade**: Delete session, verify transcriptions/answers also deleted
6. **Concurrent writes**: Simulate concurrent transcription writes
7. **Empty database**: List sessions on fresh DB returns empty list

## Definition of Done

- [ ] Schema implemented and tested
- [ ] All CRUD operations working
- [ ] Unit tests with in-memory SQLite
- [ ] Path expansion for ~ (home directory)
- [ ] JSON serialization for array fields
- [ ] Error handling for missing sessions
