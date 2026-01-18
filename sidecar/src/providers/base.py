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

@dataclass
class GroundingSource:
    """A source used for grounding the response."""
    title: str
    url: str
    snippet: Optional[str] = None

@dataclass  
class GroundedResponse:
    """Response with grounding metadata."""
    text: str
    search_queries: List[str]
    sources: List[GroundingSource]

class SearchProvider(ABC):
    """
    Abstract Base Class for Search/Grounding providers.
    """
    
    def is_available(self) -> bool:
        """Check if the provider is available."""
        return True
        
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[GroundingSource]:
        """
        Perform a basic web search.
        
        Args:
            query: Search query
            limit: Number of results
            
        Returns:
            List of GroundingSource objects
        """
        pass
        
    @abstractmethod
    async def research(self, topic: str) -> GroundedResponse:
        """
        Perform deep research on a topic and return a summarized, cited response.
        
        Args:
            topic: The topic to research
            
        Returns:
            GroundedResponse with text summary and sources
        """
        pass

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
    
    # Maximum tokens for injected profile
    # 1500 tokens allows full candidate context including STAR story summaries
    MAX_PROFILE_TOKENS = 1500
    
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

    def has_cached_content(self) -> bool:
        """
        Check if the provider has active cached content (full context).
        
        If True, RAG retrieval may be skipped as the model has
        access to the full document set.
        """
        return False

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

# NOTE: EmbeddingProvider ABC was removed as unused.
# The actual embedding implementation (GeminiEmbeddingFunction) inherits from
# ChromaDB's EmbeddingFunction interface directly. See rag/gemini_embeddings.py.
