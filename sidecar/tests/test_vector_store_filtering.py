"""
Tests for VectorStore metadata filtering capabilities.
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid

from src.rag.store import VectorStore


class TestVectorStoreMetadataFiltering:
    """Tests for metadata-driven filtering in VectorStore."""
    
    @pytest.fixture
    def mock_chromadb(self):
        """Mock ChromaDB to avoid actual database operations."""
        with patch("src.rag.store.chromadb") as mock_chroma:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_chroma.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_collection
            
            yield {
                "chromadb": mock_chroma,
                "client": mock_client,
                "collection": mock_collection
            }
    
    @pytest.fixture
    def mock_embedding(self):
        """Mock embedding function."""
        with patch("src.rag.store.GeminiEmbeddingFunction") as mock_embed:
            mock_embed.return_value = MagicMock()
            yield mock_embed
    
    @pytest.fixture
    def store(self, mock_chromadb, mock_embedding):
        """Create a VectorStore with mocked dependencies."""
        store = VectorStore(api_key="test-api-key")
        return store
    
    def test_add_documents_with_metadata(self, store, mock_chromadb):
        """Should add documents with rich metadata."""
        texts = ["Python experience", "Machine learning skills"]
        metadatas = [
            {
                "document_type": "resume",
                "level": "child",
                "parent_id": "parent-1",
                "section": "experience",
                "source": "resume.pdf"
            },
            {
                "document_type": "resume",
                "level": "child",
                "parent_id": "parent-1",
                "section": "skills",
                "source": "resume.pdf"
            }
        ]
        
        store.add_documents(texts, metadatas)
        
        # Verify ChromaDB was called with metadata
        mock_chromadb["collection"].add.assert_called_once()
        call_args = mock_chromadb["collection"].add.call_args
        assert call_args.kwargs["metadatas"] == metadatas
    
    def test_query_with_filter_by_document_type(self, store, mock_chromadb):
        """Should filter query results by document_type."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["Resume content", "More resume"]],
            "metadatas": [[{"document_type": "resume"}, {"document_type": "resume"}]],
            "distances": [[0.1, 0.2]]
        }
        
        results = store.query_with_filter(
            "Python experience",
            n_results=5,
            where={"document_type": "resume"}
        )
        
        # Verify filter was passed to ChromaDB
        mock_chromadb["collection"].query.assert_called_once()
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["where"] == {"document_type": "resume"}
    
    def test_query_with_filter_by_level(self, store, mock_chromadb):
        """Should filter query results by chunk level."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1"]],
            "documents": [["Child chunk content"]],
            "metadatas": [[{"level": "child"}]],
            "distances": [[0.15]]
        }
        
        results = store.query_with_filter(
            "skills",
            n_results=3,
            where={"level": "child"}
        )
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["where"] == {"level": "child"}
    
    def test_query_with_combined_filters(self, store, mock_chromadb):
        """Should support AND filtering with multiple conditions."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1"]],
            "documents": [["Filtered content"]],
            "metadatas": [[{"document_type": "resume", "level": "child"}]],
            "distances": [[0.1]]
        }
        
        where_filter = {
            "$and": [
                {"document_type": "resume"},
                {"level": "child"}
            ]
        }
        
        results = store.query_with_filter(
            "experience",
            n_results=5,
            where=where_filter
        )
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["where"] == where_filter
    
    def test_query_with_in_filter(self, store, mock_chromadb):
        """Should support $in filter for multiple values."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["Resume", "JD"]],
            "metadatas": [[{"document_type": "resume"}, {"document_type": "job_description"}]],
            "distances": [[0.1, 0.2]]
        }
        
        where_filter = {
            "document_type": {"$in": ["resume", "job_description"]}
        }
        
        results = store.query_with_filter(
            "Python",
            where=where_filter
        )
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["where"] == where_filter
    
    def test_query_with_filter_no_matches(self, store, mock_chromadb):
        """Should return empty results when filter matches nothing."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        
        results = store.query_with_filter(
            "nonexistent",
            where={"document_type": "industry_research"}
        )
        
        assert results.get("documents", [[]])[0] == []
    
    def test_query_with_filter_returns_full_results(self, store, mock_chromadb):
        """Should return full result structure including metadata."""
        expected_results = {
            "ids": [["id1", "id2"]],
            "documents": [["Doc 1", "Doc 2"]],
            "metadatas": [[
                {"document_type": "resume", "section": "experience"},
                {"document_type": "resume", "section": "skills"}
            ]],
            "distances": [[0.1, 0.2]]
        }
        mock_chromadb["collection"].query.return_value = expected_results
        
        results = store.query_with_filter(
            "Python",
            where={"document_type": "resume"}
        )
        
        assert results == expected_results
        assert "metadatas" in results
        assert "distances" in results
    
    def test_query_with_filter_default_n_results(self, store, mock_chromadb):
        """Should use default n_results when not specified."""
        mock_chromadb["collection"].query.return_value = {"ids": [[]], "documents": [[]]}
        
        store.query_with_filter("query", where={"level": "parent"})
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["n_results"] == 5
    
    def test_query_with_filter_custom_n_results(self, store, mock_chromadb):
        """Should respect custom n_results parameter."""
        mock_chromadb["collection"].query.return_value = {"ids": [[]], "documents": [[]]}
        
        store.query_with_filter("query", n_results=10, where={"level": "child"})
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["n_results"] == 10
    
    def test_query_without_filter_still_works(self, store, mock_chromadb):
        """Should work without any filter (backward compatible)."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1"]],
            "documents": [["Content"]],
            "metadatas": [[{}]],
            "distances": [[0.1]]
        }
        
        results = store.query_with_filter("query")
        
        call_args = mock_chromadb["collection"].query.call_args
        # where should be None or not passed
        assert call_args.kwargs.get("where") is None
    
    def test_query_with_where_document_filter(self, store, mock_chromadb):
        """Should support where_document for content-based filtering."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1"]],
            "documents": [["Python programming experience"]],
            "metadatas": [[{"document_type": "resume"}]],
            "distances": [[0.1]]
        }
        
        results = store.query_with_filter(
            "programming",
            where_document={"$contains": "Python"}
        )
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["where_document"] == {"$contains": "Python"}
    
    def test_query_with_section_filter(self, store, mock_chromadb):
        """Should filter by section metadata."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1"]],
            "documents": [["Work experience details"]],
            "metadatas": [[{"section": "experience"}]],
            "distances": [[0.1]]
        }
        
        results = store.query_with_filter(
            "work history",
            where={"section": "experience"}
        )
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["where"] == {"section": "experience"}
    
    def test_get_parent_chunks_for_children(self, store, mock_chromadb):
        """Should be able to get parent chunks given child matches."""
        # First query returns children with parent_id
        mock_chromadb["collection"].query.return_value = {
            "ids": [["child-1", "child-2"]],
            "documents": [["Child text 1", "Child text 2"]],
            "metadatas": [[
                {"level": "child", "parent_id": "parent-1"},
                {"level": "child", "parent_id": "parent-2"}
            ]],
            "distances": [[0.1, 0.2]]
        }
        
        # Get children first
        child_results = store.query_with_filter(
            "Python",
            where={"level": "child"}
        )
        
        # Extract parent IDs
        parent_ids = [m["parent_id"] for m in child_results["metadatas"][0]]
        assert parent_ids == ["parent-1", "parent-2"]
    
    def test_filter_by_source_file(self, store, mock_chromadb):
        """Should filter by source filename."""
        mock_chromadb["collection"].query.return_value = {
            "ids": [["id1"]],
            "documents": [["Resume content"]],
            "metadatas": [[{"source": "john_resume.pdf"}]],
            "distances": [[0.1]]
        }
        
        results = store.query_with_filter(
            "experience",
            where={"source": "john_resume.pdf"}
        )
        
        call_args = mock_chromadb["collection"].query.call_args
        assert call_args.kwargs["where"] == {"source": "john_resume.pdf"}


class TestVectorStoreMetadataValidation:
    """Tests for metadata validation."""
    
    @pytest.fixture
    def mock_chromadb(self):
        """Mock ChromaDB."""
        with patch("src.rag.store.chromadb") as mock_chroma:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_chroma.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_collection
            yield {"collection": mock_collection}
    
    @pytest.fixture
    def mock_embedding(self):
        """Mock embedding function."""
        with patch("src.rag.store.GeminiEmbeddingFunction") as mock_embed:
            mock_embed.return_value = MagicMock()
            yield mock_embed
    
    @pytest.fixture
    def store(self, mock_chromadb, mock_embedding):
        """Create store."""
        return VectorStore(api_key="test-key")
    
    def test_add_documents_with_empty_metadata(self, store, mock_chromadb):
        """Should accept documents with empty metadata."""
        store.add_documents(["text"], [{}])
        mock_chromadb["collection"].add.assert_called_once()
    
    def test_add_documents_without_metadata(self, store, mock_chromadb):
        """Should accept documents without metadata (None)."""
        store.add_documents(["text"])
        mock_chromadb["collection"].add.assert_called_once()
