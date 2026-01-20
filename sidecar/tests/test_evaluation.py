"""
Tests for the evaluation module (groundedness and context tracking).
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path

from src.evaluation.groundedness import (
    GroundednessEvaluator,
    GroundednessResult,
    ContextUtilizationResult,
)
from src.evaluation.context_tracker import (
    ContextUsageTracker,
    ChunkUsageRecord,
)


class TestGroundednessResult:
    """Tests for GroundednessResult dataclass."""
    
    def test_default_values(self):
        """Test default initialization."""
        result = GroundednessResult(score=0.8)
        assert result.score == 0.8
        assert result.claims == []
        assert result.claim_count == 0
        assert result.issues == []
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = GroundednessResult(
            score=0.85,
            claim_count=5,
            supported_count=4,
            unsupported_count=1,
            issues=["Missing context for claim X"],
            latency_ms=150.5,
        )
        d = result.to_dict()
        
        assert d["score"] == 0.85
        assert d["claim_count"] == 5
        assert d["supported_count"] == 4
        assert d["unsupported_count"] == 1
        assert "Missing context" in d["issues"][0]
        assert d["latency_ms"] == 150.5


class TestContextUtilizationResult:
    """Tests for ContextUtilizationResult dataclass."""
    
    def test_default_values(self):
        """Test default initialization."""
        result = ContextUtilizationResult(utilization_rate=0.75)
        assert result.utilization_rate == 0.75
        assert result.used_chunks == []
        assert result.unused_chunks == []
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = ContextUtilizationResult(
            utilization_rate=0.6,
            used_chunks=[0, 2, 3],
            unused_chunks=[1, 4],
        )
        d = result.to_dict()
        
        assert d["utilization_rate"] == 0.6
        assert d["used_chunk_count"] == 3
        assert d["unused_chunk_count"] == 2


class TestGroundednessEvaluator:
    """Tests for GroundednessEvaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator without LLM (uses heuristic fallback)."""
        return GroundednessEvaluator(llm_provider=None)
    
    def test_init_without_provider(self, evaluator):
        """Test initialization without LLM provider."""
        assert evaluator._llm_provider is None
        assert evaluator._enabled is True
    
    def test_set_enabled(self, evaluator):
        """Test enabling/disabling evaluation."""
        evaluator.set_enabled(False)
        assert evaluator._enabled is False
        
        evaluator.set_enabled(True)
        assert evaluator._enabled is True
    
    @pytest.mark.asyncio
    async def test_evaluate_empty_answer(self, evaluator):
        """Test evaluation with empty answer."""
        result = await evaluator.evaluate_groundedness(
            answer="",
            context="Some context here",
        )
        # Empty answer/context triggers early return with score 1.0
        assert result.score == 1.0
        assert "Empty" in result.issues[0]
    
    @pytest.mark.asyncio
    async def test_evaluate_empty_context(self, evaluator):
        """Test evaluation with empty context."""
        result = await evaluator.evaluate_groundedness(
            answer="Some answer",
            context="",
        )
        # Empty answer/context triggers early return
        # Score 0 when answer exists but no context to ground against
        assert result.score == 0.0
        assert "Empty" in result.issues[0]
    
    @pytest.mark.asyncio
    async def test_evaluate_disabled(self, evaluator):
        """Test evaluation when disabled returns -1 score."""
        evaluator.set_enabled(False)
        result = await evaluator.evaluate_groundedness(
            answer="Answer",
            context="Context",
        )
        assert result.score == -1.0
        assert "disabled" in result.issues[0].lower()
    
    @pytest.mark.asyncio
    async def test_heuristic_evaluation_grounded(self, evaluator):
        """Test heuristic evaluation with grounded answer."""
        context = """
        John worked at Google from 2020 to 2023.
        He led a team and achieved 40% improvement in performance.
        Technologies: Python, TensorFlow, Kubernetes.
        """
        answer = """
        At Google, I led a team that achieved significant improvements.
        We used Python and TensorFlow for our machine learning projects.
        The 40% performance improvement was a major milestone.
        """
        
        result = await evaluator.evaluate_groundedness(
            answer=answer,
            context=context,
        )
        
        # Should have high score - answer references context elements
        assert result.score > 0.5
    
    @pytest.mark.asyncio
    async def test_heuristic_evaluation_fabricated(self, evaluator):
        """Test heuristic evaluation with fabricated claims."""
        context = """
        John worked at a startup.
        He was a software engineer.
        """
        answer = """
        At Microsoft, I led a team of 50 engineers.
        We achieved 200% revenue growth and $10M in savings.
        I managed projects worth $5M each.
        """
        
        result = await evaluator.evaluate_groundedness(
            answer=answer,
            context=context,
        )
        
        # Should have lower score - many fabricated claims
        assert result.score < 0.8  # May not be 0 due to heuristic limitations
        assert result.unsupported_count > 0
    
    def test_analyze_context_utilization_all_used(self, evaluator):
        """Test utilization when all chunks are referenced."""
        chunks = [
            "I worked at Google as a software engineer",
            "Led a team of 5 engineers on the search project",
            "Achieved 30% latency improvement",
        ]
        answer = """
        At Google, I was a software engineer leading a team of 5 engineers.
        We worked on the search project and achieved a 30% latency improvement.
        """
        
        result = evaluator.analyze_context_utilization(answer, chunks)
        
        # Should have high utilization
        assert result.utilization_rate >= 0.5
        assert len(result.used_chunks) >= 2
    
    def test_analyze_context_utilization_partial(self, evaluator):
        """Test utilization when only some chunks are referenced."""
        chunks = [
            "Experience with Python and machine learning",
            "Worked on unrelated database project",
            "Led team on Python ML system",
        ]
        answer = "I have experience with Python and machine learning systems."
        
        result = evaluator.analyze_context_utilization(answer, chunks)
        
        # Should have some used, some unused
        assert result.utilization_rate > 0
        assert result.utilization_rate < 1.0
        assert len(result.overlap_details) == 3
    
    def test_analyze_context_utilization_empty(self, evaluator):
        """Test utilization with empty chunks."""
        result = evaluator.analyze_context_utilization("Some answer", [])
        assert result.utilization_rate == 1.0  # No chunks = full utilization


class TestContextUsageTracker:
    """Tests for ContextUsageTracker."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup - Windows may need a small delay
        import time
        time.sleep(0.1)
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except PermissionError:
            pass  # Ignore cleanup errors on Windows
    
    @pytest.fixture
    def tracker(self, temp_db):
        """Create tracker with temporary database."""
        t = ContextUsageTracker(db_path=temp_db)
        yield t
        t.close()  # Close before cleanup
    
    def test_init_creates_db(self, temp_db):
        """Test initialization creates database file."""
        tracker = ContextUsageTracker(db_path=temp_db)
        assert os.path.exists(temp_db)
    
    def test_set_enabled(self, tracker):
        """Test enabling/disabling tracking."""
        tracker.set_enabled(False)
        assert tracker._enabled is False
        
        tracker.set_enabled(True)
        assert tracker._enabled is True
    
    def test_log_chunk_retrieval(self, tracker):
        """Test logging chunk retrieval."""
        chunks = [
            {"text": "Chunk 1 content", "source": "resume", "distance": 0.2},
            {"text": "Chunk 2 content", "source": "jd", "distance": 0.4},
        ]
        
        # Should not raise
        tracker.log_chunk_retrieval(
            session_id="test_session",
            question="Tell me about yourself",
            chunks=chunks,
        )
    
    def test_log_groundedness_score(self, tracker):
        """Test logging groundedness score."""
        # Should not raise
        tracker.log_groundedness_score(
            session_id="test_session",
            question="Tell me about yourself",
            answer="I am a software engineer...",
            score=0.85,
            claim_count=5,
            supported_count=4,
            unsupported_count=1,
            context_utilization=0.75,
            latency_ms=120.5,
        )
    
    def test_get_session_stats_empty(self, tracker):
        """Test getting stats for non-existent session."""
        stats = tracker.get_session_stats("nonexistent")
        assert stats["question_count"] == 0
    
    def test_get_session_stats_with_data(self, tracker):
        """Test getting stats for session with data."""
        session_id = "test_session_stats"
        
        # Log some data
        tracker.log_groundedness_score(
            session_id=session_id,
            question="Q1",
            answer="A1",
            score=0.8,
            claim_count=3,
            supported_count=2,
            unsupported_count=1,
            context_utilization=0.6,
            latency_ms=100,
        )
        tracker.log_groundedness_score(
            session_id=session_id,
            question="Q2",
            answer="A2",
            score=0.9,
            claim_count=2,
            supported_count=2,
            unsupported_count=0,
            context_utilization=0.8,
            latency_ms=80,
        )
        
        stats = tracker.get_session_stats(session_id)
        
        assert stats["question_count"] == 2
        assert stats["avg_groundedness"] == 0.85  # (0.8 + 0.9) / 2
        assert stats["total_supported_claims"] == 4
        assert stats["total_unsupported_claims"] == 1
    
    def test_get_aggregate_stats(self, tracker):
        """Test getting aggregate stats."""
        # Log some data
        for i in range(3):
            tracker.log_groundedness_score(
                session_id=f"session_{i}",
                question=f"Question {i}",
                answer=f"Answer {i}",
                score=0.7 + (i * 0.1),
                claim_count=2,
                supported_count=1 + i,
                unsupported_count=1,
                context_utilization=0.5,
                latency_ms=100,
            )
        
        stats = tracker.get_aggregate_stats(days=7)
        
        assert stats["session_count"] == 3
        assert stats["question_count"] == 3
        assert stats["avg_groundedness"] >= 0.7
    
    def test_disabled_tracker(self, temp_db):
        """Test that disabled tracker doesn't write."""
        tracker = ContextUsageTracker(db_path=temp_db, enabled=False)
        
        # These should be no-ops
        tracker.log_groundedness_score(
            session_id="test",
            question="Q",
            answer="A",
            score=0.9,
        )
        
        stats = tracker.get_session_stats("test")
        assert stats == {}  # Should be empty when disabled
        
        tracker.close()


