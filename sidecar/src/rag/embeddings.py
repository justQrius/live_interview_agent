from typing import List, Any
import logging
import google.generativeai as genai
from chromadb.utils.embedding_functions import EmbeddingFunction
import concurrent.futures
import threading

logger = logging.getLogger(__name__)

class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Custom ChromaDB embedding function using Google Gemini.
    Includes timeout protection to prevent blocking the application.
    """
    
    def __init__(self, api_key: str, timeout: float = 10.0):
        """
        Initialize the Gemini embedding function.
        
        Args:
            api_key: Google Gemini API key
            timeout: Timeout in seconds for each embedding call (default 10s)
        """
        self.api_key = api_key
        self.timeout = timeout
        genai.configure(api_key=api_key)
        self.model = "models/text-embedding-004"

    def _embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text with timeout protection."""
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embeddings (list of floats)
            
        Raises:
            ValueError: If embedding generation fails or times out
        """
        embeddings = []
        
        for text in input:
            try:
                # Use ThreadPoolExecutor for timeout protection
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._embed_single, text)
                    try:
                        embedding = future.result(timeout=self.timeout)
                        embeddings.append(embedding)
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"Embedding timed out after {self.timeout}s, skipping")
                        raise ValueError(f"Embedding timed out after {self.timeout}s")
            except ValueError:
                # Re-raise ValueError (timeout or other validation errors)
                raise
            except Exception as e:
                # ChromaDB expects a list of equal length.
                # If one fails, we should probably raise or return zeros?
                # Raising is safer to detect issues.
                raise ValueError(f"Failed to generate embedding: {e}")
                
        return embeddings
