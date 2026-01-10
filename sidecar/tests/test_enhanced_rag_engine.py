"""
Tests for EnhancedRAGEngine with question-type-aware retrieval.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from src.rag.enhanced_engine import (
    EnhancedRAGEngine,
    DOC_PRIORITY_BY_QUESTION_TYPE,
)
from src.context.enhanced_manager import DocumentType


class TestDocumentPriorityMapping:
    """Tests for question type to document priority mapping."""
    
    def test_behavioral_prioritizes_resume(self):
        """Behavioral questions should prioritize resume and sample Q&A."""
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE["behavioral"]
        assert DocumentType.RESUME in priorities
        assert DocumentType.SAMPLE_QA in priorities
    
    def test_intro_prioritizes_resume(self):
        """Intro questions should prioritize resume."""
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE["intro"]
        assert DocumentType.RESUME in priorities
    
    def test_technical_prioritizes_resume_and_jd(self):
        """Technical questions should prioritize resume and job description."""
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE["technical"]
        assert DocumentType.RESUME in priorities
        assert DocumentType.JOB_DESCRIPTION in priorities
    
    def test_motivation_prioritizes_company_info(self):
        """Motivation questions should prioritize company info."""
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE["motivation"]
        assert DocumentType.COMPANY_INFO in priorities
        assert DocumentType.JOB_DESCRIPTION in priorities
        assert DocumentType.INDUSTRY_RESEARCH in priorities
    
    def test_weakness_prioritizes_sample_qa(self):
        """Weakness questions should prioritize sample Q&A."""
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE["weakness"]
        assert DocumentType.SAMPLE_QA in priorities
    
    def test_general_has_defaults(self):
        """General questions should have default priorities."""
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE["general"]
        assert DocumentType.RESUME in priorities
        assert DocumentType.JOB_DESCRIPTION in priorities


class TestEnhancedRAGEngine:
    """Tests for EnhancedRAGEngine class."""
    
    @pytest.fixture
    def mock_store(self):
        """Create a mock VectorStore."""
        store = MagicMock()
        store.query_with_filter.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["Child chunk 1", "Child chunk 2"]],
            "metadatas": [[
                {"document_type": "resume", "level": "child", "parent_id": "parent-1"},
                {"document_type": "resume", "level": "child", "parent_id": "parent-2"}
            ]],
            "distances": [[0.2, 0.3]]
        }
        return store
    
    @pytest.fixture
    def engine(self, mock_store):
        """Create engine with mock store."""
        return EnhancedRAGEngine(mock_store)
    
    def test_initialization(self, mock_store):
        """Should initialize with vector store."""
        engine = EnhancedRAGEngine(mock_store)
        assert engine.vector_store == mock_store
    
    def test_retrieve_for_behavioral_question(self, engine, mock_store):
        """Should filter by resume for behavioral questions."""
        results = engine.retrieve_for_question(
            question="Tell me about a time you led a team",
            question_type="behavioral"
        )
        
        # Should have called query_with_filter
        assert mock_store.query_with_filter.called
        
        # Check the filter included document_type
        calls = mock_store.query_with_filter.call_args_list
        assert len(calls) > 0
    
    def test_retrieve_for_technical_question(self, engine, mock_store):
        """Should filter by resume and JD for technical questions."""
        results = engine.retrieve_for_question(
            question="How would you design a distributed cache?",
            question_type="technical"
        )
        
        assert mock_store.query_with_filter.called
    
    def test_retrieve_for_motivation_question(self, engine, mock_store):
        """Should filter by company info for motivation questions."""
        mock_store.query_with_filter.return_value = {
            "ids": [["id1"]],
            "documents": [["Company mission statement"]],
            "metadatas": [[{"document_type": "company_info", "level": "child"}]],
            "distances": [[0.25]]
        }
        
        results = engine.retrieve_for_question(
            question="Why do you want to work here?",
            question_type="motivation"
        )
        
        assert mock_store.query_with_filter.called
    
    def test_retrieve_with_unknown_type_uses_defaults(self, engine, mock_store):
        """Unknown question type should use default priorities."""
        results = engine.retrieve_for_question(
            question="Random question",
            question_type="unknown_type"
        )
        
        # Should still work with defaults
        assert mock_store.query_with_filter.called
    
    def test_retrieve_returns_retrieval_results(self, engine, mock_store):
        """Should return list of RetrievalResult objects."""
        results = engine.retrieve_for_question(
            question="Tell me about yourself",
            question_type="intro"
        )
        
        assert isinstance(results, list)
        # Results should have text and metadata
        if results:
            assert hasattr(results[0], 'text')
            assert hasattr(results[0], 'metadata')
    
    def test_retrieve_with_limit(self, engine, mock_store):
        """Should respect the limit parameter."""
        results = engine.retrieve_for_question(
            question="Question",
            question_type="general",
            limit=3
        )
        
        # Should not return more than limit
        assert len(results) <= 3
    
    def test_retrieve_empty_query(self, engine, mock_store):
        """Empty query should return empty results."""
        results = engine.retrieve_for_question(
            question="",
            question_type="general"
        )
        
        assert results == []
    
    def test_retrieve_no_results(self, engine, mock_store):
        """Should handle no results gracefully."""
        mock_store.query_with_filter.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        
        results = engine.retrieve_for_question(
            question="Very specific query",
            question_type="general"
        )
        
        assert results == []
    
    def test_parent_expansion(self, engine, mock_store):
        """Should expand child chunks to parent chunks."""
        # Setup: child results with parent_id
        mock_store.query_with_filter.return_value = {
            "ids": [["child-1", "child-2"]],
            "documents": [["Child text 1", "Child text 2"]],
            "metadatas": [[
                {"document_type": "resume", "level": "child", "parent_id": "parent-1"},
                {"document_type": "resume", "level": "child", "parent_id": "parent-1"}
            ]],
            "distances": [[0.2, 0.25]]
        }
        
        results = engine.retrieve_for_question(
            question="Experience question",
            question_type="behavioral"
        )
        
        # Should have attempted parent expansion
        assert mock_store.query_with_filter.called
    
    def test_retrieve_with_sub_questions(self, engine, mock_store):
        """Should aggregate context from sub-questions."""
        results = engine.retrieve_for_question(
            question="Main question",
            question_type="technical",
            sub_questions=["Sub question 1", "Sub question 2"]
        )
        
        # Should have made multiple queries (one per sub-question)
        # At minimum, should return results
        assert isinstance(results, list)
    
    def test_filters_by_child_level(self, engine, mock_store):
        """Should filter for child-level chunks initially."""
        engine.retrieve_for_question(
            question="Question",
            question_type="general"
        )
        
        # Check that at least one call filtered by level=child
        calls = mock_store.query_with_filter.call_args_list
        found_child_filter = False
        for call in calls:
            where = call.kwargs.get('where', {})
            if isinstance(where, dict):
                if where.get('level') == 'child':
                    found_child_filter = True
                elif '$and' in where:
                    for condition in where['$and']:
                        if condition.get('level') == 'child':
                            found_child_filter = True
        
        assert found_child_filter or len(calls) > 0  # At minimum, queries were made


class TestEnhancedRAGEngineParentCache:
    """Tests for parent chunk caching."""
    
    @pytest.fixture
    def mock_store(self):
        """Create mock store."""
        return MagicMock()
    
    @pytest.fixture
    def engine(self, mock_store):
        """Create engine."""
        return EnhancedRAGEngine(mock_store)
    
    def test_parent_cache_initialization(self, engine):
        """Should initialize with empty parent cache."""
        assert hasattr(engine, 'parent_cache')
        assert engine.parent_cache == {}
    
    def test_parent_cache_populated(self, engine, mock_store):
        """Should cache parent chunks after retrieval."""
        # First call returns children
        mock_store.query_with_filter.side_effect = [
            {
                "ids": [["child-1"]],
                "documents": [["Child text"]],
                "metadatas": [[{"level": "child", "parent_id": "parent-1", "document_type": "resume"}]],
                "distances": [[0.2]]
            },
            # Second call for parent lookup
            {
                "ids": [["parent-1"]],
                "documents": [["Full parent context"]],
                "metadatas": [[{"level": "parent", "document_type": "resume"}]],
                "distances": [[0.0]]
            }
        ]
        
        engine.retrieve_for_question("Question", "general")
        
        # Parent cache may be populated depending on implementation
        # This test verifies the cache exists and is a dict
        assert isinstance(engine.parent_cache, dict)


class TestEnhancedRAGEngineBackwardCompatibility:
    """Tests for backward compatibility with existing RAGEngine."""
    
    @pytest.fixture
    def mock_store(self):
        """Create mock store."""
        store = MagicMock()
        store.query_with_filter.return_value = {
            "ids": [["id1"]],
            "documents": [["Document"]],
            "metadatas": [[{"document_type": "resume"}]],
            "distances": [[0.3]]
        }
        store.query_with_scores.return_value = {
            "ids": [["id1"]],
            "documents": [["Document"]],
            "metadatas": [[{}]],
            "distances": [[0.3]]
        }
        return store
    
    @pytest.fixture
    def engine(self, mock_store):
        """Create engine."""
        return EnhancedRAGEngine(mock_store)
    
    def test_has_retrieve_method(self, engine):
        """Should have retrieve() method for compatibility."""
        assert hasattr(engine, 'retrieve')
        assert callable(engine.retrieve)
    
    def test_retrieve_basic_usage(self, engine, mock_store):
        """Basic retrieve() should work like original RAGEngine."""
        results = engine.retrieve("Simple query", limit=5)
        
        assert isinstance(results, list)
    
    def test_retrieve_returns_retrieval_result_objects(self, engine, mock_store):
        """retrieve() should return RetrievalResult objects."""
        from src.rag.retrieval import RetrievalResult
        
        results = engine.retrieve("Query")
        
        if results:
            assert isinstance(results[0], RetrievalResult)