class TestChunkUsageRecord:
    """Tests for ChunkUsageRecord dataclass."""
    
    def test_default_values(self):
        """Test default initialization."""
        record = ChunkUsageRecord()
        assert record.id is None
        assert record.session_id == ""
        assert record.was_used is False
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        record = ChunkUsageRecord(
            session_id="sess1",
            question="Tell me about yourself",
            chunk_index=0,
            chunk_source="resume",
            retrieval_distance=0.25,
            was_used=True,
            overlap_ratio=0.45,
        )
        d = record.to_dict()
        
        assert d["session_id"] == "sess1"
        assert d["chunk_index"] == 0
        assert d["chunk_source"] == "resume"
        assert d["was_used"] is True
        assert d["overlap_ratio"] == 0.45


class TestEvaluationIntegration:
    """Integration tests for evaluation components."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        import time
        time.sleep(0.1)
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except PermissionError:
            pass
    
    @pytest.mark.asyncio
    async def test_full_evaluation_flow(self, temp_db):
        """Test complete evaluation and tracking flow."""
        evaluator = GroundednessEvaluator()
        tracker = ContextUsageTracker(db_path=temp_db)
        
        # Simulate answer generation
        question = "Tell me about a time you led a project"
        context_chunks = [
            "Led the migration project at Acme Corp in 2022",
            "Managed a team of 3 engineers for 6 months",
            "Achieved 50% reduction in deployment time",
        ]
        answer = "At Acme Corp in 2022, I led a migration project with a team of 3 engineers. Over 6 months, we achieved a 50% reduction in deployment time."
        
        session_id = "integration_test"
        
        # Track chunk retrieval
        tracker.log_chunk_retrieval(
            session_id=session_id,
            question=question,
            chunks=[
                {"text": c, "source": "resume", "distance": 0.2 + i * 0.1}
                for i, c in enumerate(context_chunks)
            ],
        )
        
        # Evaluate groundedness
        context_str = "\n\n".join(context_chunks)
        groundedness = await evaluator.evaluate_groundedness(
            answer=answer,
            context=context_str,
            question=question,
        )
        
        # Analyze utilization
        utilization = evaluator.analyze_context_utilization(answer, context_chunks)
        
        # Log results
        tracker.log_groundedness_score(
            session_id=session_id,
            question=question,
            answer=answer,
            score=groundedness.score,
            claim_count=groundedness.claim_count,
            supported_count=groundedness.supported_count,
            unsupported_count=groundedness.unsupported_count,
            context_utilization=utilization.utilization_rate,
            latency_ms=groundedness.latency_ms,
        )
        
        # Verify tracking
        stats = tracker.get_session_stats(session_id)
        assert stats["question_count"] == 1
        assert stats["avg_groundedness"] >= 0  # Some score was recorded
        
        # Cleanup
        tracker.close()
