from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator, Union, Optional
from dataclasses import dataclass

@dataclass
class TranscriptionResult:
    """
    Standardized result from an STT provider.
    """
    text: str
    confidence: float = 0.0
    speaker: Optional[str] = None
    language: str = "en"

class STTProvider(ABC):
    """
    Abstract Base Class for Speech-to-Text providers.
    """
    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes (PCM, wav, etc as supported by provider)
            language: Language code (default "en")
            
        Returns:
            TranscriptionResult object
        """
        pass

class LLMProvider(ABC):
    """
    Abstract Base Class for Large Language Model providers.
    """
    @abstractmethod
    async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            prompt: The user query or current prompt
            context: Retrieved context from RAG
            history: Conversation history (list of dicts with 'role' and 'content')
            
        Yields:
            String chunks of the response
        """
        pass

class EmbeddingProvider(ABC):
    """
    Abstract Base Class for Embedding providers.
    """
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for a single text string.
        """
        pass
    
    @abstractmethod
    async def batch_embed_text(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings.
        """
        pass
