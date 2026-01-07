"""
Providers package for multi-provider AI support.

This package provides abstract interfaces and a factory for managing
multiple STT, LLM, and Embedding providers with automatic fallback.
"""
from .base import (
    STTProvider,
    LLMProvider,
    EmbeddingProvider,
    TranscriptionResult,
)
from .config import ProviderConfig, ProviderType
from .factory import ProviderFactory, ProviderError

__all__ = [
    # Base interfaces
    "STTProvider",
    "LLMProvider",
    "EmbeddingProvider",
    "TranscriptionResult",
    # Config
    "ProviderConfig",
    "ProviderType",
    # Factory
    "ProviderFactory",
    "ProviderError",
]
