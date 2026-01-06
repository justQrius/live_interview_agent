import pytest
from unittest.mock import MagicMock, patch
import numpy as np
import sys
import os
import pathlib

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import modules under test
# We will mock dependencies inside the tests or using patch decorators
from rag.embeddings import GeminiEmbeddingFunction
from rag.store import VectorStore

class TestGeminiEmbeddingFunction:
    @patch('rag.embeddings.genai')
    def test_init(self, mock_genai):
        api_key = "test_key"
        ef = GeminiEmbeddingFunction(api_key)
        assert ef.api_key == api_key
        mock_genai.configure.assert_called_with(api_key=api_key)

    @patch('rag.embeddings.genai')
    def test_call(self, mock_genai):
        api_key = "test_key"
        ef = GeminiEmbeddingFunction(api_key)
        
        texts = ["hello", "world"]
        
        # Configure mock to return a dict with 'embedding' key containing floats
        # genai.embed_content returns a dict
        mock_genai.embed_content.return_value = {'embedding': [0.1, 0.2, 0.3]}
        
        embeddings = ef(texts)
        
        assert len(embeddings) == 2
        # Use assert_allclose for floating point comparison
        np.testing.assert_allclose(embeddings[0], [0.1, 0.2, 0.3])
        
        # Verify calls
        assert mock_genai.embed_content.call_count >= 1

class TestVectorStore:
    @pytest.fixture
    def mock_chroma_client(self):
        with patch('rag.store.chromadb.PersistentClient') as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_embedding_function(self):
        with patch('rag.store.GeminiEmbeddingFunction') as mock_cls:
            # Create a mock instance that returns valid embeddings when called
            mock_ef = MagicMock()
            mock_ef.return_value = [[0.1, 0.2], [0.1, 0.2]] # For list input
            mock_cls.return_value = mock_ef
            yield mock_ef

    def test_init(self, mock_chroma_client, mock_embedding_function, tmp_path):
        api_key = "test_key"
        
        # Mock pathlib.Path.home to return tmp_path
        with patch('pathlib.Path.home', return_value=tmp_path):
            store = VectorStore(api_key)
            
            # Verify client init
            store.client.get_or_create_collection.assert_called()
            
            call_args = store.client.get_or_create_collection.call_args
            assert call_args[1]['name'] == 'interview_context'
            # Check embedding function is our mock instance
            assert call_args[1]['embedding_function'] == mock_embedding_function

    def test_add_documents(self, mock_chroma_client, mock_embedding_function, tmp_path):
        with patch('pathlib.Path.home', return_value=tmp_path):
            store = VectorStore("key")
            # store.collection is the return value of get_or_create_collection
            mock_collection = store.collection
            
            chunks = ["chunk1", "chunk2"]
            store.add_documents(chunks)
            
            mock_collection.add.assert_called_once()
            call_kwargs = mock_collection.add.call_args[1]
            assert call_kwargs['documents'] == chunks
            assert len(call_kwargs['ids']) == 2

    def test_query(self, mock_chroma_client, mock_embedding_function, tmp_path):
        with patch('pathlib.Path.home', return_value=tmp_path):
            store = VectorStore("key")
            mock_collection = store.collection
            
            # Mock query response
            mock_collection.query.return_value = {
                'documents': [['doc1', 'doc2']],
                'distances': [[0.1, 0.2]],
                'ids': [['id1', 'id2']]
            }
            
            results = store.query("query", n_results=3)
            
            mock_collection.query.assert_called_once()
            call_kwargs = mock_collection.query.call_args[1]
            assert call_kwargs['query_texts'] == ["query"]
            assert call_kwargs['n_results'] == 3
            
            assert results == ['doc1', 'doc2']

    def test_clear(self, mock_chroma_client, mock_embedding_function, tmp_path):
        with patch('pathlib.Path.home', return_value=tmp_path):
            store = VectorStore("key")
            
            store.clear()
            
            store.client.delete_collection.assert_called_with("interview_context")
            # Should recreate
            assert store.client.get_or_create_collection.call_count == 2 # Once in init, once in clear
