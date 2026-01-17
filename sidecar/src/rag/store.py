import chromadb
from chromadb.config import Settings
import pathlib
import uuid
import logging
from typing import List, Optional, Dict, Any
from .gemini_embeddings import GeminiEmbeddingFunction

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Manages the ChromaDB vector store for RAG.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the VectorStore.
        
        Args:
            api_key: Gemini API Key for embeddings.
        """
        self.api_key = api_key
        
        # Setup path: ~/.live_interview_agent/chroma/
        self.persist_path = pathlib.Path.home() / ".live_interview_agent" / "chroma"
        self.persist_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB at {self.persist_path}")

        # Disable telemetry to prevent PostHog timeout blocking
        settings = Settings(
            persist_directory=str(self.persist_path),
            anonymized_telemetry=False,
            allow_reset=True
        )
        self.client = chromadb.PersistentClient(path=str(self.persist_path), settings=settings)
        
        self.embedding_function = GeminiEmbeddingFunction(api_key=api_key)
        
        self.collection_name = "interview_context"
        try:
            self._get_collection()
        except Exception as e:
            logger.error(f"Failed to load collection: {e}. Resetting database...")
            try:
                self.client.reset()
                self._get_collection()
            except Exception as reset_error:
                logger.error(f"Failed to reset database: {reset_error}")
                # Fallback: Try to use a different collection name or just fail gracefully
                # If reset fails, we might need to manually delete files, but that's risky.
                # Re-raising original error if reset fails.
                raise e
        
    def _get_collection(self):
        """Get or create the collection."""
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )

    def add_documents(self, chunks: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of text chunks.
            metadatas: Optional list of metadata dicts corresponding to chunks.
        """
        if not chunks:
            return
            
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        logger.info(f"Adding {len(chunks)} documents to vector store")
        
        try:
            # Flatten metadata lists to strings for ChromaDB compatibility
            # ChromaDB only supports str, int, float, bool in metadata values
            processed_metadatas = []
            if metadatas:
                for meta in metadatas:
                    processed_meta = {}
                    for k, v in meta.items():
                        if isinstance(v, list):
                            # Join list items with comma
                            processed_meta[k] = ", ".join(str(item) for item in v)
                        else:
                            processed_meta[k] = v
                    processed_metadatas.append(processed_meta)
            
            self.collection.add(
                documents=chunks,
                metadatas=processed_metadatas,
                ids=ids
            )
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            raise
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            raise

    def query(self, text: str, n_results: int = 5) -> List[str]:
        """
        Query the vector store.
        
        Args:
            text: Query text.
            n_results: Number of results to return.
            
        Returns:
            List of matching text chunks.
        """
        try:
            results = self.query_with_scores(text, n_results)
            
            # ChromaDB returns list of lists (one per query)
            if results and results.get('documents'):
                return results['documents'][0]
            return []
            
        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            return []

    def query_with_scores(self, text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Query the vector store and return full results including scores/metadata.
        
        Args:
            text: Query text.
            n_results: Number of results to return.
            
        Returns:
            Dict containing 'ids', 'distances', 'metadatas', 'documents'.
        """
        try:
            return self.collection.query(
                query_texts=[text],
                n_results=n_results
            )
        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            return {}
    
    def query_with_filter(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query with metadata filtering.
        
        Enables filtering by document_type, level, section, or any metadata
        field before performing vector similarity search.
        
        Args:
            query: Search query text.
            n_results: Number of results to return (default 5).
            where: Metadata filter dict. Examples:
                - {"document_type": "resume"}
                - {"level": "child"}
                - {"$and": [{"document_type": "resume"}, {"level": "child"}]}
                - {"document_type": {"$in": ["resume", "job_description"]}}
            where_document: Document content filter. Example:
                - {"$contains": "Python"}
        
        Returns:
            Dict containing 'ids', 'distances', 'metadatas', 'documents'.
            
        Examples:
            # Get only resume chunks
            store.query_with_filter("Python experience", where={"document_type": "resume"})
            
            # Get child chunks from job descriptions
            store.query_with_filter(
                "requirements",
                where={"$and": [{"document_type": "job_description"}, {"level": "child"}]}
            )
            
            # Get chunks from specific section
            store.query_with_filter("skills", where={"section": "experience"})
        """
        try:
            return self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
        except Exception as e:
            logger.error(f"Failed to query ChromaDB with filter: {e}")
            return {}

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query text.
        
        Args:
            text: Query text.
            
        Returns:
            Embedding vector as list of floats.
        """
        try:
            embeddings = self.embedding_function(input=[text])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            return []
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []

    def embed_queries(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple query texts in a single batch call.
        
        This is more efficient than calling embed_query() multiple times
        as it makes a single API request for all texts.
        
        Args:
            texts: List of query texts to embed.
            
        Returns:
            List of embedding vectors (one per input text).
        """
        if not texts:
            return []
        try:
            embeddings = self.embedding_function(input=texts)
            return embeddings if embeddings else []
        except Exception as e:
            logger.error(f"Failed to batch embed queries: {e}")
            return []

    def query_with_embedding(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query using a pre-computed embedding vector.
        
        This avoids re-embedding the same query text multiple times
        when querying with different filters.
        
        Args:
            query_embedding: Pre-computed embedding vector.
            n_results: Number of results to return (default 5).
            where: Metadata filter dict (same as query_with_filter).
            where_document: Document content filter.
        
        Returns:
            Dict containing 'ids', 'distances', 'metadatas', 'documents'.
        """
        try:
            return self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
        except Exception as e:
            logger.error(f"Failed to query with embedding: {e}")
            return {}

    def clear(self) -> None:
        """Clear the vector store (delete collection and recreate)."""
        logger.info("Clearing vector store")
        try:
            self.client.delete_collection(self.collection_name)
            self._get_collection() # Recreate empty
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            # Try to recover by just getting/creating
            try:
                self._get_collection()
            except:
                pass

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by its ID.
        
        Used for parent chunk expansion - when a child chunk matches,
        retrieve its parent chunk for richer context.
        
        Args:
            doc_id: The document ID to retrieve.
            
        Returns:
            Dict with 'document', 'metadata', 'id' or None if not found.
        """
        try:
            result = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if result and result.get("ids") and len(result["ids"]) > 0:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result.get("documents") else None,
                    "metadata": result["metadatas"][0] if result.get("metadatas") else None
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document by ID {doc_id}: {e}")
            return None

    def get_by_ids(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple documents by their IDs.
        
        Batch version of get_by_id for efficiency when expanding
        multiple parent chunks.
        
        Args:
            doc_ids: List of document IDs to retrieve.
            
        Returns:
            List of dicts with 'document', 'metadata', 'id'.
        """
        if not doc_ids:
            return []
            
        try:
            result = self.collection.get(
                ids=doc_ids,
                include=["documents", "metadatas"]
            )
            
            docs = []
            if result and result.get("ids"):
                for i, doc_id in enumerate(result["ids"]):
                    docs.append({
                        "id": doc_id,
                        "document": result["documents"][i] if result.get("documents") else None,
                        "metadata": result["metadatas"][i] if result.get("metadatas") else None
                    })
            return docs
            
        except Exception as e:
            logger.error(f"Failed to get documents by IDs: {e}")
            return []
