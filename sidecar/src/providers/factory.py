"""
Provider Factory.

Creates and manages instances of AI providers (STT, LLM, etc.)
based on configuration and availability.
Handles fallback logic and provider lifecycle.
"""

import logging
from typing import Dict, List, Optional, Any

from .base import STTProvider, LLMProvider, SearchProvider
from .config import ProviderConfig, ProviderType, GeminiModels, OpenAIModels, AnthropicModels
from .stt.streaming_base import StreamingSTTProvider

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Exception raised when provider creation or retrieval fails."""
    pass


class ProviderFactory:
    """
    Factory for creating and managing AI providers.
    
    Implements the Singleton pattern to ensure only one factory instance exists.
    Manages provider caches to reuse instances (e.g., maintaining WebSocket connections).
    """
    
    _instance = None
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize the provider factory.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self._stt_cache: Dict[ProviderType, STTProvider] = {}
        self._llm_cache: Dict[ProviderType, LLMProvider] = {}
        self._embedding_cache: Dict[str, Any] = {} # Abstract type for now
        self._search_cache: Dict[ProviderType, SearchProvider] = {}
        self._streaming_stt_cache: Dict[Any, StreamingSTTProvider] = {}
        
        # Mocks for testing
        self._mock_llm_providers: Optional[Dict[ProviderType, LLMProvider]] = None
        self._mock_stt_providers: Optional[Dict[ProviderType, STTProvider]] = None
        self._mock_search_providers: Optional[Dict[ProviderType, SearchProvider]] = None
        self._mock_streaming_providers: Optional[Dict[Any, StreamingSTTProvider]] = None

    @classmethod
    def get_instance(cls, config: Optional[ProviderConfig] = None) -> "ProviderFactory":
        """
        Get the singleton instance of the factory.
        
        Args:
            config: Optional config to update/initialize with
            
        Returns:
            The ProviderFactory instance
        """
        if cls._instance is None:
            if config is None:
                # Default config if none provided
                config = ProviderConfig()
            cls._instance = cls(config)
        elif config is not None:
            # Update config of existing instance
            cls._instance.config = config
            # Clear caches if config changes significantly? 
            # For now, we keep caches to avoid reconnecting overhead
            # unless explicitly cleared.
            
        return cls._instance

    def get_stt_provider(self, preferred: Optional[ProviderType] = None) -> STTProvider:
        """
        Get the best available STT provider.
        
        Args:
            preferred: Preferred provider type
            
        Returns:
            An instantiated STTProvider
            
        Raises:
            Exception: If no STT provider is available
        """
        # 1. Check mocks first
        if self._mock_stt_providers is not None:
            return self._get_mock_stt_provider(preferred)

        # 2. Try preferred
        if preferred:
            provider = self._get_or_create_stt_provider(preferred)
            if provider and provider.is_available():
                return provider
                
        # 3. Try configured preference
        if self.config.preferred_stt:
            provider = self._get_or_create_stt_provider(self.config.preferred_stt)
            if provider and provider.is_available():
                return provider

        # 4. Fallback chain
        for provider_type in self.get_stt_fallback_order():
            provider = self._get_or_create_stt_provider(provider_type)
            if provider and provider.is_available():
                return provider
                
        raise ProviderError("No STT providers available. Please check your API keys.")

    def get_llm_provider(self, preferred: Optional[ProviderType] = None) -> LLMProvider:
        """
        Get the best available LLM provider.
        
        Args:
            preferred: Preferred provider type
            
        Returns:
            An instantiated LLMProvider
            
        Raises:
            Exception: If no LLM provider is available
        """
        # 1. Check mocks
        if self._mock_llm_providers is not None:
            return self._get_mock_llm_provider(preferred)

        # 2. Try preferred
        if preferred:
            provider = self._get_or_create_llm_provider(preferred)
            if provider and provider.is_available():
                return provider

        # 3. Try configured preference
        if self.config.preferred_llm:
            provider = self._get_or_create_llm_provider(self.config.preferred_llm)
            if provider and provider.is_available():
                return provider

        # 4. Fallback chain
        for provider_type in self.get_llm_fallback_order():
            provider = self._get_or_create_llm_provider(provider_type)
            if provider and provider.is_available():
                return provider
                
        raise ProviderError("No LLM providers available. Please check your API keys.")

    def get_search_provider(self, preferred: Optional[ProviderType] = None) -> SearchProvider:
        """
        Get the best available Search provider.
        
        Args:
            preferred: Preferred provider type
            
        Returns:
            An instantiated SearchProvider
            
        Raises:
            Exception: If no Search provider is available
        """
        # 1. Check mocks
        if self._mock_search_providers is not None:
            return self._get_mock_search_provider(preferred)

        # 2. Try preferred
        if preferred:
            provider = self._get_or_create_search_provider(preferred)
            if provider and provider.is_available():
                return provider
                
        # 3. Fallback chain
        for provider_type in self.get_search_fallback_order():
            provider = self._get_or_create_search_provider(provider_type)
            if provider and provider.is_available():
                return provider
                
        # Note: Search is optional in many cases, but if requested we throw
        raise Exception("No available Search providers found.")

    def get_streaming_stt_provider(self) -> StreamingSTTProvider:
        """
        Get the configured streaming STT provider.
        
        Returns:
            An instantiated StreamingSTTProvider
            
        Raises:
            Exception: If streaming STT is disabled or not configured correctly
        """
        # 1. Check mocks
        if self._mock_streaming_providers:
            # Just return the first one for now in mocks
            return next(iter(self._mock_streaming_providers.values()))

        # 2. Check cache based on configured mode
        mode = self.config.streaming_mode
        
        if mode in self._streaming_stt_cache:
            return self._streaming_stt_cache[mode]
            
        # 3. Create new
        provider = self._create_streaming_stt_provider(mode)
        if provider:
            self._streaming_stt_cache[mode] = provider
            return provider
            
        raise Exception(f"Failed to create streaming STT provider for mode: {mode}")

    def get_stt_fallback_order(self) -> List[ProviderType]:
        """
        Get the order of STT providers to try.
        
        Simplified in Phase 3:
        1. LOCAL_WHISPER (primary, local GPU)
        2. GEMINI (cloud fallback)
        """
        order = []
        
        # 1. Configured preference (if still valid after simplification)
        if self.config.preferred_stt in (ProviderType.LOCAL_WHISPER, ProviderType.GEMINI):
            order.append(self.config.preferred_stt)
        
        # 2. LOCAL_WHISPER first (if GPU available - checked during creation)
        # This is the fastest and most private option
        if ProviderType.LOCAL_WHISPER not in order:
            order.append(ProviderType.LOCAL_WHISPER)
            
        # 3. Gemini as cloud fallback (native audio processing)
        if ProviderType.GEMINI not in order and self.config.has_api_key(ProviderType.GEMINI):
            order.append(ProviderType.GEMINI)
                
        return order

    def get_llm_fallback_order(self) -> List[ProviderType]:
        """Get the order of LLM providers to try."""
        order = []
        
        # 1. Configured preference
        if self.config.preferred_llm:
            order.append(self.config.preferred_llm)
            
        # 2. High capability providers
        defaults = [
            ProviderType.GEMINI,    # High context, fast
            ProviderType.OPENAI,    # Standard
            ProviderType.ANTHROPIC, # High reasoning
        ]
        
        for p in defaults:
            if p not in order and self.config.has_api_key(p):
                order.append(p)
                
        return order

    def get_search_fallback_order(self) -> List[ProviderType]:
        """Get the order of Search providers to try."""
        order = []
        
        # 1. Gemini (Integrated & Grounded)
        if self.config.has_api_key(ProviderType.GEMINI):
            order.append(ProviderType.GEMINI)
            
        # 2. DuckDuckGo (Free, no key needed)
        order.append(ProviderType.DUCKDUCKGO)
        
        return order

    def get_available_stt_providers(self) -> List[ProviderType]:
        """
        Get list of available STT providers.
        
        Simplified in Phase 3:
        - LOCAL_WHISPER: Always available (checked for GPU during creation)
        - GEMINI: Available if API key is set
        """
        providers = []
        
        # LOCAL_WHISPER is always potentially available (no API key needed)
        # It will be checked for GPU availability during creation
        providers.append(ProviderType.LOCAL_WHISPER)
        
        # Gemini is the only cloud STT fallback
        if self.config.has_api_key(ProviderType.GEMINI):
            providers.append(ProviderType.GEMINI)
                
        return providers

    def get_available_llm_providers(self) -> List[ProviderType]:
        """Get list of available LLM providers (have API keys)."""
        llm_providers = [
            ProviderType.GEMINI,
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
        ]
        return [p for p in llm_providers if self.config.has_api_key(p)]
        
    def get_available_search_providers(self) -> List[ProviderType]:
        """Get list of available Search providers."""
        providers = []
        if self.config.has_api_key(ProviderType.GEMINI):
            providers.append(ProviderType.GEMINI)
        providers.append(ProviderType.DUCKDUCKGO) # Always available
        return providers

    def get_available_streaming_providers(self) -> List[Any]:
        """
        Get list of available Streaming STT modes.
        
        Simplified in Phase 3: Only Deepgram streaming is supported.
        """
        from .config import StreamingMode
        modes = []
        
        # Always allow AUTO/DISABLED
        modes.append(StreamingMode.AUTO)
        
        # Only Deepgram streaming is supported after Phase 3
        if self.config.has_api_key(ProviderType.DEEPGRAM):
            modes.append(StreamingMode.DEEPGRAM)
            modes.append(StreamingMode.DEEPGRAM_FLUX)
            
        return modes

    def _get_or_create_stt_provider(self, provider_type: ProviderType) -> Optional[STTProvider]:
        """Get from cache or create STT provider."""
        if provider_type in self._stt_cache:
            return self._stt_cache[provider_type]
            
        provider = self._create_stt_provider(provider_type)
        if provider:
            self._stt_cache[provider_type] = provider
            
        return provider

    def _get_or_create_llm_provider(self, provider_type: ProviderType) -> Optional[LLMProvider]:
        """Get from cache or create LLM provider."""
        if provider_type in self._llm_cache:
            return self._llm_cache[provider_type]
            
        provider = self._create_llm_provider(provider_type)
        if provider:
            self._llm_cache[provider_type] = provider
            
        return provider

    def _get_or_create_search_provider(self, provider_type: ProviderType) -> Optional[SearchProvider]:
        """Get from cache or create Search provider."""
        if provider_type in self._search_cache:
            return self._search_cache[provider_type]
            
        provider = self._create_search_provider(provider_type)
        if provider:
            self._search_cache[provider_type] = provider
            
        return provider

    def _create_stt_provider(self, provider_type: ProviderType) -> Optional[STTProvider]:
        """
        Create an STT provider instance.
        
        Simplified in Phase 3 - only supports:
        - LOCAL_WHISPER: Primary, local GPU-accelerated (faster-whisper)
        - GEMINI: Cloud fallback with native audio processing
        """
        # LOCAL_WHISPER doesn't need an API key - it's local
        if provider_type == ProviderType.LOCAL_WHISPER:
            try:
                from .stt.local_whisper import LocalWhisperProvider, _check_gpu_available
                
                # Only create if GPU is available (for performance)
                # Note: LocalWhisperProvider can run on CPU but is much slower
                if not _check_gpu_available():
                    logger.info("No GPU available, skipping LOCAL_WHISPER provider")
                    return None
                
                # Use whisper_model_size preference, or stt_model as fallback, or default
                model = self.config.whisper_model_size or self.config.stt_model or "large-v3-turbo"
                return LocalWhisperProvider(model_size=model)
            except ImportError as e:
                logger.warning(f"Failed to import LocalWhisperProvider: {e}")
                return None
            except Exception as e:
                logger.warning(f"Failed to create LocalWhisperProvider: {e}")
                return None
        
        api_key = self.config.get_api_key(provider_type)
        if not api_key:
            return None
            
        try:
            # Simplified: Only Gemini as cloud STT fallback
            if provider_type == ProviderType.GEMINI:
                from .stt.gemini import GeminiSTTProvider
                model = self.config.stt_model or GeminiModels.DEFAULT_STT
                return GeminiSTTProvider(api_key, model_name=model)
            # Other provider types (GROQ, DEEPGRAM, OPENAI) removed in Phase 3
            # They were redundant with local faster-whisper
            else:
                logger.debug(f"STT provider {provider_type.value} not supported (removed in Phase 3)")
        except ImportError as e:
            logger.warning(f"Failed to import {provider_type.value} STT provider: {e}")
        except Exception as e:
            logger.warning(f"Failed to create {provider_type.value} STT provider: {e}")
            
        return None

    def _create_streaming_stt_provider(self, mode: Any) -> Optional[StreamingSTTProvider]:
        """
        Create a Streaming STT provider instance.
        
        Simplified in Phase 3 - only supports Deepgram streaming:
        - DEEPGRAM: Nova-3 with acoustic endpointing
        - DEEPGRAM_FLUX: Flux with semantic endpointing (recommended)
        """
        from .config import StreamingMode
        
        try:
            if mode == StreamingMode.DEEPGRAM:
                api_key = self.config.deepgram_api_key
                if not api_key: return None
                from .stt.deepgram_streaming import DeepgramStreamingProvider
                model = self.config.streaming_stt_model or "nova-3"
                return DeepgramStreamingProvider(api_key, model=model)
                
            elif mode == StreamingMode.DEEPGRAM_FLUX:
                api_key = self.config.deepgram_api_key
                if not api_key: return None
                from .stt.deepgram_flux import DeepgramFluxProvider
                model = self.config.streaming_stt_model or "flux-general-en"
                return DeepgramFluxProvider(api_key, model=model)
                
            elif mode == StreamingMode.AUTO:
                # AUTO mode: Only Deepgram streaming is supported after Phase 3 simplification
                # Prefer Flux (semantic endpointing) over Nova-3 (acoustic)
                if self.config.deepgram_api_key:
                    return self._create_streaming_stt_provider(StreamingMode.DEEPGRAM_FLUX)
                
                # No streaming available without Deepgram key
                logger.info("No streaming STT available (Deepgram API key required)")
                    
        except ImportError as e:
            logger.warning(f"Failed to import streaming provider for {mode}: {e}")
        except Exception as e:
            logger.warning(f"Failed to create streaming provider for {mode}: {e}")
            
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
                from .search.duckduckgo import DuckDuckGoSearchProvider
                
                # Use configured model or default
                model = self.config.llm_model or OpenAIModels.DEFAULT_LLM
                
                # Determine thinking budget
                thinking_budget = self.config.thinking_budget
                if self.config.extended_thinking and not thinking_budget:
                    thinking_budget = 2048
                    
                # Setup search provider if enabled
                search_provider = None
                if self.config.search_enabled:
                    # Use DuckDuckGo for OpenAI grounding
                    # Note: We create a fresh instance here. We could use _get_or_create_search_provider
                    # but we want to avoid circular dependencies if we injected the LLM back into it.
                    # Since DuckDuckGo is lightweight, creating a new one is fine.
                    try:
                        search_provider = DuckDuckGoSearchProvider()
                    except ImportError:
                        logger.warning("DuckDuckGo search not available for OpenAI grounding")
                
                return OpenAILLMProvider(
                    api_key, 
                    model=model,
                    thinking_budget=thinking_budget,
                    search_provider=search_provider,
                    search_enabled=self.config.search_enabled
                )
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

    # Mock helpers for testing
    def set_mock_llm_provider(self, provider_type: ProviderType, provider: LLMProvider):
        if self._mock_llm_providers is None: self._mock_llm_providers = {}
        self._mock_llm_providers[provider_type] = provider

    def set_mock_stt_provider(self, provider_type: ProviderType, provider: STTProvider):
        if self._mock_stt_providers is None: self._mock_stt_providers = {}
        self._mock_stt_providers[provider_type] = provider
        
    def _get_mock_llm_provider(self, preferred: Optional[ProviderType]) -> LLMProvider:
        if self._mock_llm_providers is None: raise Exception("No mocks set")
        if preferred and preferred in self._mock_llm_providers:
            return self._mock_llm_providers[preferred]
        return next(iter(self._mock_llm_providers.values()))
        
    def _get_mock_stt_provider(self, preferred: Optional[ProviderType]) -> STTProvider:
        if self._mock_stt_providers is None: raise Exception("No mocks set")
        if preferred and preferred in self._mock_stt_providers:
            return self._mock_stt_providers[preferred]
        return next(iter(self._mock_stt_providers.values()))

    def _get_mock_search_provider(self, preferred: Optional[ProviderType]) -> SearchProvider:
        if self._mock_search_providers is None: raise Exception("No mocks set")
        if preferred and preferred in self._mock_search_providers:
            return self._mock_search_providers[preferred]
        return next(iter(self._mock_search_providers.values()))
