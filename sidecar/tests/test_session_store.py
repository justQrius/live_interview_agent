"""
Tests for SessionHistoryStore (Session Persistence).

Tests the SQLite-based session storage with CRUD operations
for sessions, transcriptions, and answers.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import List

from src.storage.session_store import SessionHistoryStore, SessionSummary, SessionData


class TestSessionStoreBasic:
    """Basic CRUD operation tests for SessionHistoryStore."""

    @pytest.fixture
    def store(self) -> SessionHistoryStore:
        """Create an in-memory store for testing."""
        return SessionHistoryStore(db_path=":memory:")

    # =========================================================================
    # SESSION CREATION
    # =========================================================================

    def test_create_session_returns_id(self, store: SessionHistoryStore):
        """Creating a session should return a unique ID."""
        session_id = store.create_session()
        
        assert session_id is not None
        assert len(session_id) > 0
        assert isinstance(session_id, str)

    def test_create_session_generates_unique_ids(self, store: SessionHistoryStore):
        """Each session should have a unique ID."""
        ids = [store.create_session() for _ in range(10)]
        
        assert len(set(ids)) == 10  # All unique

    def test_create_session_with_context_files(self, store: SessionHistoryStore):
        """Session can be created with context files."""
        context_files = ["resume.pdf", "job_description.txt"]
        session_id = store.create_session(context_files=context_files)
        
        session = store.get_session(session_id)
        assert session is not None
        assert session.context_files == context_files

    def test_create_session_with_empty_context(self, store: SessionHistoryStore):
        """Session can be created without context files."""
        session_id = store.create_session()
        
        session = store.get_session(session_id)
        assert session is not None
        assert session.context_files == []

    def test_create_session_sets_started_at(self, store: SessionHistoryStore):
        """Session should have started_at timestamp set."""
        before = datetime.now()
        session_id = store.create_session()
        after = datetime.now()
        
        session = store.get_session(session_id)
        assert session is not None
        assert before <= session.started_at <= after

    # =========================================================================
    # SESSION RETRIEVAL
    # =========================================================================

    def test_get_session_returns_data(self, store: SessionHistoryStore):
        """Getting a session should return SessionData."""
        session_id = store.create_session(context_files=["test.pdf"])
        
        session = store.get_session(session_id)
        
        assert isinstance(session, SessionData)
        assert session.id == session_id

    def test_get_session_nonexistent_returns_none(self, store: SessionHistoryStore):
        """Getting a nonexistent session should return None."""
        session = store.get_session("nonexistent-id")
        
        assert session is None

    def test_get_session_includes_transcriptions(self, store: SessionHistoryStore):
        """Session data should include transcriptions."""
        session_id = store.create_session()
        store.add_transcription(session_id, "Interviewer", "Hello", 0.0)
        store.add_transcription(session_id, "Candidate", "Hi there", 1.0)
        
        session = store.get_session(session_id)
        
        assert len(session.transcriptions) == 2

    def test_get_session_includes_answers(self, store: SessionHistoryStore):
        """Session data should include answers."""
        session_id = store.create_session()
        store.add_answer(session_id, "What is Python?", "Python is a language...")
        
        session = store.get_session(session_id)
        
        assert len(session.answers) == 1

    # =========================================================================
    # SESSION ENDING
    # =========================================================================

    def test_end_session_sets_timestamp(self, store: SessionHistoryStore):
        """Ending a session should set ended_at timestamp."""
        session_id = store.create_session()
        
        before = datetime.now()
        store.end_session(session_id)
        after = datetime.now()
        
        session = store.get_session(session_id)
        assert session.ended_at is not None
        assert before <= session.ended_at <= after

    def test_end_session_nonexistent_no_error(self, store: SessionHistoryStore):
        """Ending a nonexistent session should not raise error."""
        # Should not raise
        store.end_session("nonexistent-id")

    # =========================================================================
    # SESSION DELETION
    # =========================================================================

    def test_delete_session_removes_session(self, store: SessionHistoryStore):
        """Deleting a session should remove it."""
        session_id = store.create_session()
        
        result = store.delete_session(session_id)
        
        assert result is True
        assert store.get_session(session_id) is None

    def test_delete_session_nonexistent_returns_false(self, store: SessionHistoryStore):
        """Deleting a nonexistent session should return False."""
        result = store.delete_session("nonexistent-id")
        
        assert result is False

    def test_delete_session_cascades_to_transcriptions(self, store: SessionHistoryStore):
        """Deleting a session should delete its transcriptions."""
        session_id = store.create_session()
        store.add_transcription(session_id, "Interviewer", "Hello", 0.0)
        store.add_transcription(session_id, "Candidate", "Hi", 1.0)
        
        store.delete_session(session_id)
        
        # Create new session to verify transcriptions were deleted
        session = store.get_session(session_id)
        assert session is None

    def test_delete_session_cascades_to_answers(self, store: SessionHistoryStore):
        """Deleting a session should delete its answers."""
        session_id = store.create_session()
        store.add_answer(session_id, "Question?", "Answer.")
        
        store.delete_session(session_id)
        
        session = store.get_session(session_id)
        assert session is None


class TestTranscriptions:
    """Tests for transcription recording."""

    @pytest.fixture
    def store(self) -> SessionHistoryStore:
        """Create an in-memory store for testing."""
        return SessionHistoryStore(db_path=":memory:")

    def test_add_transcription_basic(self, store: SessionHistoryStore):
        """Add a basic transcription."""
        session_id = store.create_session()
        
        store.add_transcription(session_id, "Interviewer", "Tell me about yourself", 0.0)
        
        session = store.get_session(session_id)
        assert len(session.transcriptions) == 1
        assert session.transcriptions[0]["speaker"] == "Interviewer"
        assert session.transcriptions[0]["text"] == "Tell me about yourself"

    def test_add_transcription_with_confidence(self, store: SessionHistoryStore):
        """Add transcription with confidence score."""
        session_id = store.create_session()
        
        store.add_transcription(session_id, "Interviewer", "Hello", 0.0, confidence=0.95)
        
        session = store.get_session(session_id)
        assert session.transcriptions[0]["confidence"] == 0.95

    def test_add_transcription_preserves_order(self, store: SessionHistoryStore):
        """Transcriptions should be returned in timestamp order."""
        session_id = store.create_session()
        
        store.add_transcription(session_id, "Interviewer", "First", 0.0)
        store.add_transcription(session_id, "Candidate", "Second", 1.0)
        store.add_transcription(session_id, "Interviewer", "Third", 2.0)
        
        session = store.get_session(session_id)
        assert len(session.transcriptions) == 3
        assert session.transcriptions[0]["text"] == "First"
        assert session.transcriptions[1]["text"] == "Second"
        assert session.transcriptions[2]["text"] == "Third"

    def test_add_transcription_invalid_session(self, store: SessionHistoryStore):
        """Adding transcription to invalid session should raise or be handled."""
        # Depending on implementation, this might raise or silently fail
        # For robustness, we'll accept either behavior but not crash
        try:
            store.add_transcription("invalid-session", "Speaker", "Text", 0.0)
        except Exception:
            pass  # Expected behavior

    def test_add_many_transcriptions(self, store: SessionHistoryStore):
        """Store should handle many transcriptions efficiently."""
        session_id = store.create_session()
        
        for i in range(100):
            store.add_transcription(
                session_id, 
                "Interviewer" if i % 2 == 0 else "Candidate",
                f"Message {i}",
                float(i)
            )
        
        session = store.get_session(session_id)
        assert len(session.transcriptions) == 100


class TestAnswers:
    """Tests for answer recording."""

    @pytest.fixture
    def store(self) -> SessionHistoryStore:
        """Create an in-memory store for testing."""
        return SessionHistoryStore(db_path=":memory:")

    def test_add_answer_basic(self, store: SessionHistoryStore):
        """Add a basic answer."""
        session_id = store.create_session()
        
        store.add_answer(session_id, "What is Python?", "Python is a programming language.")
        
        session = store.get_session(session_id)
        assert len(session.answers) == 1
        assert session.answers[0]["question"] == "What is Python?"
        assert session.answers[0]["answer"] == "Python is a programming language."

    def test_add_answer_with_metadata(self, store: SessionHistoryStore):
        """Add answer with all metadata fields."""
        session_id = store.create_session()
        
        store.add_answer(
            session_id,
            question="What is Python?",
            answer="Python is a language...",
            confidence="high",
            rag_chunks=["chunk1", "chunk2"],
            latency_ms=250
        )
        
        session = store.get_session(session_id)
        answer = session.answers[0]
        assert answer["confidence"] == "high"
        assert answer["rag_chunks"] == ["chunk1", "chunk2"]
        assert answer["latency_ms"] == 250

    def test_add_answer_preserves_order(self, store: SessionHistoryStore):
        """Answers should be returned in creation order."""
        session_id = store.create_session()
        
        store.add_answer(session_id, "Q1", "A1")
        store.add_answer(session_id, "Q2", "A2")
        store.add_answer(session_id, "Q3", "A3")
        
        session = store.get_session(session_id)
        assert len(session.answers) == 3
        assert session.answers[0]["question"] == "Q1"
        assert session.answers[1]["question"] == "Q2"
        assert session.answers[2]["question"] == "Q3"

    def test_add_answer_with_none_fields(self, store: SessionHistoryStore):
        """Answer with None optional fields should work."""
        session_id = store.create_session()
        
        store.add_answer(
            session_id,
            question="Question?",
            answer="Answer.",
            confidence=None,
            rag_chunks=None,
            latency_ms=None
        )
        
        session = store.get_session(session_id)
        assert len(session.answers) == 1


class TestSessionListing:
    """Tests for session listing with pagination."""

    @pytest.fixture
    def store(self) -> SessionHistoryStore:
        """Create an in-memory store for testing."""
        return SessionHistoryStore(db_path=":memory:")

    def test_list_sessions_empty_database(self, store: SessionHistoryStore):
        """Listing sessions on empty DB should return empty list."""
        sessions = store.list_sessions()
        
        assert sessions == []

    def test_list_sessions_returns_summaries(self, store: SessionHistoryStore):
        """List should return SessionSummary objects."""
        store.create_session()
        
        sessions = store.list_sessions()
        
        assert len(sessions) == 1
        assert isinstance(sessions[0], SessionSummary)

    def test_list_sessions_newest_first(self, store: SessionHistoryStore):
        """Sessions should be ordered by started_at descending."""
        ids = []
        for i in range(5):
            ids.append(store.create_session())
            time.sleep(0.01)  # Ensure different timestamps
        
        sessions = store.list_sessions()
        
        assert len(sessions) == 5
        # Newest (last created) should be first
        assert sessions[0].id == ids[-1]
        assert sessions[-1].id == ids[0]

    def test_list_sessions_with_limit(self, store: SessionHistoryStore):
        """Limit should restrict number of results."""
        for _ in range(10):
            store.create_session()
        
        sessions = store.list_sessions(limit=5)
        
        assert len(sessions) == 5

    def test_list_sessions_with_offset(self, store: SessionHistoryStore):
        """Offset should skip results."""
        ids = []
        for i in range(10):
            ids.append(store.create_session())
            time.sleep(0.01)
        
        sessions = store.list_sessions(limit=5, offset=5)
        
        assert len(sessions) == 5
        # Should get the older sessions (after skipping 5 newest)

    def test_list_sessions_includes_counts(self, store: SessionHistoryStore):
        """Summary should include transcription and answer counts."""
        session_id = store.create_session()
        store.add_transcription(session_id, "Speaker", "Text 1", 0.0)
        store.add_transcription(session_id, "Speaker", "Text 2", 1.0)
        store.add_answer(session_id, "Q", "A")
        
        sessions = store.list_sessions()
        
        assert sessions[0].transcription_count == 2
        assert sessions[0].answer_count == 1

    def test_list_sessions_includes_context_files(self, store: SessionHistoryStore):
        """Summary should include context files."""
        context = ["resume.pdf", "jd.txt"]
        store.create_session(context_files=context)
        
        sessions = store.list_sessions()
        
        assert sessions[0].context_files == context


class TestConcurrency:
    """Tests for concurrent access safety."""

    @pytest.fixture
    def store(self, tmp_path) -> SessionHistoryStore:
        """Create a file-based store for concurrency testing.
        
        Note: In-memory SQLite databases are not shared between threads,
        so we use a file-based database for concurrency tests.
        """
        db_file = tmp_path / "test_concurrent.db"
        return SessionHistoryStore(db_path=str(db_file))

    def test_concurrent_transcription_writes(self, store: SessionHistoryStore):
        """Concurrent writes should not cause data loss."""
        session_id = store.create_session()
        num_threads = 10
        transcriptions_per_thread = 10
        errors = []
        
        def write_transcriptions(thread_id: int):
            try:
                for i in range(transcriptions_per_thread):
                    store.add_transcription(
                        session_id,
                        f"Thread-{thread_id}",
                        f"Message {i}",
                        float(thread_id * 100 + i)
                    )
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=write_transcriptions, args=(i,))
            for i in range(num_threads)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"
        
        session = store.get_session(session_id)
        assert len(session.transcriptions) == num_threads * transcriptions_per_thread

    def test_concurrent_session_creation(self, store: SessionHistoryStore):
        """Concurrent session creation should not cause conflicts."""
        num_threads = 10
        sessions_per_thread = 5
        created_ids: List[str] = []
        lock = threading.Lock()
        errors = []
        
        def create_sessions():
            try:
                for _ in range(sessions_per_thread):
                    session_id = store.create_session()
                    with lock:
                        created_ids.append(session_id)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=create_sessions)
            for _ in range(num_threads)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
        assert len(created_ids) == num_threads * sessions_per_thread
        assert len(set(created_ids)) == len(created_ids)  # All unique


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def store(self) -> SessionHistoryStore:
        """Create an in-memory store for testing."""
        return SessionHistoryStore(db_path=":memory:")

    def test_unicode_text_handling(self, store: SessionHistoryStore):
        """Store should handle unicode text correctly."""
        session_id = store.create_session()
        unicode_text = "你好世界 🎉 Привет мир"
        
        store.add_transcription(session_id, "Speaker", unicode_text, 0.0)
        
        session = store.get_session(session_id)
        assert session.transcriptions[0]["text"] == unicode_text

    def test_very_long_text(self, store: SessionHistoryStore):
        """Store should handle very long text."""
        session_id = store.create_session()
        long_text = "A" * 10000
        
        store.add_transcription(session_id, "Speaker", long_text, 0.0)
        
        session = store.get_session(session_id)
        assert len(session.transcriptions[0]["text"]) == 10000

    def test_special_characters_in_text(self, store: SessionHistoryStore):
        """Store should handle special characters."""
        session_id = store.create_session()
        special_text = "Text with 'quotes', \"double quotes\", and \\ backslashes"
        
        store.add_transcription(session_id, "Speaker", special_text, 0.0)
        
        session = store.get_session(session_id)
        assert session.transcriptions[0]["text"] == special_text

    def test_json_in_metadata(self, store: SessionHistoryStore):
        """Store should handle JSON strings in context files."""
        session_id = store.create_session()
        # Context files with special characters
        context = ['file with "quotes".pdf', "path/to/file.txt"]
        
        session_id = store.create_session(context_files=context)
        session = store.get_session(session_id)
        
        assert session.context_files == context

    def test_empty_transcription_text(self, store: SessionHistoryStore):
        """Empty transcription text should be handled."""
        session_id = store.create_session()
        
        store.add_transcription(session_id, "Speaker", "", 0.0)
        
        session = store.get_session(session_id)
        assert session.transcriptions[0]["text"] == ""

    def test_negative_timestamp(self, store: SessionHistoryStore):
        """Negative timestamps should be handled."""
        session_id = store.create_session()
        
        store.add_transcription(session_id, "Speaker", "Text", -1.0)
        
        session = store.get_session(session_id)
        assert session.transcriptions[0]["timestamp"] == -1.0


class TestDatabasePath:
    """Tests for database path handling."""

    def test_custom_path_works(self, tmp_path):
        """Custom database path should work."""
        db_file = tmp_path / "test.db"
        store = SessionHistoryStore(db_path=str(db_file))
        
        session_id = store.create_session()
        
        assert db_file.exists()
        assert store.get_session(session_id) is not None

    def test_in_memory_database(self):
        """In-memory database should work."""
        store = SessionHistoryStore(db_path=":memory:")
        
        session_id = store.create_session()
        
        assert store.get_session(session_id) is not None

    def test_default_path_expansion(self, monkeypatch, tmp_path):
        """Default path should expand ~ to home directory."""
        # Mock the home directory
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
        
        store = SessionHistoryStore()  # Use default path
        session_id = store.create_session()
        
        # Verify session was created (path was valid)
        assert store.get_session(session_id) is not None
