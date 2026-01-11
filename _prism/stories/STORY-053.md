# STORY-053: Memory Store Infrastructure

**Phase**: 4A - Persistent Memory
**Priority**: High
**Effort**: 1 day
**Dependencies**: None

---

## User Story

As a developer, I need a persistent memory store to save extracted facts, stories, and profiles, so that the LLM can maintain understanding of the candidate across all interactions.

---

## Acceptance Criteria

### AC-1: SQLite Database Setup
- [ ] Database created at `~/.live_interview_agent/memory.db`
- [ ] Schema includes tables: documents, facts, stories, candidate_profile, session_claims
- [ ] Migrations system for future schema changes
- [ ] Database connection pool for concurrent access

### AC-2: Data Models
- [ ] `ExtractedFacts` dataclass with skills, timeline, achievements, education
- [ ] `STARStory` dataclass with situation, task, action, result, metrics, tags
- [ ] `CandidateProfile` dataclass with profile_text (~1000 tokens)
- [ ] `SessionClaim` dataclass for consistency tracking

### AC-3: CRUD Operations
- [ ] `save_document_summary(doc_id, summary, sections)` - stores document summaries
- [ ] `save_facts(doc_id, facts: ExtractedFacts)` - stores extracted facts
- [ ] `save_story(story: STARStory)` - stores STAR story
- [ ] `get_all_facts() -> ExtractedFacts` - retrieves merged facts
- [ ] `get_all_stories() -> List[STARStory]` - retrieves story bank
- [ ] `get_profile() -> CandidateProfile` - retrieves current profile
- [ ] `save_profile(profile: CandidateProfile)` - updates profile

### AC-4: Session Claims
- [ ] `add_claim(session_id, claim_text, claim_type)` - logs a claim
- [ ] `get_session_claims(session_id) -> List[SessionClaim]` - retrieves claims
- [ ] `clear_session_claims(session_id)` - clears claims on session end

---

## Technical Notes

```python
# File: sidecar/src/memory/store.py

class MemoryStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._default_path()
        self._ensure_schema()
    
    def _default_path(self) -> str:
        home = Path.home()
        app_dir = home / ".live_interview_agent"
        app_dir.mkdir(exist_ok=True)
        return str(app_dir / "memory.db")
```

---

## Test Cases

1. **test_database_creation**: Verify database file created on first access
2. **test_save_and_retrieve_facts**: Save facts, retrieve, verify match
3. **test_save_and_retrieve_stories**: Save multiple stories, retrieve all
4. **test_profile_update**: Save profile, update, verify latest returned
5. **test_session_claims**: Add claims, retrieve by session, clear session
6. **test_concurrent_access**: Multiple simultaneous reads/writes succeed

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests passing with >90% coverage
- [ ] Integration test with real SQLite database
- [ ] No type errors (pyright clean)
- [ ] Code reviewed
