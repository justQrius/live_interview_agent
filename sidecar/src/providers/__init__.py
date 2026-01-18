"""
Providers package for multi-provider AI support.

This package provides abstract interfaces and a factory for managing
multiple STT, LLM, and Embedding providers with automatic fallback.
"""
from .base import (
    STTProvider,
    LLMProvider,
    TranscriptionResult,
)
from .config import ProviderConfig, ProviderType
from .factory import ProviderFactory, ProviderError
from .stt.gemini import GeminiSTTProvider, GeminiSTTProviderError
from .llm.gemini import GeminiLLMProvider, GeminiLLMProviderError

__all__ = [
    # Base interfaces
    "STTProvider",
    "LLMProvider",
    "TranscriptionResult",
    # Config
    "ProviderConfig",
    "ProviderType",
    # Factory
    "ProviderFactory",
    "ProviderError",
    # Concrete providers - STT
    "GeminiSTTProvider",
    "GeminiSTTProviderError",
    # Concrete providers - LLM
    "GeminiLLMProvider",
    "GeminiLLMProviderError",
]
