"""
Context usage tracking for RAG debugging and optimization.

Logs which chunks are retrieved and potentially used in answers,
enabling analysis of context utilization patterns over time.
"""

import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkUsageRecord:
    """Record of a chunk's usage in answer generation."""
    
    # Unique identifier for this usage event
    id: Optional[int] = None
    
    # Session and question context
    session_id: str = ""
    question: str = ""
    
    # Chunk details
    chunk_index: int = 0
    chunk_text: str = ""
    chunk_source: str = ""  # document type (resume, jd, etc.)
    
    # Retrieval metrics
    retrieval_distance: float = 0.0
    retrieval_rank: int = 0
    
    # Usage analysis
    was_used: bool = False
    overlap_ratio: float = 0.0
    
    # Timestamps
    retrieved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question": self.question[:100],
            "chunk_index": self.chunk_index,
            "chunk_source": self.chunk_source,
            "retrieval_distance": self.retrieval_distance,
            "retrieval_rank": self.retrieval_rank,
            "was_used": self.was_used,
            "overlap_ratio": self.overlap_ratio,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
        }


class ContextUsageTracker:
    """
    Tracks context chunk usage across sessions for analysis.
    
    Stores usage data in SQLite for lightweight, persistent tracking
    without external dependencies.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize the context usage tracker.
        
        Args:
            db_path: Path to SQLite database. Defaults to user data directory.
            enabled: Whether tracking is enabled.
        """
        self._enabled = enabled
        self._lock = threading.Lock()
        
        if db_path:
            self._db_path = Path(db_path)
        else:
            # Default to user data directory
            data_dir = Path.home() / ".live_interview_agent" / "analytics"
            data_dir.mkdir(parents=True, exist_ok=True)
            self._db_path = data_dir / "context_usage.db"
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the SQLite database schema."""
        if not self._enabled:
            return
            
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS chunk_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        chunk_text_preview TEXT,
                        chunk_source TEXT,
                        retrieval_distance REAL,
                        retrieval_rank INTEGER,
                        was_used BOOLEAN DEFAULT FALSE,
                        overlap_ratio REAL DEFAULT 0.0,
                        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS groundedness_scores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer_preview TEXT,
                        score REAL NOT NULL,
                        claim_count INTEGER DEFAULT 0,
                        supported_count INTEGER DEFAULT 0,
                        unsupported_count INTEGER DEFAULT 0,
                        context_utilization REAL DEFAULT 0.0,
                        latency_ms REAL DEFAULT 0.0,
                        evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for common queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunk_session 
                    ON chunk_usage(session_id)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_groundedness_session 
                    ON groundedness_scores(session_id)
                """)
                
                conn.commit()
                logger.info(f"Context usage tracker initialized at {self._db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize context usage tracker: {e}")
            self._enabled = False
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable tracking."""
        self._enabled = enabled
    
    def log_chunk_retrieval(
        self,
        session_id: str,
        question: str,
        chunks: List[Dict[str, Any]],
    ) -> None:
        """
        Log retrieved chunks for later analysis.
        
        Args:
            session_id: Current session ID.
            question: The question that triggered retrieval.
            chunks: List of chunk dictionaries with text, distance, source, etc.
        """
        if not self._enabled:
            return
            
        try:
            with self._lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    for i, chunk in enumerate(chunks):
                        conn.execute("""
                            INSERT INTO chunk_usage 
                            (session_id, question, chunk_index, chunk_text_preview, 
                             chunk_source, retrieval_distance, retrieval_rank)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            session_id,
                            question[:500],
                            i,
                            chunk.get("text", "")[:200],
                            chunk.get("source", chunk.get("document_type", "unknown")),
                            chunk.get("distance", 0.0),
                            i + 1,
                        ))
                    conn.commit()
                    
        except Exception as e:
            logger.warning(f"Failed to log chunk retrieval: {e}")
    
    def log_chunk_usage(
        self,
        session_id: str,
        question: str,
        usage_results: List[Dict[str, Any]],
    ) -> None:
        """
        Update chunk records with usage analysis results.
        
        Args:
            session_id: Current session ID.
            question: The question.
            usage_results: List of usage analysis results from ContextUtilizationResult.
        """
        if not self._enabled:
            return
            
        try:
            with self._lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    for result in usage_results:
                        conn.execute("""
                            UPDATE chunk_usage 
                            SET was_used = ?, overlap_ratio = ?
                            WHERE session_id = ? AND question = ? AND chunk_index = ?
                        """, (
                            result.get("overlap_ratio", 0) > 0.10,
                            result.get("overlap_ratio", 0),
                            session_id,
                            question[:500],
                            result.get("chunk_index", 0),
                        ))
                    conn.commit()
                    
        except Exception as e:
            logger.warning(f"Failed to log chunk usage: {e}")
    
    def log_groundedness_score(
        self,
        session_id: str,
        question: str,
        answer: str,
        score: float,
        claim_count: int = 0,
        supported_count: int = 0,
        unsupported_count: int = 0,
        context_utilization: float = 0.0,
        latency_ms: float = 0.0,
    ) -> None:
        """
        Log groundedness evaluation results.
        
        Args:
            session_id: Current session ID.
            question: The question.
            answer: The generated answer.
            score: Groundedness score (0-1).
            claim_count: Total claims identified.
            supported_count: Claims supported by context.
            unsupported_count: Claims not supported.
            context_utilization: Context utilization rate.
            latency_ms: Evaluation latency.
        """
        if not self._enabled:
            return
            
        try:
            with self._lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    conn.execute("""
                        INSERT INTO groundedness_scores 
                        (session_id, question, answer_preview, score, claim_count,
                         supported_count, unsupported_count, context_utilization, latency_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        question[:500],
                        answer[:300],
                        score,
                        claim_count,
                        supported_count,
                        unsupported_count,
                        context_utilization,
                        latency_ms,
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.warning(f"Failed to log groundedness score: {e}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get aggregated stats for a session.
        
        Args:
            session_id: Session ID to analyze.
            
        Returns:
            Dictionary with session statistics.
        """
        if not self._enabled:
            return {}
            
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                # Get groundedness stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as question_count,
                        AVG(score) as avg_groundedness,
                        AVG(context_utilization) as avg_utilization,
                        SUM(supported_count) as total_supported,
                        SUM(unsupported_count) as total_unsupported,
                        AVG(latency_ms) as avg_eval_latency
                    FROM groundedness_scores
                    WHERE session_id = ?
                """, (session_id,))
                row = cursor.fetchone()
                
                if not row or row[0] == 0:
                    return {"session_id": session_id, "question_count": 0}
                
                # Get chunk usage stats
                cursor2 = conn.execute("""
                    SELECT 
                        COUNT(*) as total_chunks,
                        SUM(CASE WHEN was_used THEN 1 ELSE 0 END) as used_chunks,
                        AVG(overlap_ratio) as avg_overlap
                    FROM chunk_usage
                    WHERE session_id = ?
                """, (session_id,))
                chunk_row = cursor2.fetchone()
                
                return {
                    "session_id": session_id,
                    "question_count": row[0],
                    "avg_groundedness": round(row[1] or 0, 3),
                    "avg_context_utilization": round(row[2] or 0, 3),
                    "total_supported_claims": row[3] or 0,
                    "total_unsupported_claims": row[4] or 0,
                    "avg_eval_latency_ms": round(row[5] or 0, 1),
                    "total_chunks_retrieved": chunk_row[0] if chunk_row else 0,
                    "chunks_actually_used": chunk_row[1] if chunk_row else 0,
                    "avg_chunk_overlap": round(chunk_row[2] or 0, 3) if chunk_row else 0,
                }
                
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"session_id": session_id, "error": str(e)}
    
    def get_aggregate_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get aggregated stats across all sessions for the last N days.
        
        Args:
            days: Number of days to include.
            
        Returns:
            Dictionary with aggregate statistics.
        """
        if not self._enabled:
            return {}
            
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(DISTINCT session_id) as session_count,
                        COUNT(*) as question_count,
                        AVG(score) as avg_groundedness,
                        MIN(score) as min_groundedness,
                        MAX(score) as max_groundedness,
                        AVG(context_utilization) as avg_utilization,
                        SUM(claim_count) as total_claims,
                        SUM(unsupported_count) as total_unsupported
                    FROM groundedness_scores
                    WHERE evaluated_at > datetime('now', ?)
                """, (f'-{days} days',))
                row = cursor.fetchone()
                
                if not row or row[0] == 0:
                    return {"period_days": days, "session_count": 0}
                
                return {
                    "period_days": days,
                    "session_count": row[0],
                    "question_count": row[1],
                    "avg_groundedness": round(row[2] or 0, 3),
                    "min_groundedness": round(row[3] or 0, 3),
                    "max_groundedness": round(row[4] or 0, 3),
                    "avg_context_utilization": round(row[5] or 0, 3),
                    "total_claims_analyzed": row[6] or 0,
                    "total_unsupported_claims": row[7] or 0,
                    "unsupported_claim_rate": round(
                        (row[7] or 0) / (row[6] or 1), 3
                    ),
                }
                
        except Exception as e:
            logger.error(f"Failed to get aggregate stats: {e}")
            return {"error": str(e)}
    
    def clear_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clear data older than specified days.
        
        Args:
            days_to_keep: Number of days of data to retain.
            
        Returns:
            Number of records deleted.
        """
        if not self._enabled:
            return 0
            
        try:
            with self._lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    cursor = conn.execute("""
                        DELETE FROM chunk_usage 
                        WHERE retrieved_at < datetime('now', ?)
                    """, (f'-{days_to_keep} days',))
                    chunk_deleted = cursor.rowcount
                    
                    cursor = conn.execute("""
                        DELETE FROM groundedness_scores 
                        WHERE evaluated_at < datetime('now', ?)
                    """, (f'-{days_to_keep} days',))
                    score_deleted = cursor.rowcount
                    
                    conn.commit()
                    
                    total = chunk_deleted + score_deleted
                    logger.info(f"Cleared {total} old tracking records")
                    return total
                    
        except Exception as e:
            logger.error(f"Failed to clear old data: {e}")
            return 0
    
    def close(self) -> None:
        """
        Close the tracker and release any resources.
        
        Should be called before deleting the database file in tests.
        """
        # SQLite connections are closed after each operation,
        # but we mark as disabled to prevent further writes
        self._enabled = False
