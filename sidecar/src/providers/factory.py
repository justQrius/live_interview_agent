"""
Provider Factory for creating and managing AI providers.

Implements fallback chains and caching for STT, LLM, and Embedding providers.
"""
import logging
from typing import Dict, List, Optional, Any

from .base import STTProvider, LLMProvider, EmbeddingProvider
from .config import ProviderConfig, ProviderType

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when provider operations fail."""
    pass


class ProviderFactory:
    """
    Factory for creating and managing AI providers.

    Handles provider creation, fallback chains, and caching.
    Providers are created lazily on first request and cached for reuse.
    """

    # Default fallback orders (optimized for speed and reliability)
    DEFAULT_STT_ORDER = [
        ProviderType.GROQ,      # Fastest (~300ms)
        ProviderType.DEEPGRAM,  # Very fast (~350ms)
        ProviderType.OPENAI,    # Good quality (~400ms)
        ProviderType.GEMINI,    # Always available as fallback
    ]

    DEFAULT_LLM_ORDER = [
        ProviderType.OPENAI,    # Best quality
        ProviderType.ANTHROPIC, # High quality
        ProviderType.GEMINI,    # Always available as fallback
    ]

    def __init__(self, config: ProviderConfig):
        """
        Initialize the factory with configuration.

        Args:
            config: ProviderConfig with API keys and preferences
        """
        self.config = config

        # Provider caches
        self._stt_cache: Dict[ProviderType, STTProvider] = {}
        self._llm_cache: Dict[ProviderType, LLMProvider] = {}
        self._embedding_cache: Dict[ProviderType, EmbeddingProvider] = {}

        # Mock providers (for testing)
        self._mock_stt_providers: Optional[Dict[ProviderType, STTProvider]] = None
        self._mock_llm_providers: Optional[Dict[ProviderType, LLMProvider]] = None

    def get_stt_fallback_order(self) -> List[ProviderType]:
        """
        Get the STT provider fallback order.

        If a preferred provider is set, it goes first.
        Otherwise, uses default order.

        Returns:
            List of ProviderTypes in fallback order
        """
        if self.config.preferred_stt:
            # Put preferred first, then rest of default order
            order = [self.config.preferred_stt]
            order.extend(p for p in self.DEFAULT_STT_ORDER if p != self.config.preferred_stt)
            return order
        return self.DEFAULT_STT_ORDER.copy()

    def get_llm_fallback_order(self) -> List[ProviderType]:
        """
        Get the LLM provider fallback order.

        If a preferred provider is set, it goes first.
        Otherwise, uses default order.

        Returns:
            List of ProviderTypes in fallback order
        """
        if self.config.preferred_llm:
            order = [self.config.preferred_llm]
            order.extend(p for p in self.DEFAULT_LLM_ORDER if p != self.config.preferred_llm)
            return order
        return self.DEFAULT_LLM_ORDER.copy()

    def get_available_stt_providers(self) -> List[ProviderType]:
        """
        Get list of STT providers that have API keys configured.

        Returns:
            List of available ProviderTypes for STT
        """
        stt_providers = [
            ProviderType.GEMINI,
            ProviderType.GROQ,
            ProviderType.DEEPGRAM,
            ProviderType.OPENAI,
        ]
        return [p for p in stt_providers if self.config.has_api_key(p)]

    def get_available_llm_providers(self) -> List[ProviderType]:
        """
        Get list of LLM providers that have API keys configured.

        Returns:
            List of available ProviderTypes for LLM
        """
        llm_providers = [
            ProviderType.GEMINI,
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
        ]
        return [p for p in llm_providers if self.config.has_api_key(p)]

    def get_stt_provider(self, preferred: Optional[ProviderType] = None) -> STTProvider:
        """
        Get an STT provider, with fallback chain.

        Tries providers in fallback order until one is available.

        Args:
            preferred: Override preference for this call (optional)

        Returns:
            Available STT provider

        Raises:
            ProviderError: If no STT providers are available
        """
        # Use mock providers if set (for testing)
        if self._mock_stt_providers is not None:
            return self._get_mock_stt_provider(preferred)

        # Determine fallback order
        if preferred:
            order = [preferred] + [p for p in self.DEFAULT_STT_ORDER if p != preferred]
        else:
            order = self.get_stt_fallback_order()

        # Try providers in order
        for provider_type in order:
            # Skip if no API key
            if not self.config.has_api_key(provider_type):
                continue

            # Check cache first
            if provider_type in self._stt_cache:
                provider = self._stt_cache[provider_type]
                if provider.is_available():
                    return provider

            # Create new provider
            provider = self._create_stt_provider(provider_type)
            if provider is not None:
                self._stt_cache[provider_type] = provider
                if provider.is_available():
                    logger.info(f"Using STT provider: {provider_type.value}")
                    return provider

        raise ProviderError(
            "No STT providers available. Configure at least one API key for: "
            + ", ".join(p.value for p in self.DEFAULT_STT_ORDER)
        )

    def get_llm_provider(self, preferred: Optional[ProviderType] = None) -> LLMProvider:
        """
        Get an LLM provider, with fallback chain.

        Tries providers in fallback order until one is available.

        Args:
            preferred: Override preference for this call (optional)

        Returns:
            Available LLM provider

        Raises:
            ProviderError: If no LLM providers are available
        """
        # Use mock providers if set (for testing)
        if self._mock_llm_providers is not None:
            return self._get_mock_llm_provider(preferred)

        # Determine fallback order
        if preferred:
            order = [preferred] + [p for p in self.DEFAULT_LLM_ORDER if p != preferred]
        else:
            order = self.get_llm_fallback_order()

        # Try providers in order
        for provider_type in order:
            # Skip if no API key
            if not self.config.has_api_key(provider_type):
                continue

            # Check cache first
            if provider_type in self._llm_cache:
                provider = self._llm_cache[provider_type]
                if provider.is_available():
                    return provider

            # Create new provider
            provider = self._create_llm_provider(provider_type)
            if provider is not None:
                self._llm_cache[provider_type] = provider
                if provider.is_available():
                    logger.info(f"Using LLM provider: {provider_type.value}")
                    return provider

        raise ProviderError(
            "No LLM providers available. Configure at least one API key for: "
            + ", ".join(p.value for p in self.DEFAULT_LLM_ORDER)
        )

    def _get_mock_stt_provider(self, preferred: Optional[ProviderType]) -> STTProvider:
        """Get mock STT provider for testing."""
        if preferred and preferred in self._mock_stt_providers:
            p = self._mock_stt_providers[preferred]
            if p.is_available():
                return p

        # Fallback through mocks
        order = self.get_stt_fallback_order()
        for provider_type in order:
            if provider_type in self._mock_stt_providers:
                p = self._mock_stt_providers[provider_type]
                if p.is_available():
                    return p

        raise ProviderError("No STT providers available")

    def _get_mock_llm_provider(self, preferred: Optional[ProviderType]) -> LLMProvider:
        """Get mock LLM provider for testing."""
        if preferred and preferred in self._mock_llm_providers:
            p = self._mock_llm_providers[preferred]
            if p.is_available():
                return p

        # Fallback through mocks
        order = self.get_llm_fallback_order()
        for provider_type in order:
            if provider_type in self._mock_llm_providers:
                p = self._mock_llm_providers[provider_type]
                if p.is_available():
                    return p

        raise ProviderError("No LLM providers available")

    def _create_stt_provider(self, provider_type: ProviderType) -> Optional[STTProvider]:
        """
        Create an STT provider instance.

        Args:
            provider_type: Type of provider to create

        Returns:
            STTProvider instance or None if creation fails
        """
        api_key = self.config.get_api_key(provider_type)
        if not api_key:
            return None

        try:
            # Lazy imports to avoid loading all provider dependencies
            if provider_type == ProviderType.GEMINI:
                from .stt.gemini import GeminiSTTProvider
                return GeminiSTTProvider(api_key)
            elif provider_type == ProviderType.GROQ:
                from .stt.groq import GroqSTTProvider
                return GroqSTTProvider(api_key)
            elif provider_type == ProviderType.DEEPGRAM:
                from .stt.deepgram import DeepgramSTTProvider
                return DeepgramSTTProvider(api_key)
            elif provider_type == ProviderType.OPENAI:
                from .stt.openai import OpenAISTTProvider
                return OpenAISTTProvider(api_key)
        except ImportError as e:
            logger.warning(f"Failed to import {provider_type.value} STT provider: {e}")
        except Exception as e:
            logger.warning(f"Failed to create {provider_type.value} STT provider: {e}")

        return None

    def _create_llm_provider(self, provider_type: ProviderType) -> Optional[LLMProvider]:
        """
        Create an LLM provider instance.

        Args:
            provider_type: Type of provider to create

        Returns:
            LLMProvider instance or None if creation fails
        """
        api_key = self.config.get_api_key(provider_type)
        if not api_key:
            return None

        try:
            # Lazy imports to avoid loading all provider dependencies
            if provider_type == ProviderType.GEMINI:
                from .llm.gemini import GeminiLLMProvider
                return GeminiLLMProvider(api_key, thinking_budget=self.config.thinking_budget)
            elif provider_type == ProviderType.OPENAI:
                from .llm.openai import OpenAILLMProvider
                return OpenAILLMProvider(api_key)
            elif provider_type == ProviderType.ANTHROPIC:
                from .llm.anthropic import AnthropicLLMProvider
                return AnthropicLLMProvider(api_key)
        except ImportError as e:
            logger.warning(f"Failed to import {provider_type.value} LLM provider: {e}")
        except Exception as e:
            logger.warning(f"Failed to create {provider_type.value} LLM provider: {e}")

        return None

    def clear_cache(self) -> None:
        """Clear all cached provider instances."""
        self._stt_cache.clear()
        self._llm_cache.clear()
        self._embedding_cache.clear()
        logger.info("Provider cache cleared")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current provider status.

        Returns:
            Dictionary with provider status information
        """
        # Determine active providers from cache
        active_stt = None
        for provider_type, provider in self._stt_cache.items():
            if provider.is_available():
                active_stt = provider_type.value
                break

        active_llm = None
        for provider_type, provider in self._llm_cache.items():
            if provider.is_available():
                active_llm = provider_type.value
                break

        return {
            "stt": {
                "active": active_stt,
                "available": [p.value for p in self.get_available_stt_providers()],
                "fallback_order": [p.value for p in self.get_stt_fallback_order()],
            },
            "llm": {
                "active": active_llm,
                "available": [p.value for p in self.get_available_llm_providers()],
                "fallback_order": [p.value for p in self.get_llm_fallback_order()],
            },
        }
