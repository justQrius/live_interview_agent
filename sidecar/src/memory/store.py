"""
SQLite-based Memory Store for persistent candidate context.

This module provides:
- Database creation and migrations
- CRUD operations for documents, facts, stories, profiles
- Session claim management for consistency tracking
- Thread-safe concurrent access via connection pooling
- Async wrappers for non-blocking access from async code
"""

import asyncio
import sqlite3
import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, TypeVar
from contextlib import contextmanager
from queue import Queue
from functools import wraps

# Type variable for generic async wrapper
T = TypeVar('T')

from .models import (
    ExtractedFacts,
    STARStory,
    CandidateProfile,
    SessionClaim,
    DocumentSummary,
    DocumentType,
    ClaimType,
)


logger = logging.getLogger(__name__)


# Schema version for migrations
SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    filename TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    section_summaries TEXT,  -- JSON
    key_points TEXT  -- JSON
);

-- Facts table (one-to-many with documents)
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    fact_type TEXT,  -- skill, career, achievement, education, etc.
    data TEXT NOT NULL,  -- JSON
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- STAR Stories table
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    title TEXT,
    situation TEXT,
    task TEXT,
    action TEXT,
    result TEXT,
    metrics TEXT,  -- JSON
    tags TEXT,  -- JSON
    source_company TEXT,
    source_role TEXT,
    opening_line TEXT,
    twenty_second_version TEXT,
    full_version TEXT,
    confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Candidate Profile table (singleton - only one active profile)
CREATE TABLE IF NOT EXISTS candidate_profile (
    id TEXT PRIMARY KEY,
    profile_text TEXT,
    current_role TEXT,
    total_experience_years INTEGER DEFAULT 0,
    core_skills TEXT,  -- JSON
    key_achievements TEXT,  -- JSON
    target_role TEXT,
    target_company TEXT,
    strengths TEXT,  -- JSON
    gaps TEXT,  -- JSON
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_documents TEXT  -- JSON
);

