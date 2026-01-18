"""
Provider Factory for creating and managing AI providers.

Implements fallback chains and caching for STT, LLM, and Embedding providers.
Supports both batch and streaming STT providers.
"""
import logging
from typing import Dict, List, Optional, Any

from .base import STTProvider, LLMProvider, EmbeddingProvider, SearchProvider
from .config import (
    ProviderConfig, ProviderType, StreamingMode,
    DeepgramModels, AssemblyAIModels, OpenAIModels,
    GeminiModels, AnthropicModels, GroqModels,
)
from .stt.streaming_base import StreamingSTTProvider

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

    DEFAULT_SEARCH_ORDER = [
        ProviderType.GEMINI,    # Integrated LLM+Search
        ProviderType.DUCKDUCKGO # Free, privacy-focused
    ]

    # Streaming STT provider order (for real-time transcription)
    DEFAULT_STREAMING_STT_ORDER = [
        StreamingMode.DEEPGRAM,      # Fast, reliable (~150ms)
        StreamingMode.ASSEMBLYAI,    # Semantic endpointing
        StreamingMode.OPENAI_REALTIME,  # Best semantic VAD (expensive)
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
        self._search_cache: Dict[ProviderType, SearchProvider] = {}
        self._streaming_stt_cache: Dict[StreamingMode, StreamingSTTProvider] = {}

        # Mock providers (for testing)
        self._mock_stt_providers: Optional[Dict[ProviderType, STTProvider]] = None
        self._mock_llm_providers: Optional[Dict[ProviderType, LLMProvider]] = None
        self._mock_search_providers: Optional[Dict[ProviderType, SearchProvider]] = None

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

    def get_search_fallback_order(self) -> List[ProviderType]:
        """
        Get the Search provider fallback order.

        Returns:
            List of ProviderTypes in fallback order
        """
        return self.DEFAULT_SEARCH_ORDER.copy()

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

    def get_available_search_providers(self) -> List[ProviderType]:
        """
        Get list of Search providers that have API keys configured (or are free).

        Returns:
            List of available ProviderTypes for Search
        """
        search_providers = [
            ProviderType.GEMINI,
            ProviderType.DUCKDUCKGO,
        ]
        return [p for p in search_providers if self.config.has_api_key(p) or p == ProviderType.DUCKDUCKGO]

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

    def get_search_provider(self, preferred: Optional[ProviderType] = None) -> SearchProvider:
        """
        Get a Search provider, with fallback chain.

        Args:
            preferred: Override preference for this call (optional)

        Returns:
            Available Search provider

        Raises:
            ProviderError: If no Search providers are available
        """
        # Use mock providers if set (for testing)
        if self._mock_search_providers is not None:
            # Simple mock retrieval for brevity
            for p_type, p in self._mock_search_providers.items():
                if p.is_available():
                    return p

        # Determine fallback order
        order = self.get_search_fallback_order()
        if preferred and preferred in order:
             # Move preferred to front
             order.remove(preferred)
             order.insert(0, preferred)

        # Try providers in order
        for provider_type in order:
            # Skip if no API key (DDG returns "free" which is valid string)
            if not self.config.has_api_key(provider_type) and provider_type != ProviderType.DUCKDUCKGO:
                continue

            # Check cache first
            if provider_type in self._search_cache:
                provider = self._search_cache[provider_type]
                if provider.is_available():
                    return provider

            # Create new provider
            provider = self._create_search_provider(provider_type)
            if provider is not None:
                self._search_cache[provider_type] = provider
                if provider.is_available():
                    logger.info(f"Using Search provider: {provider_type.value}")
                    return provider

        raise ProviderError("No Search providers available.")

    def get_streaming_stt_provider(
        self, 
        preferred: Optional[StreamingMode] = None
    ) -> Optional[StreamingSTTProvider]:
        """
        Get a streaming STT provider for real-time transcription.

        Streaming providers offer lower latency through WebSocket-based
        real-time transcription with interim results and semantic endpointing.

        Args:
            preferred: Override streaming mode preference for this call

        Returns:
            StreamingSTTProvider or None if streaming disabled/unavailable
        """
        # Check if streaming is disabled
        mode = preferred or self.config.streaming_mode
        if mode == StreamingMode.DISABLED:
            return None

        # Determine order to try
        if mode == StreamingMode.AUTO:
            order = self.DEFAULT_STREAMING_STT_ORDER
        else:
            # Put preferred first, then rest
            order = [mode] + [m for m in self.DEFAULT_STREAMING_STT_ORDER if m != mode]

        # Try providers in order
        for streaming_mode in order:
            # Check if we have API key for this provider
            if not self._has_streaming_api_key(streaming_mode):
                continue

            # Check cache first
            if streaming_mode in self._streaming_stt_cache:
                provider = self._streaming_stt_cache[streaming_mode]
                if provider.is_available():
                    return provider

            # Create new provider
            provider = self._create_streaming_stt_provider(streaming_mode)
            if provider is not None:
                self._streaming_stt_cache[streaming_mode] = provider
                if provider.is_available():
                    logger.info(f"Using streaming STT provider: {streaming_mode.value}")
                    return provider

        # No streaming providers available
        logger.info("No streaming STT providers available, will use batch STT")
        return None

    def _has_streaming_api_key(self, streaming_mode: StreamingMode) -> bool:
        """Check if API key exists for streaming provider."""
        if streaming_mode == StreamingMode.DEEPGRAM:
            return self.config.has_api_key(ProviderType.DEEPGRAM)
        elif streaming_mode == StreamingMode.ASSEMBLYAI:
            return self.config.has_api_key(ProviderType.ASSEMBLYAI)
        elif streaming_mode == StreamingMode.OPENAI_REALTIME:
            return self.config.has_api_key(ProviderType.OPENAI)
        return False

    def _create_streaming_stt_provider(
        self, 
        streaming_mode: StreamingMode
    ) -> Optional[StreamingSTTProvider]:
        """
        Create a streaming STT provider instance.

        Args:
            streaming_mode: Type of streaming provider to create

        Returns:
            StreamingSTTProvider instance or None if creation fails
        """
        try:
            if streaming_mode == StreamingMode.DEEPGRAM:
                api_key = self.config.get_api_key(ProviderType.DEEPGRAM)
                if not api_key:
                    return None
                from .stt.deepgram_streaming import DeepgramStreamingProvider
                # Use configured model or default
                model = self.config.streaming_stt_model or DeepgramModels.DEFAULT_STT
                return DeepgramStreamingProvider(api_key, model=model)

            elif streaming_mode == StreamingMode.ASSEMBLYAI:
                api_key = self.config.get_api_key(ProviderType.ASSEMBLYAI)
                if not api_key:
                    return None
                from .stt.assemblyai_streaming import AssemblyAIStreamingProvider
                # Use configured model or default
                model = self.config.streaming_stt_model or AssemblyAIModels.DEFAULT_STT
                return AssemblyAIStreamingProvider(api_key, model=model)

            elif streaming_mode == StreamingMode.OPENAI_REALTIME:
                api_key = self.config.get_api_key(ProviderType.OPENAI)
                if not api_key:
                    return None
                from .stt.openai_realtime import OpenAIRealtimeProvider
                # Use configured model or default
                model = self.config.streaming_stt_model or OpenAIModels.REALTIME
                return OpenAIRealtimeProvider(api_key, model=model)

        except ImportError as e:
            logger.warning(f"Failed to import {streaming_mode.value} streaming provider: {e}")
        except Exception as e:
            logger.warning(f"Failed to create {streaming_mode.value} streaming provider: {e}")

        return None

    def get_available_streaming_providers(self) -> List[StreamingMode]:
        """
        Get list of streaming STT providers that have API keys configured.

        Returns:
            List of available StreamingMode values
        """
        available = []
        for mode in [StreamingMode.DEEPGRAM, StreamingMode.ASSEMBLYAI, StreamingMode.OPENAI_REALTIME]:
            if self._has_streaming_api_key(mode):
                available.append(mode)
        return available

    def _get_mock_stt_provider(self, preferred: Optional[ProviderType]) -> STTProvider:
        """Get mock STT provider for testing."""
        if self._mock_stt_providers is None:
            raise ProviderError("Mock STT providers not initialized")

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
        if self._mock_llm_providers is None:
            raise ProviderError("Mock LLM providers not initialized")
            
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
                # Use configured model or default
                model = self.config.stt_model or GeminiModels.DEFAULT_STT
                return GeminiSTTProvider(api_key, model_name=model)
            elif provider_type == ProviderType.GROQ:
                from .stt.groq import GroqSTTProvider
                # Use configured model or default
                model = self.config.stt_model or GroqModels.DEFAULT_STT
                return GroqSTTProvider(api_key, model=model)
            elif provider_type == ProviderType.DEEPGRAM:
                from .stt.deepgram import DeepgramSTTProvider
                # Use configured model or default
                model = self.config.stt_model or DeepgramModels.DEFAULT_STT
                return DeepgramSTTProvider(api_key, model=model)
            elif provider_type == ProviderType.OPENAI:
                from .stt.openai import OpenAISTTProvider
                # Use configured model or default
                model = self.config.stt_model or OpenAIModels.DEFAULT_STT
                return OpenAISTTProvider(api_key, model=model)
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
                # Use configured model or default
                model = self.config.llm_model or GeminiModels.DEFAULT_LLM
                
                # Determine thinking budget
                # If extended_thinking is enabled but no budget set, default to 2048
                thinking_budget = self.config.thinking_budget
                if self.config.extended_thinking and not thinking_budget:
                    thinking_budget = 2048
                
                return GeminiLLMProvider(
                    api_key, 
                    model_name=model,
                    thinking_budget=thinking_budget,
                    search_enabled=self.config.search_enabled
                )
            elif provider_type == ProviderType.OPENAI:
                from .llm.openai import OpenAILLMProvider
                # Use configured model or default
                model = self.config.llm_model or OpenAIModels.DEFAULT_LLM
                return OpenAILLMProvider(api_key, model=model)
            elif provider_type == ProviderType.ANTHROPIC:
                from .llm.anthropic import AnthropicLLMProvider
                # Use configured model or default
                model = self.config.llm_model or AnthropicModels.DEFAULT_LLM
                return AnthropicLLMProvider(api_key, model=model)
        except ImportError as e:
            logger.warning(f"Failed to import {provider_type.value} LLM provider: {e}")
        except Exception as e:
            logger.warning(f"Failed to create {provider_type.value} LLM provider: {e}")

        return None

    def _create_search_provider(self, provider_type: ProviderType) -> Optional[SearchProvider]:
        """
        Create a Search provider instance.
        """
        try:
            if provider_type == ProviderType.GEMINI:
                api_key = self.config.get_api_key(provider_type)
                if not api_key:
                    return None
                from .search.gemini import GeminiSearchProvider
                return GeminiSearchProvider(api_key)
                
            elif provider_type == ProviderType.DUCKDUCKGO:
                from .search.duckduckgo import DuckDuckGoSearchProvider
                return DuckDuckGoSearchProvider()
                
        except ImportError as e:
            logger.warning(f"Failed to import {provider_type.value} Search provider: {e}")
        except Exception as e:
            logger.warning(f"Failed to create {provider_type.value} Search provider: {e}")

        return None

    def clear_cache(self) -> None:
        """Clear all cached provider instances."""
        self._stt_cache.clear()
        self._llm_cache.clear()
        self._embedding_cache.clear()
        self._search_cache.clear()
        self._streaming_stt_cache.clear()
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

        active_search = None
        for provider_type, provider in self._search_cache.items():
            if provider.is_available():
                active_search = provider_type.value
                break

        active_streaming_stt = None
        for streaming_mode, provider in self._streaming_stt_cache.items():
            if provider.is_available():
                active_streaming_stt = streaming_mode.value
                break

        return {
            "stt": {
                "active": active_stt,
                "available": [p.value for p in self.get_available_stt_providers()],
                "fallback_order": [p.value for p in self.get_stt_fallback_order()],
            },
            "streaming_stt": {
                "active": active_streaming_stt,
                "mode": self.config.streaming_mode.value,
                "available": [m.value for m in self.get_available_streaming_providers()],
            },
            "llm": {
                "active": active_llm,
                "available": [p.value for p in self.get_available_llm_providers()],
                "fallback_order": [p.value for p in self.get_llm_fallback_order()],
            },
            "search": {
                "active": active_search,
                "available": [p.value for p in self.get_available_search_providers()],
                "fallback_order": [p.value for p in self.get_search_fallback_order()],
            }
        }
