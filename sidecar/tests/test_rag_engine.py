import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from rag.engine import RAGEngine
from rag.retrieval import RetrievalResult, confidence_from_distance
from protocol import ConfidenceLevel

def test_confidence_from_distance():
    # Test High confidence (< 0.35)
    assert confidence_from_distance(0.1) == ConfidenceLevel.HIGH
    assert confidence_from_distance(0.34) == ConfidenceLevel.HIGH

    # Test Medium confidence (< 0.65)
    assert confidence_from_distance(0.35) == ConfidenceLevel.MEDIUM
    assert confidence_from_distance(0.5) == ConfidenceLevel.MEDIUM
    assert confidence_from_distance(0.64) == ConfidenceLevel.MEDIUM

    # Test Low confidence (>= 0.65)
    assert confidence_from_distance(0.65) == ConfidenceLevel.LOW
    assert confidence_from_distance(0.8) == ConfidenceLevel.LOW
    assert confidence_from_distance(1.5) == ConfidenceLevel.LOW

class TestRAGEngine:
    @pytest.fixture
    def mock_vector_store(self):
        return MagicMock()

    @pytest.fixture
    def engine(self, mock_vector_store):
        return RAGEngine(vector_store=mock_vector_store)

    def test_retrieve_happy_path(self, engine, mock_vector_store):
        # Setup mock return values
        # ChromaDB query returns: {'ids': [...], 'distances': [...], 'metadatas': [...], 'documents': [...]}
        # But VectorStore.query() wrapper returns just List[str] in the current implementation.
        # Wait, I need to check VectorStore.query implementation in store.py.
        # It currently returns List[str]. 
        # Requirement says: "Wraps VectorStore". "Method retrieve(query: str, limit: int = 5) -> List[RetrievalResult]".
        # AND "Implement logic to convert ChromaDB distances to confidence levels".
        
        # Issue: The current VectorStore.query() only returns documents (List[str]).
        # It swallows distances and metadata.
        # I will need to modify VectorStore.query OR add a new method VectorStore.query_with_scores 
        # to get the distances for the confidence calculation.
        # The prompt didn't explicitly say to modify store.py, but it's implied if I need distances.
        # Actually, let's look at `sidecar/src/rag/store.py` again.
        pass

    def test_retrieve_empty_query(self, engine):
        results = engine.retrieve("")
        assert results == []

    def test_retrieve_no_results(self, engine, mock_vector_store):
        # Mock returning empty lists
        mock_vector_store.query_with_scores.return_value = {
            'ids': [[]],
            'distances': [[]],
            'metadatas': [[]],
            'documents': [[]]
        }
        
        results = engine.retrieve("test")
        assert results == []

    def test_retrieve_with_scores(self, engine, mock_vector_store):
        # Mock return data
        mock_vector_store.query_with_scores.return_value = {
            'ids': [['id1', 'id2']],
            'distances': [[0.2, 0.6]],
            'metadatas': [[{'source': 'doc1'}, {'source': 'doc2'}]],
            'documents': [['content1', 'content2']]
        }
        
        results = engine.retrieve("test query")
        
        assert len(results) == 2
        
        # Check first result (High confidence)
        r1 = results[0]
        assert r1.text == 'content1'
        assert r1.distance == 0.2
        assert r1.confidence == ConfidenceLevel.HIGH
        assert r1.metadata == {'source': 'doc1'}
        
        # Check second result (Medium confidence)
        r2 = results[1]
        assert r2.text == 'content2'
        assert r2.distance == 0.6
        assert r2.confidence == ConfidenceLevel.MEDIUM
