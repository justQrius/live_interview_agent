"""
Provider Configuration for multi-provider support.

Manages API keys, preferences, and model constants for STT, LLM, and Embedding providers.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# =============================================================================
# MODEL CONSTANTS
# Centralized model name definitions - update here when models change
# Last updated: Jan 2026 (Gen 1 Flagships)
# =============================================================================

class GeminiModels:
    """Gemini model identifiers."""
    # Gen 1 (Current)
    PRO_3 = "gemini-3-pro"        # Reasoning / Native Audio
    FLASH_3 = "gemini-3-flash"    # Fast / Cost-effective
    
    # Gen 2 (Previous)
    PRO_2_5 = "gemini-2.5-pro"
    FLASH_2_5 = "gemini-2.5-flash"
    
    # Specialized
    EMBEDDING = "text-embedding-004"
    
    # Default choices by use case
    DEFAULT_LLM = FLASH_3
    DEFAULT_STT = FLASH_3  # Native audio processing
    DEFAULT_CACHE = PRO_3
    DEFAULT_SEARCH = FLASH_3


class OpenAIModels:
    """OpenAI model identifiers."""
    # Gen 1 (Current)
    GPT5_2 = "gpt-5.2"        # Flagship
    GPT5_1 = "gpt-5.1"        # Reasoning
    GPT5_MINI = "gpt-5-mini"  # Fast
    GPT5_NANO = "gpt-5-nano"  # Ultra-fast
    
    # Gen 2 (Previous)
    GPT4O = "gpt-4o"
    O3_MINI = "o3-mini"
    
    # Whisper for STT
    WHISPER_1 = "whisper-1"
    
    # Realtime for streaming STT
    REALTIME = "gpt-realtime"  # GA model
    REALTIME_MINI = "gpt-realtime-mini"
    REALTIME_PREVIEW = "gpt-4o-realtime-preview" # Legacy Beta
    
    # Default
    DEFAULT_LLM = GPT5_MINI
    DEFAULT_STT = WHISPER_1


class AnthropicModels:
    """Anthropic model identifiers."""
    # Gen 1 (Current)
    CLAUDE_4_OPUS = "claude-4-opus"
    CLAUDE_4_SONNET = "claude-4-sonnet"
    CLAUDE_4_HAIKU = "claude-4-haiku"
    
    # Gen 2 (Previous)
    CLAUDE_3_7_SONNET = "claude-3.7-sonnet"
    
    # Default
    DEFAULT_LLM = CLAUDE_4_SONNET


class DeepgramModels:
    """Deepgram model identifiers."""
    # Nova-3 Series (Latest)
    NOVA_3 = "nova-3"
    NOVA_3_GENERAL = "nova-3-general"
    NOVA_3_MEETING = "nova-3-meeting"
    
    # Legacy
    NOVA_2 = "nova-2"
    FLUX = "flux"
    
    # Default
    DEFAULT_STT = NOVA_3


class GroqModels:
    """Groq model identifiers for Whisper."""
    WHISPER_LARGE_V3 = "whisper-large-v3"
    WHISPER_LARGE_V3_TURBO = "whisper-large-v3-turbo"
    
    # Default
    DEFAULT_STT = WHISPER_LARGE_V3_TURBO


class AssemblyAIModels:
    """AssemblyAI model identifiers."""
    BEST = "best"
    NANO = "nano"
    
    # Default
    DEFAULT_STT = BEST


# =============================================================================
# PROVIDER CONFIGURATION
# =============================================================================

class ProviderType(Enum):
    """Enum for supported AI provider types."""
    GEMINI = "gemini"
    GROQ = "groq"
    DEEPGRAM = "deepgram"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ASSEMBLYAI = "assemblyai"
    DUCKDUCKGO = "duckduckgo"


class StreamingMode(Enum):
    """Streaming STT mode preference."""
    DISABLED = "disabled"  # Use batch STT only
    AUTO = "auto"          # Auto-select best available
    DEEPGRAM = "deepgram"  # Prefer Deepgram streaming
    ASSEMBLYAI = "assemblyai"  # Prefer AssemblyAI streaming
    OPENAI_REALTIME = "openai_realtime"  # Prefer OpenAI Realtime


@dataclass
class ProviderConfig:
    """
    Configuration for all AI providers.

    Stores API keys, provider preferences, and fallback settings.
    Used by ProviderFactory to create and manage provider instances.
    """

    # API Keys
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    assemblyai_api_key: Optional[str] = None

    # Preferences (None means use fallback chain / auto)
    preferred_stt: Optional[ProviderType] = None
    preferred_llm: Optional[ProviderType] = None
    
    # Model selections (None means use provider default)
    llm_model: Optional[str] = None
    stt_model: Optional[str] = None
    streaming_stt_model: Optional[str] = None
    
    # Streaming STT preference
    streaming_mode: StreamingMode = StreamingMode.AUTO

    # Fallback settings
    fallback_enabled: bool = True
    fallback_timeout: float = 5.0  # seconds before trying next provider
    
    # Advanced settings (Phase 5 & 7)
    thinking_budget: Optional[int] = 1024 # Default token budget for thinking models
    search_enabled: bool = True  # Enable Google Search grounding for Gemini LLM
    extended_thinking: bool = False # Enable High Reasoning Mode (GPT-5/Claude 4)

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderConfig":
        """
        Create ProviderConfig from a dictionary.

        Expected format (from WebSocket message):
        {
            "apiKeys": {
                "gemini": "...",
                ...
            },
            "preferences": {
                "sttProvider": "groq",
                "llmProvider": "openai",
                "thinkingBudget": 2048,  # Optional
                "extendedThinking": true # Optional
            }
        }
        """
        api_keys = data.get("apiKeys", {})
        preferences = data.get("preferences", {})

        # Parse STT preference
        preferred_stt = None
        stt_pref = preferences.get("sttProvider")
        if stt_pref and stt_pref != "auto":
            try:
                preferred_stt = ProviderType(stt_pref)
            except ValueError:
                pass  # Invalid provider, use auto

        # Parse LLM preference
        preferred_llm = None
        llm_pref = preferences.get("llmProvider")
        if llm_pref and llm_pref != "auto":
            try:
                preferred_llm = ProviderType(llm_pref)
            except ValueError:
                pass  # Invalid provider, use auto

        # Parse streaming mode preference
        streaming_mode = StreamingMode.AUTO
        streaming_pref = preferences.get("streamingSttProvider")
        if streaming_pref:
            try:
                streaming_mode = StreamingMode(streaming_pref)
            except ValueError:
                pass  # Invalid mode, use auto

        # Parse model selections (Phase 7)
        llm_model = preferences.get("llmModel")
        if llm_model == "auto":
            llm_model = None
        
        stt_model = preferences.get("sttModel")
        if stt_model == "auto":
            stt_model = None
        
        streaming_stt_model = preferences.get("streamingSttModel")
        if streaming_stt_model == "auto":
            streaming_stt_model = None

        # Search is enabled by default, can be disabled via preferences
        search_enabled = preferences.get("searchEnabled", True)
        
        # Extended thinking toggle
        extended_thinking = preferences.get("extendedThinking", False)
        
        return cls(
            gemini_api_key=api_keys.get("gemini"),
            groq_api_key=api_keys.get("groq"),
            deepgram_api_key=api_keys.get("deepgram"),
            openai_api_key=api_keys.get("openai"),
            anthropic_api_key=api_keys.get("anthropic"),
            assemblyai_api_key=api_keys.get("assemblyai"),
            preferred_stt=preferred_stt,
            preferred_llm=preferred_llm,
            llm_model=llm_model,
            stt_model=stt_model,
            streaming_stt_model=streaming_stt_model,
            streaming_mode=streaming_mode,
            thinking_budget=preferences.get("thinkingBudget"),
            search_enabled=search_enabled,
            extended_thinking=extended_thinking
        )

    def has_api_key(self, provider_type: ProviderType) -> bool:
        """
        Check if an API key exists for the given provider.

        Args:
            provider_type: The provider to check

        Returns:
            True if API key is set and non-empty
        """
        key = self.get_api_key(provider_type)
        return key is not None and len(key) > 0

    def get_api_key(self, provider_type: ProviderType) -> Optional[str]:
        """
        Get the API key for a provider.

        Args:
            provider_type: The provider to get key for

        Returns:
            API key string or None if not set
        """
        key_mapping = {
            ProviderType.GEMINI: self.gemini_api_key,
            ProviderType.GROQ: self.groq_api_key,
            ProviderType.DEEPGRAM: self.deepgram_api_key,
            ProviderType.OPENAI: self.openai_api_key,
            ProviderType.ANTHROPIC: self.anthropic_api_key,
            ProviderType.ASSEMBLYAI: self.assemblyai_api_key,
            ProviderType.DUCKDUCKGO: "free",
        }
        return key_mapping.get(provider_type)
