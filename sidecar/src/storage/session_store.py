"""
Session History Store - SQLite-based session persistence.

Stores interview sessions, transcriptions, and generated answers
for later review and export.
"""

import json
import logging
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default database location
DEFAULT_DB_DIR = ".live_interview_agent"
DEFAULT_DB_NAME = "sessions.db"


@dataclass
class SessionSummary:
    """Summary information for a session (used in listing)."""
    id: str
    started_at: datetime
    ended_at: Optional[datetime]
    context_files: List[str]
    transcription_count: int
    answer_count: int


@dataclass
class SessionData:
    """Full session data including transcriptions and answers."""
    id: str
    started_at: datetime
    ended_at: Optional[datetime]
    context_files: List[str]
    transcriptions: List[Dict[str, Any]]
    answers: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionHistoryStore:
    """
    SQLite-based storage for interview session history.
    
    Thread-safe implementation using connection-per-thread pattern.
    Supports concurrent reads and writes.
    """

    # SQL schema for database tables
    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP,
        context_files TEXT,
        metadata TEXT
    );
    
    CREATE TABLE IF NOT EXISTS transcriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        speaker TEXT NOT NULL,
        text TEXT NOT NULL,
        timestamp REAL NOT NULL,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        confidence TEXT,
        rag_chunks TEXT,
        latency_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        claim_type TEXT NOT NULL,
        value TEXT NOT NULL,
        original_text TEXT,
        timestamp REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_transcriptions_session 
        ON transcriptions(session_id);
    CREATE INDEX IF NOT EXISTS idx_answers_session 
        ON answers(session_id);
    CREATE INDEX IF NOT EXISTS idx_claims_session 
        ON claims(session_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_started 
        ON sessions(started_at DESC);
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the session history store.
        
        Args:
            db_path: Path to SQLite database file.
                     Use ":memory:" for in-memory database (testing).
                     If None, uses default path ~/.live_interview_agent/sessions.db
        """
        if db_path is None:
            # Use default path in home directory
            home = Path.home()
            db_dir = home / DEFAULT_DB_DIR
            db_dir.mkdir(parents=True, exist_ok=True)
            self._db_path = str(db_dir / DEFAULT_DB_NAME)
        else:
            self._db_path = db_path
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Initialize schema
        self._init_db()
        
        logger.info(f"SessionHistoryStore initialized with database: {self._db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,  # We handle threading ourselves
                timeout=30.0  # Wait up to 30s for locks
            )
            # Enable foreign key constraints
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            if self._db_path != ":memory:":
                self._local.connection.execute("PRAGMA journal_mode = WAL")
        return self._local.connection

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.executescript(self._SCHEMA)
        conn.commit()

    def create_session(self, context_files: Optional[List[str]] = None) -> str:
        """
        Create a new session.
        
        Args:
            context_files: List of context file paths (resume, JD, etc.)
        
        Returns:
            The new session ID (UUID)
        """
        session_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()  # Store as ISO string
        context_json = json.dumps(context_files or [])
        metadata_json = json.dumps({})
        
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO sessions (id, started_at, context_files, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, started_at, context_json, metadata_json)
        )
        conn.commit()
        
        logger.debug(f"Created session: {session_id}")
        return session_id

    def end_session(self, session_id: str) -> None:
        """
        Mark a session as ended.
        
        Args:
            session_id: The session to end
        """
        ended_at = datetime.now().isoformat()  # Store as ISO string
        
        conn = self._get_connection()
        conn.execute(
            """
            UPDATE sessions SET ended_at = ? WHERE id = ?
            """,
            (ended_at, session_id)
        )
        conn.commit()
        
        logger.debug(f"Ended session: {session_id}")

    def add_transcription(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: float,
        confidence: Optional[float] = None
    ) -> None:
        """
        Record a transcription.
        
        Args:
            session_id: Session to add transcription to
            speaker: Speaker identifier (e.g., "Interviewer", "Candidate")
            text: Transcribed text
            timestamp: Timestamp in seconds from session start
            confidence: Optional STT confidence score
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO transcriptions (session_id, speaker, text, timestamp, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, speaker, text, timestamp, confidence)
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            logger.warning(f"Failed to add transcription (invalid session?): {e}")
            raise

    def add_answer(
        self,
        session_id: str,
        question: str,
        answer: str,
        confidence: Optional[str] = None,
        rag_chunks: Optional[List[str]] = None,
        latency_ms: Optional[int] = None
    ) -> None:
        """
        Record a generated answer.
        
        Args:
            session_id: Session to add answer to
            question: The question that was asked
            answer: The generated answer
            confidence: Confidence level (e.g., "high", "medium", "low")
            rag_chunks: List of RAG chunks used for context
            latency_ms: Answer generation latency in milliseconds
        """
        rag_json = json.dumps(rag_chunks) if rag_chunks else None
        
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO answers (session_id, question, answer, confidence, rag_chunks, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, question, answer, confidence, rag_json, latency_ms)
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            logger.warning(f"Failed to add answer (invalid session?): {e}")
            raise

    def add_claim(
        self,
        session_id: str,
        claim_type: str,
        value: str,
        original_text: str,
        timestamp: float
    ) -> None:
        """
        Record a factual claim made during the session.
        
        Args:
            session_id: Session ID
            claim_type: Type of claim (e.g. "experience_years")
            value: Normalized value (e.g. "5")
            original_text: Original text fragment
            timestamp: Time of claim
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO claims (session_id, claim_type, value, original_text, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, claim_type, value, original_text, timestamp)
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            logger.warning(f"Failed to add claim: {e}")

    def get_claims(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all factual claims for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of claim dictionaries
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT claim_type, value, original_text, timestamp
            FROM claims WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,)
        )
        return [
            {
                "claim_type": r[0],
                "value": r[1],
                "original_text": r[2],
                "timestamp": r[3]
            }
            for r in cursor.fetchall()
        ]

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get full session data including transcriptions and answers.
        
        Args:
            session_id: The session ID to retrieve
        
        Returns:
            SessionData if found, None otherwise
        """
        conn = self._get_connection()
        
        # Get session
        cursor = conn.execute(
            """
            SELECT id, started_at, ended_at, context_files, metadata
            FROM sessions WHERE id = ?
            """,
            (session_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        # Parse session data
        session_id, started_at, ended_at, context_json, metadata_json = row
        
        # Get transcriptions
        cursor = conn.execute(
            """
            SELECT speaker, text, timestamp, confidence, created_at
            FROM transcriptions WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,)
        )
        transcriptions = [
            {
                "speaker": r[0],
                "text": r[1],
                "timestamp": r[2],
                "confidence": r[3],
                "created_at": r[4]
            }
            for r in cursor.fetchall()
        ]
        
        # Get answers
        cursor = conn.execute(
            """
            SELECT question, answer, confidence, rag_chunks, latency_ms, created_at
            FROM answers WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,)
        )
        answers = [
            {
                "question": r[0],
                "answer": r[1],
                "confidence": r[2],
                "rag_chunks": json.loads(r[3]) if r[3] else None,
                "latency_ms": r[4],
                "created_at": r[5]
            }
            for r in cursor.fetchall()
        ]
        
        return SessionData(
            id=session_id,
            started_at=datetime.fromisoformat(started_at) if isinstance(started_at, str) else started_at,
            ended_at=datetime.fromisoformat(ended_at) if isinstance(ended_at, str) and ended_at else ended_at,
            context_files=json.loads(context_json) if context_json else [],
            transcriptions=transcriptions,
            answers=answers,
            metadata=json.loads(metadata_json) if metadata_json else {}
        )

    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[SessionSummary]:
        """
        List sessions with pagination, newest first.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
        
        Returns:
            List of SessionSummary objects
        """
        conn = self._get_connection()
        
        cursor = conn.execute(
            """
            SELECT 
                s.id,
                s.started_at,
                s.ended_at,
                s.context_files,
                (SELECT COUNT(*) FROM transcriptions t WHERE t.session_id = s.id) as trans_count,
                (SELECT COUNT(*) FROM answers a WHERE a.session_id = s.id) as ans_count
            FROM sessions s
            ORDER BY s.started_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        
        sessions = []
        for row in cursor.fetchall():
            session_id, started_at, ended_at, context_json, trans_count, ans_count = row
            sessions.append(SessionSummary(
                id=session_id,
                started_at=datetime.fromisoformat(started_at) if isinstance(started_at, str) else started_at,
                ended_at=datetime.fromisoformat(ended_at) if isinstance(ended_at, str) and ended_at else ended_at,
                context_files=json.loads(context_json) if context_json else [],
                transcription_count=trans_count,
                answer_count=ans_count
            ))
        
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all related data.
        
        Args:
            session_id: The session to delete
        
        Returns:
            True if session was deleted, False if not found
        """
        conn = self._get_connection()
        
        # Check if session exists
        cursor = conn.execute(
            "SELECT id FROM sessions WHERE id = ?",
            (session_id,)
        )
        if cursor.fetchone() is None:
            return False
        
        # Delete (cascades to transcriptions and answers due to foreign keys)
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        
        logger.debug(f"Deleted session: {session_id}")
        return True

    def close(self) -> None:
        """Close the database connection for this thread."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
