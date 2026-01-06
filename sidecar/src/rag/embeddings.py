from typing import List, Any
import google.generativeai as genai
from chromadb.utils.embedding_functions import EmbeddingFunction

class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Custom ChromaDB embedding function using Google Gemini.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini embedding function.
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = "models/text-embedding-004"

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embeddings (list of floats)
        """
        embeddings = []
        # Gemini API supports batching but has limits. 
        # For safety and simplicity, processing one by one or in small batches is better.
        # But 'embed_content' acts on a single content usually unless batched endpoint used.
        # Let's iterate.
        
        for text in input:
            try:
                # task_type="retrieval_document" is good for storing in DB
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            except Exception as e:
                # ChromaDB expects a list of equal length.
                # If one fails, we should probably raise or return zeros?
                # Raising is safer to detect issues.
                raise ValueError(f"Failed to generate embedding: {e}")
                
        return embeddings