-- Session Claims for consistency tracking
CREATE TABLE IF NOT EXISTS session_claims (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    claim_text TEXT,
    claim_value TEXT,
    claim_type TEXT,
    context TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metadata table for schema versioning
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_facts_document_id ON facts(document_id);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_stories_tags ON stories(tags);
CREATE INDEX IF NOT EXISTS idx_claims_session ON session_claims(session_id);

-- FTS5 virtual table for full-text story search (Phase 4.1 optimization)
CREATE VIRTUAL TABLE IF NOT EXISTS stories_fts USING fts5(
    id UNINDEXED,
    title,
    situation,
    task,
    action,
    result,
    tags,
    content='stories',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync with stories table
CREATE TRIGGER IF NOT EXISTS stories_ai AFTER INSERT ON stories BEGIN
    INSERT INTO stories_fts(rowid, id, title, situation, task, action, result, tags)
    VALUES (NEW.rowid, NEW.id, NEW.title, NEW.situation, NEW.task, NEW.action, NEW.result, NEW.tags);
END;

CREATE TRIGGER IF NOT EXISTS stories_ad AFTER DELETE ON stories BEGIN
    INSERT INTO stories_fts(stories_fts, rowid, id, title, situation, task, action, result, tags)
    VALUES('delete', OLD.rowid, OLD.id, OLD.title, OLD.situation, OLD.task, OLD.action, OLD.result, OLD.tags);
END;

CREATE TRIGGER IF NOT EXISTS stories_au AFTER UPDATE ON stories BEGIN
    INSERT INTO stories_fts(stories_fts, rowid, id, title, situation, task, action, result, tags)
    VALUES('delete', OLD.rowid, OLD.id, OLD.title, OLD.situation, OLD.task, OLD.action, OLD.result, OLD.tags);
    INSERT INTO stories_fts(rowid, id, title, situation, task, action, result, tags)
    VALUES (NEW.rowid, NEW.id, NEW.title, NEW.situation, NEW.task, NEW.action, NEW.result, NEW.tags);
END;
"""


class ConnectionPool:
    """Thread-safe connection pool for SQLite."""

    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._initialized = False

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool or create a new one."""
        try:
            return self._pool.get_nowait()
        except Exception:
            return self._create_connection()

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        try:
            self._pool.put_nowait(conn)
        except Exception:
            # Pool is full, close the connection
            conn.close()

    def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                break


class MemoryStore:
    """
    Persistent memory store for candidate context.

    Stores extracted facts, STAR stories, candidate profiles, and session claims
    in a SQLite database for persistent access across sessions.
    """

    def __init__(self, db_path: Optional[str] = None, pool_size: int = 5):
        """
        Initialize the memory store.

        Args:
            db_path: Path to the SQLite database file. Defaults to ~/.live_interview_agent/memory.db
            pool_size: Number of connections in the pool
        """
        self.db_path = db_path or self._default_path()
        self._pool = ConnectionPool(self.db_path, pool_size)
        self._ensure_schema()
        logger.info(f"MemoryStore initialized at {self.db_path}")

    def _default_path(self) -> str:
        """Get the default database path."""
        home = Path.home()
        app_dir = home / ".live_interview_agent"
        app_dir.mkdir(parents=True, exist_ok=True)
        return str(app_dir / "memory.db")

    @contextmanager
    def _get_connection(self):
        """Context manager for getting/returning connections."""
        conn = self._pool.get_connection()
        try:
            yield conn
        finally:
            self._pool.return_connection(conn)

    def _ensure_schema(self) -> None:
        """Ensure the database schema exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(SCHEMA_SQL)

            # Set schema version
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION))
            )
            conn.commit()

    def close(self) -> None:
        """Close all database connections."""
        self._pool.close_all()

    # ===================
    # Document Operations
    # ===================

    def save_document_summary(self, summary: DocumentSummary) -> str:
        """
        Save a document summary.

        Args:
            summary: The DocumentSummary to save

        Returns:
            The document ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO documents (id, type, filename, uploaded_at, summary, section_summaries, key_points)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.document_id,
                    summary.document_type.value if isinstance(summary.document_type, DocumentType) else summary.document_type,
                    summary.filename,
                    summary.uploaded_at or datetime.now(),
                    summary.document_summary,
                    json.dumps(summary.section_summaries),
                    json.dumps(summary.key_points),
                )
            )
            conn.commit()
            return summary.document_id

    def get_document_summary(self, document_id: str) -> Optional[DocumentSummary]:
        """Get a document summary by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return DocumentSummary(
                document_id=row["id"],
                document_type=DocumentType(row["type"]) if row["type"] else DocumentType.OTHER,
                filename=row["filename"] or "",
                document_summary=row["summary"] or "",
                section_summaries=json.loads(row["section_summaries"]) if row["section_summaries"] else {},
                key_points=json.loads(row["key_points"]) if row["key_points"] else [],
                uploaded_at=row["uploaded_at"],
            )

    def get_all_document_summaries(self) -> List[DocumentSummary]:
        """Get all document summaries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
            rows = cursor.fetchall()

            return [
                DocumentSummary(
                    document_id=row["id"],
                    document_type=DocumentType(row["type"]) if row["type"] else DocumentType.OTHER,
                    filename=row["filename"] or "",
                    document_summary=row["summary"] or "",
                    section_summaries=json.loads(row["section_summaries"]) if row["section_summaries"] else {},
                    key_points=json.loads(row["key_points"]) if row["key_points"] else [],
                    uploaded_at=row["uploaded_at"],
                )
                for row in rows
            ]

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its associated facts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Delete associated facts first
            cursor.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))
            # Delete document
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_document_by_filename(self, filename: str) -> bool:
        """Delete a document by filename."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Find ID
            cursor.execute("SELECT id FROM documents WHERE filename = ?", (filename,))
            row = cursor.fetchone()
            if not row:
                return False
            
            document_id = row["id"]
            
            # Delete facts
            cursor.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))
            # Delete document
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()
            return True

    # ===================
    # Facts Operations
    # ===================

    def save_facts(self, document_id: str, facts: ExtractedFacts) -> None:
        """
        Save extracted facts for a document.

        Args:
            document_id: The document ID these facts came from
            facts: The ExtractedFacts to save
        """
        facts.document_id = document_id
        facts.extracted_at = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clear existing facts for this document
            cursor.execute("DELETE FROM facts WHERE document_id = ?", (document_id,))

            # Save each fact type
            fact_types = [
                ("skills", facts.skills),
                ("timeline", facts.timeline),
                ("achievements", facts.achievements),
                ("education", facts.education),
                ("certifications", facts.certifications),
                ("summary", {
                    "total_experience_years": facts.total_experience_years,
                    "current_role": facts.current_role,
                    "current_company": facts.current_company,
                    "industries": facts.industries,
                    "languages": facts.languages,
                }),
            ]

            for fact_type, data in fact_types:
                if data:  # Only save non-empty facts
                    import uuid
                    if isinstance(data, list):
                        data_to_save = [d.to_dict() if hasattr(d, 'to_dict') else d for d in data]
                    elif isinstance(data, dict):
                        data_to_save = data
                    else:
                        data_to_save = data

                    cursor.execute(
                        """
                        INSERT INTO facts (id, document_id, fact_type, data, extracted_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            document_id,
                            fact_type,
                            json.dumps(data_to_save),
                            datetime.now(),
                        )
                    )

            conn.commit()

    def get_facts_for_document(self, document_id: str) -> Optional[ExtractedFacts]:
        """Get extracted facts for a specific document."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT fact_type, data FROM facts WHERE document_id = ?",
                (document_id,)
            )
            rows = cursor.fetchall()

            if not rows:
                return None

            facts_data: Dict[str, Any] = {}
            for row in rows:
                fact_type = row["fact_type"]
                data = json.loads(row["data"])

                if fact_type == "summary":
                    facts_data.update(data)
                else:
                    facts_data[fact_type] = data

            facts_data["document_id"] = document_id
            return ExtractedFacts.from_dict(facts_data)

    def get_all_facts(self) -> ExtractedFacts:
        """
        Get all facts merged from all documents.

        Returns:
            Merged ExtractedFacts from all documents
        """
        all_facts: List[ExtractedFacts] = []

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT document_id FROM facts")
            doc_ids = [row["document_id"] for row in cursor.fetchall()]

        for doc_id in doc_ids:
            facts = self.get_facts_for_document(doc_id)
            if facts:
                all_facts.append(facts)

        if not all_facts:
            return ExtractedFacts()

        # Merge all facts
        merged = all_facts[0]
        for facts in all_facts[1:]:
            merged = merged.merge_with(facts)

        return merged

    # ===================
    # Story Operations
    # ===================

    def save_story(self, story: STARStory) -> str:
        """
        Save a STAR story.

        Args:
            story: The STARStory to save

        Returns:
            The story ID
        """
        now = datetime.now()
        if not story.created_at:
            story.created_at = now
        story.updated_at = now

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO stories
                (id, title, situation, task, action, result, metrics, tags,
                 source_company, source_role, opening_line, twenty_second_version,
                 full_version, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    story.id,
                    story.title,
                    story.situation,
                    story.task,
                    story.action,
                    story.result,
                    json.dumps(story.metrics),
                    json.dumps(story.tags),
                    story.source_company,
                    story.source_role,
                    story.opening_line,
                    story.twenty_second_version,
                    story.full_version,
                    story.confidence,
                    story.created_at,
                    story.updated_at,
                )
            )
            conn.commit()
            return story.id

    def get_story(self, story_id: str) -> Optional[STARStory]:
        """Get a story by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_story(row)

    def get_all_stories(self) -> List[STARStory]:
        """Get all STAR stories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stories ORDER BY created_at DESC")
            rows = cursor.fetchall()

            return [self._row_to_story(row) for row in rows]

    def get_stories_by_tag(self, tag: str) -> List[STARStory]:
        """Get stories that have a specific tag."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Use LIKE to search within JSON array
            cursor.execute(
                "SELECT * FROM stories WHERE tags LIKE ? ORDER BY confidence DESC",
                (f'%"{tag}"%',)
            )
            rows = cursor.fetchall()

            return [self._row_to_story(row) for row in rows]

    def search_stories_fts(self, query: str, limit: int = 10) -> List[STARStory]:
        """
        Full-text search for stories using FTS5.
        
        This is much faster than LIKE queries for text search.
        Uses SQLite FTS5 with BM25 ranking.
        
        Args:
            query: Search query (supports FTS5 syntax like "python OR java")
            limit: Maximum number of results
            
        Returns:
            List of matching stories, ranked by relevance
        """
        if not query or not query.strip():
            return []
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Use FTS5 MATCH with BM25 ranking
                cursor.execute(
                    """
                    SELECT stories.* FROM stories
                    JOIN stories_fts ON stories.id = stories_fts.id
                    WHERE stories_fts MATCH ?
                    ORDER BY bm25(stories_fts) 
                    LIMIT ?
                    """,
                    (query, limit)
                )
                rows = cursor.fetchall()
                return [self._row_to_story(row) for row in rows]
            except sqlite3.OperationalError as e:
                # FTS table might not exist (old database), fallback to LIKE
                logger.warning(f"FTS5 search failed, falling back to LIKE: {e}")
                return self._search_stories_fallback(query, limit)

    def _search_stories_fallback(self, query: str, limit: int = 10) -> List[STARStory]:
        """Fallback story search using LIKE when FTS5 is unavailable."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute(
                """
                SELECT * FROM stories 
                WHERE title LIKE ? OR situation LIKE ? OR task LIKE ? 
                      OR action LIKE ? OR result LIKE ? OR tags LIKE ?
                ORDER BY confidence DESC
                LIMIT ?
                """,
                (pattern, pattern, pattern, pattern, pattern, pattern, limit)
            )
            rows = cursor.fetchall()
            return [self._row_to_story(row) for row in rows]

    def delete_story(self, story_id: str) -> bool:
        """Delete a story by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_story(self, row: sqlite3.Row) -> STARStory:
        """Convert a database row to a STARStory."""
        return STARStory(
            id=row["id"],
            title=row["title"] or "",
            situation=row["situation"] or "",
            task=row["task"] or "",
            action=row["action"] or "",
            result=row["result"] or "",
            metrics=json.loads(row["metrics"]) if row["metrics"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            source_company=row["source_company"] or "",
            source_role=row["source_role"] or "",
            opening_line=row["opening_line"] or "",
            twenty_second_version=row["twenty_second_version"] or "",
            full_version=row["full_version"] or "",
            confidence=row["confidence"] or 0.0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ===================
    # Profile Operations
    # ===================

    def save_profile(self, profile: CandidateProfile) -> str:
        """
        Save or update the candidate profile.

        Note: Only one profile is maintained (singleton pattern).
        Saving a new profile replaces the existing one.

        Args:
            profile: The CandidateProfile to save

        Returns:
            The profile ID
        """
        profile.generated_at = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Delete existing profile (singleton)
            cursor.execute("DELETE FROM candidate_profile")

            cursor.execute(
                """
                INSERT INTO candidate_profile
                (id, profile_text, current_role, total_experience_years, core_skills,
                 key_achievements, target_role, target_company, strengths, gaps,
                 generated_at, source_documents)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.id,
                    profile.profile_text,
                    profile.current_role,
                    profile.total_experience_years,
                    json.dumps(profile.core_skills),
                    json.dumps(profile.key_achievements),
                    profile.target_role,
                    profile.target_company,
                    json.dumps(profile.strengths),
                    json.dumps(profile.gaps),
                    profile.generated_at,
                    json.dumps(profile.source_documents),
                )
            )
            conn.commit()
            return profile.id

    def get_profile(self) -> Optional[CandidateProfile]:
        """Get the current candidate profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidate_profile LIMIT 1")
            row = cursor.fetchone()

            if row is None:
                return None

            return CandidateProfile(
                id=row["id"],
                profile_text=row["profile_text"] or "",
                current_role=row["current_role"] or "",
                total_experience_years=row["total_experience_years"] or 0,
                core_skills=json.loads(row["core_skills"]) if row["core_skills"] else [],
                key_achievements=json.loads(row["key_achievements"]) if row["key_achievements"] else [],
                target_role=row["target_role"] or "",
                target_company=row["target_company"] or "",
                strengths=json.loads(row["strengths"]) if row["strengths"] else [],
                gaps=json.loads(row["gaps"]) if row["gaps"] else [],
                generated_at=row["generated_at"],
                source_documents=json.loads(row["source_documents"]) if row["source_documents"] else [],
            )

    def delete_profile(self) -> bool:
        """Delete the candidate profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM candidate_profile")
            conn.commit()
            return cursor.rowcount > 0

    # ===================
    # Session Claims
    # ===================

    def add_claim(
        self,
        session_id: str,
        claim_text: str,
        claim_value: str,
        claim_type: ClaimType = ClaimType.OTHER,
        context: str = ""
    ) -> str:
        """
        Log a claim made during an interview session.

        Args:
            session_id: The session ID
            claim_text: The text containing the claim
            claim_value: The extracted claim value (e.g., "8 years")
            claim_type: The type of claim
            context: Surrounding context

        Returns:
            The claim ID
        """
        import uuid
        claim_id = str(uuid.uuid4())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO session_claims
                (id, session_id, claim_text, claim_value, claim_type, context, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim_id,
                    session_id,
                    claim_text,
                    claim_value,
                    claim_type.value if isinstance(claim_type, ClaimType) else claim_type,
                    context,
                    datetime.now(),
                )
            )
            conn.commit()
            return claim_id

    def get_session_claims(self, session_id: str) -> List[SessionClaim]:
        """Get all claims for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM session_claims WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            rows = cursor.fetchall()

            return [
                SessionClaim(
                    id=row["id"],
                    session_id=row["session_id"],
                    claim_text=row["claim_text"] or "",
                    claim_value=row["claim_value"] or "",
                    claim_type=ClaimType(row["claim_type"]) if row["claim_type"] else ClaimType.OTHER,
                    context=row["context"] or "",
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]

    def clear_session_claims(self, session_id: str) -> int:
        """
        Clear all claims for a session.

        Args:
            session_id: The session ID

        Returns:
            Number of claims deleted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM session_claims WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            return cursor.rowcount

    def get_claims_by_type(self, session_id: str, claim_type: ClaimType) -> List[SessionClaim]:
        """Get claims of a specific type for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM session_claims WHERE session_id = ? AND claim_type = ? ORDER BY timestamp",
                (session_id, claim_type.value if isinstance(claim_type, ClaimType) else claim_type)
            )
            rows = cursor.fetchall()

            return [
                SessionClaim(
                    id=row["id"],
                    session_id=row["session_id"],
                    claim_text=row["claim_text"] or "",
                    claim_value=row["claim_value"] or "",
                    claim_type=ClaimType(row["claim_type"]) if row["claim_type"] else ClaimType.OTHER,
                    context=row["context"] or "",
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]

    # ===================
    # Utility Methods
    # ===================

    def clear_all(self) -> None:
        """Clear all data from the memory store. Use with caution!"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM session_claims")
            cursor.execute("DELETE FROM candidate_profile")
            cursor.execute("DELETE FROM stories")
            cursor.execute("DELETE FROM facts")
            cursor.execute("DELETE FROM documents")
            conn.commit()
            logger.warning("All data cleared from memory store")

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about stored data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}
            tables = ["documents", "facts", "stories", "candidate_profile", "session_claims"]

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                row = cursor.fetchone()
                stats[table] = row["count"] if row else 0

            return stats


class AsyncMemoryStore:
    """
    Async wrapper for MemoryStore.
    
    Provides non-blocking access to all MemoryStore operations by running
    them in a thread pool via asyncio.to_thread(). This prevents blocking
    the event loop in async WebSocket handlers.
    
    Usage:
        async_store = AsyncMemoryStore(memory_store)
        profile = await async_store.get_profile()
    """
    
    def __init__(self, store: MemoryStore):
        """
        Initialize async wrapper.
        
        Args:
            store: The underlying MemoryStore instance
        """
        self._store = store
    
    @property
    def sync_store(self) -> MemoryStore:
        """Access the underlying synchronous store."""
        return self._store
    
    # ===================
    # Document Operations
    # ===================
    
    async def save_document_summary(self, summary: DocumentSummary) -> str:
        """Save a document summary (async)."""
        return await asyncio.to_thread(self._store.save_document_summary, summary)
    
    async def get_document_summary(self, document_id: str) -> Optional[DocumentSummary]:
        """Get a document summary by ID (async)."""
        return await asyncio.to_thread(self._store.get_document_summary, document_id)
    
    async def get_all_document_summaries(self) -> List[DocumentSummary]:
        """Get all document summaries (async)."""
        return await asyncio.to_thread(self._store.get_all_document_summaries)
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its associated facts (async)."""
        return await asyncio.to_thread(self._store.delete_document, document_id)

    async def delete_document_by_filename(self, filename: str) -> bool:
        """Delete a document by filename (async)."""
        return await asyncio.to_thread(self._store.delete_document_by_filename, filename)
    
    # ===================
    # Facts Operations
    # ===================
    
    async def save_facts(self, document_id: str, facts: ExtractedFacts) -> None:
        """Save extracted facts for a document (async)."""
        return await asyncio.to_thread(self._store.save_facts, document_id, facts)
    
    async def get_facts_for_document(self, document_id: str) -> Optional[ExtractedFacts]:
        """Get extracted facts for a specific document (async)."""
        return await asyncio.to_thread(self._store.get_facts_for_document, document_id)
    
    async def get_all_facts(self) -> ExtractedFacts:
        """Get all facts merged from all documents (async)."""
        return await asyncio.to_thread(self._store.get_all_facts)
    
    # ===================
    # Story Operations
    # ===================
    
    async def save_story(self, story: STARStory) -> str:
        """Save a STAR story (async)."""
        return await asyncio.to_thread(self._store.save_story, story)
    
    async def get_story(self, story_id: str) -> Optional[STARStory]:
        """Get a story by ID (async)."""
        return await asyncio.to_thread(self._store.get_story, story_id)
    
    async def get_all_stories(self) -> List[STARStory]:
        """Get all STAR stories (async)."""
        return await asyncio.to_thread(self._store.get_all_stories)
    
    async def get_stories_by_tag(self, tag: str) -> List[STARStory]:
        """Get stories that have a specific tag (async)."""
        return await asyncio.to_thread(self._store.get_stories_by_tag, tag)
    
    async def delete_story(self, story_id: str) -> bool:
        """Delete a story by ID (async)."""
        return await asyncio.to_thread(self._store.delete_story, story_id)
    
    # ===================
    # Profile Operations
    # ===================
    
    async def save_profile(self, profile: CandidateProfile) -> str:
        """Save or update the candidate profile (async)."""
        return await asyncio.to_thread(self._store.save_profile, profile)
    
    async def get_profile(self) -> Optional[CandidateProfile]:
        """Get the current candidate profile (async)."""
        return await asyncio.to_thread(self._store.get_profile)
    
    async def delete_profile(self) -> bool:
        """Delete the candidate profile (async)."""
        return await asyncio.to_thread(self._store.delete_profile)
    
    # ===================
    # Session Claims
    # ===================
    
    async def add_claim(
        self,
        session_id: str,
        claim_text: str,
        claim_value: str,
        claim_type: ClaimType = ClaimType.OTHER,
        context: str = ""
    ) -> str:
        """Log a claim made during an interview session (async)."""
        return await asyncio.to_thread(
            self._store.add_claim,
            session_id, claim_text, claim_value, claim_type, context
        )
    
    async def get_session_claims(self, session_id: str) -> List[SessionClaim]:
        """Get all claims for a session (async)."""
        return await asyncio.to_thread(self._store.get_session_claims, session_id)
    
    async def clear_session_claims(self, session_id: str) -> int:
        """Clear all claims for a session (async)."""
        return await asyncio.to_thread(self._store.clear_session_claims, session_id)
    
    async def get_claims_by_type(self, session_id: str, claim_type: ClaimType) -> List[SessionClaim]:
        """Get claims of a specific type for a session (async)."""
        return await asyncio.to_thread(self._store.get_claims_by_type, session_id, claim_type)
    
    # ===================
    # Utility Methods
    # ===================
    
    async def clear_all(self) -> None:
        """Clear all data from the memory store (async)."""
        return await asyncio.to_thread(self._store.clear_all)
    
    async def get_stats(self) -> Dict[str, int]:
        """Get statistics about stored data (async)."""
        return await asyncio.to_thread(self._store.get_stats)
    
    def close(self) -> None:
        """Close all database connections."""
        self._store.close()
