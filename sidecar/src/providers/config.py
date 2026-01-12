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
# =============================================================================

class GeminiModels:
    """Gemini model identifiers."""
    # Primary models
    FLASH = "gemini-3-flash-preview"  # Fast, cost-effective for most tasks
    PRO = "gemini-3-pro-preview"      # Higher capability for complex tasks
    
    # Specialized
    EMBEDDING = "text-embedding-004"
    
    # Default choices by use case
    DEFAULT_LLM = PRO
    DEFAULT_STT = FLASH
    DEFAULT_CACHE = FLASH
    DEFAULT_SEARCH = FLASH


class OpenAIModels:
    """OpenAI model identifiers."""
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    
    # Default
    DEFAULT_LLM = GPT4O


class AnthropicModels:
    """Anthropic model identifiers."""
    CLAUDE_35_SONNET = "claude-3-5-sonnet-20240620"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    
    # Default
    DEFAULT_LLM = CLAUDE_35_SONNET


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

    # Preferences (None means use fallback chain / auto)
    preferred_stt: Optional[ProviderType] = None
    preferred_llm: Optional[ProviderType] = None

    # Fallback settings
    fallback_enabled: bool = True
    fallback_timeout: float = 5.0  # seconds before trying next provider
    
    # Advanced settings (Phase 5)
    thinking_budget: Optional[int] = 1024 # Default token budget for thinking models

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
                "thinkingBudget": 2048  # Optional
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

        return cls(
            gemini_api_key=api_keys.get("gemini"),
            groq_api_key=api_keys.get("groq"),
            deepgram_api_key=api_keys.get("deepgram"),
            openai_api_key=api_keys.get("openai"),
            anthropic_api_key=api_keys.get("anthropic"),
            preferred_stt=preferred_stt,
            preferred_llm=preferred_llm,
            thinking_budget=preferences.get("thinkingBudget")
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
        }
        return key_mapping.get(provider_type)
