from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator, Union, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

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

    def is_available(self) -> bool:
        """
        Check if the provider is available and ready to use.

        Default implementation returns True. Subclasses can override
        to check API keys, network connectivity, etc.

        Returns:
            True if provider is ready to accept requests
        """
        return True

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
    
    Supports candidate profile injection for personalized responses.
    """
    
    # Maximum tokens for injected profile (conservative estimate)
    MAX_PROFILE_TOKENS = 1000
    
    def __init__(self):
        """Initialize base LLM provider with profile support."""
        self._candidate_profile: Optional[str] = None
    
    @property
    def candidate_profile(self) -> Optional[str]:
        """Get the current candidate profile."""
        return self._candidate_profile
    
    def set_candidate_profile(self, profile: Optional[str]) -> None:
        """
        Set the candidate profile for prompt injection.
        
        The profile will be included at the start of all LLM calls
        to maintain consistent understanding of the candidate.
        
        Args:
            profile: Profile text (~1000 tokens) or None to clear
        """
        if profile:
            # Estimate token count (conservative: ~4 chars per token)
            estimated_tokens = len(profile) / 4
            if estimated_tokens > self.MAX_PROFILE_TOKENS * 1.5:
                logger.warning(
                    f"Profile exceeds recommended token limit "
                    f"({estimated_tokens:.0f} > {self.MAX_PROFILE_TOKENS}). "
                    "Consider truncating for optimal performance."
                )
        self._candidate_profile = profile
        if profile:
            logger.info(f"Candidate profile set ({len(profile)} chars)")
        else:
            logger.info("Candidate profile cleared")
    
    def clear_candidate_profile(self) -> None:
        """Clear the candidate profile."""
        self._candidate_profile = None
        logger.info("Candidate profile cleared")
    
    def has_candidate_profile(self) -> bool:
        """Check if a candidate profile is set."""
        return self._candidate_profile is not None and len(self._candidate_profile) > 0

    def is_available(self) -> bool:
        """
        Check if the provider is available and ready to use.

        Returns:
            True if provider is ready to accept requests
        """
        return True

    @abstractmethod
    def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
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

    def is_available(self) -> bool:
        """
        Check if the provider is available and ready to use.

        Returns:
            True if provider is ready to accept requests
        """
        return True

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
