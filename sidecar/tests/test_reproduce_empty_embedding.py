
import pytest
from unittest.mock import MagicMock, patch
from src.rag.enhanced_engine import EnhancedRAGEngine
from src.rag.store import VectorStore
from src.rag.retrieval import RetrievalResult
from src.providers.gemini_client import GeminiClient
from src.rag.gemini_embeddings import GeminiEmbeddingFunction

@pytest.fixture
def mock_vector_store():
    store = MagicMock(spec=VectorStore)
    return store

def test_enhanced_rag_engine_parent_expansion_with_empty_query(mock_vector_store):
    """
    Verifies that _get_parent_text NO LONGER calls query_with_filter with an empty query.
    It should now use a placeholder query like "parent lookup".
    """
    # Setup
    engine = EnhancedRAGEngine(vector_store=mock_vector_store, context_manager=None)
    
    # Mock vector store return value
    mock_vector_store.query_with_filter.return_value = {"ids": [[]]}
    
    # Trigger the method
    result = engine._get_parent_text("some-parent-id")
    
    # It should NOT be called with empty string anymore
    # The fix we implemented changed query="" to query="parent lookup"
    mock_vector_store.query_with_filter.assert_called_with(
        query="parent lookup",
        n_results=1,
        where={"$and": [{"level": "parent"}, {"chunk_id": "some-parent-id"}]}
    )

def test_gemini_embedding_function_empty_string():
    """
    Verifies that GeminiEmbeddingFunction handles empty strings gracefully by replacing them
    with a space, instead of passing them to the API which would raise an error.
    """
    # Mock GeminiClient
    with patch("src.rag.gemini_embeddings.GeminiClient") as MockClient:
        mock_client_instance = MockClient.return_value
        
        # Capture what gets passed to embed_content
        # NOTE: The fix handles empty strings in GeminiClient.embed_content itself,
        # which calls _embed_content_with_retry with the processed list.
        # But we are mocking GeminiClient (the class), so its methods are replaced by Mocks.
        # This means the logic inside GeminiClient.embed_content is NOT executed.
        # We need to verify that GeminiEmbeddingFunction works correctly assuming GeminiClient works.
        
        # Actually, GeminiEmbeddingFunction calls self.client.embed_content.
        # Since we mock GeminiClient, we are mocking the method that contains the fix.
        # This is why the test fails - the mock doesn't execute the real method code.
        
        # To test the fix, we should treat GeminiClient as a real object (or partial mock)
        # OR we should verify that GeminiEmbeddingFunction does its own pre-processing 
        # (which it doesn't anymore, we moved logic to Client).
        
        # Let's adjust the test to verify GeminiClient.embed_content logic directly.
        from src.providers.gemini_client import GeminiClient
        
        # Create a real client but mock the internal _embed_content_with_retry
        client = GeminiClient(api_key="fake-key")
        client._embed_content_with_retry = MagicMock()
        client._embed_content_with_retry.return_value = [[0.1]*768] * 2
        
        # Call the method
        client.embed_content("model", ["valid", ""])
        
        # Verify _embed_content_with_retry received processed input
        call_args = client._embed_content_with_retry.call_args
        assert call_args, "Method was not called"
        
        # args[0] is model, args[1] is contents
        processed_contents = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]['contents']
        
        # Check that empty string was replaced by space
        assert processed_contents[1] == " ", "Empty string should be replaced by space"
        assert processed_contents[0] == "valid", "Valid string should be preserved"

