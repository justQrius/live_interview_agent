import logging
from typing import List
from .store import VectorStore
from .retrieval import RetrievalResult, confidence_from_distance

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Core RAG Engine that handles retrieval and result processing.
    """
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize the RAG Engine.
        
        Args:
            vector_store: The VectorStore instance to use for retrieval.
        """
        self.vector_store = vector_store

    def retrieve(self, query: str, limit: int = 5) -> List[RetrievalResult]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: The question or query string.
            limit: Maximum number of results to return.
            
        Returns:
            List of RetrievalResult objects, sorted by distance (ascending).
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to RAG Engine")
            return []
            
        try:
            results = self.vector_store.query_with_scores(query, n_results=limit)
            
            # Check if we got valid results
            # ChromaDB returns lists of lists (one per query)
            if not results or not results.get('ids') or not results['ids'][0]:
                logger.info("No results found in vector store")
                return []
            
            # Parse results
            # We assume single query, so we take index 0 of the lists
            ids = results['ids'][0]
            distances = results['distances'][0] if results.get('distances') else []
            metadatas = results['metadatas'][0] if results.get('metadatas') else []
            documents = results['documents'][0] if results.get('documents') else []
            
            retrieval_results = []
            
            # Zip everything together
            for i in range(len(ids)):
                # Handle cases where distances might be missing (though unlikely if query succeeded)
                dist = distances[i] if i < len(distances) else 1.0
                text = documents[i] if i < len(documents) else ""
                meta = metadatas[i] if i < len(metadatas) else {}
                
                # Convert distance to confidence
                confidence = confidence_from_distance(dist)
                
                result = RetrievalResult(
                    text=text,
                    distance=dist,
                    confidence=confidence,
                    metadata=meta or {}
                )
                retrieval_results.append(result)
                
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []
