import chromadb
from chromadb.config import Settings
import pathlib
import uuid
import logging
from typing import List, Optional, Dict, Any
from .embeddings import GeminiEmbeddingFunction

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
        self._get_collection()
        
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
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
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
