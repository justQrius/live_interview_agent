"""
Gemini Embedding Function for ChromaDB.

Uses the unified GeminiClient (google-genai SDK) for embeddings.
"""

import logging
import concurrent.futures
from typing import List, Union, Sequence, cast
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings, Embedding

from src.providers.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Custom ChromaDB embedding function using Google Gemini (via GeminiClient).
    Includes timeout protection.
    """
    
    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001", timeout: float = 10.0):
        """
        Initialize the Gemini embedding function.
        
        Args:
            api_key: Google Gemini API key
            model: Embedding model name (default: models/gemini-embedding-001)
            timeout: Timeout in seconds for each embedding call
        """
        self.client = GeminiClient(api_key=api_key)
        self.model = model
        self.timeout = timeout

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        return self.client.embed_content(
            model=self.model,
            contents=texts
        )

    def __call__(self, input: Documents) -> Embeddings:
        """
        Generate embeddings for a list of texts.
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embeddings (list of floats)
        """
        # Batch processing is much more efficient than single calls
        # The new SDK handles batching internally well, but we still wrap 
        # for timeout protection on the network call level.
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._embed_batch, input)
                result = future.result(timeout=self.timeout)
                return cast(Embeddings, result)
                
        except concurrent.futures.TimeoutError:
            logger.error(f"Embedding timed out after {self.timeout}s")
            raise ValueError(f"Embedding timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise ValueError(f"Failed to generate embeddings: {e}")
