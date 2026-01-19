"""
Tests for Provider Factory and Config (STORY-023).

Tests the ProviderConfig dataclass and ProviderFactory with fallback chains.
"""
import sys
from pathlib import Path
import pytest
from typing import List, Dict, AsyncGenerator

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.providers.base import STTProvider, LLMProvider, TranscriptionResult
from src.providers.config import ProviderConfig, ProviderType
from src.providers.factory import ProviderFactory, ProviderError


# =============================================================================
# Test Fixtures - Mock Providers
# =============================================================================

class MockSTTProvider(STTProvider):
    """Mock STT provider for testing."""

    def __init__(self, name: str, available: bool = True):
        self.name = name
        self._available = available
        self.transcribe_called = False

    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        self.transcribe_called = True
        return TranscriptionResult(text=f"transcribed by {self.name}", confidence=0.95)

    def is_available(self) -> bool:
        return self._available


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, name: str, available: bool = True):
        self.name = name
        self._available = available
        self.generate_called = False

    async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
        self.generate_called = True
        yield f"response from {self.name}"

    def is_available(self) -> bool:
        return self._available


# NOTE: MockEmbeddingProvider removed - EmbeddingProvider ABC was deprecated.
# Actual embedding uses ChromaDB's EmbeddingFunction interface.


# =============================================================================
# ProviderType Enum Tests
# =============================================================================

class TestProviderType:
    """Tests for ProviderType enum."""

    def test_provider_type_values(self):
        """Test all provider types have correct string values."""
        assert ProviderType.GEMINI.value == "gemini"
        assert ProviderType.GROQ.value == "groq"
        assert ProviderType.DEEPGRAM.value == "deepgram"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"

    def test_provider_type_from_string(self):
        """Test creating ProviderType from string value."""
        assert ProviderType("gemini") == ProviderType.GEMINI
        assert ProviderType("groq") == ProviderType.GROQ
        assert ProviderType("openai") == ProviderType.OPENAI

    def test_provider_type_invalid_value(self):
        """Test invalid provider type raises error."""
        with pytest.raises(ValueError):
            ProviderType("invalid_provider")


# =============================================================================
# ProviderConfig Tests
# =============================================================================

class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_default_values(self):
        """Test ProviderConfig has correct defaults."""
        config = ProviderConfig()

        # All API keys should be None by default
        assert config.gemini_api_key is None
        assert config.groq_api_key is None
        assert config.deepgram_api_key is None
        assert config.openai_api_key is None
        assert config.anthropic_api_key is None

        # Preferences should be None (auto)
        assert config.preferred_stt is None
        assert config.preferred_llm is None

        # Fallback enabled by default
        assert config.fallback_enabled is True
        assert config.fallback_timeout == 5.0

    def test_init_with_api_keys(self):
        """Test ProviderConfig initialization with API keys."""
        config = ProviderConfig(
            gemini_api_key="gemini-key-123",
            openai_api_key="openai-key-456"
        )

        assert config.gemini_api_key == "gemini-key-123"
        assert config.openai_api_key == "openai-key-456"
        assert config.groq_api_key is None

    def test_init_with_preferences(self):
        """Test ProviderConfig with provider preferences."""
        config = ProviderConfig(
            preferred_stt=ProviderType.GROQ,
            preferred_llm=ProviderType.ANTHROPIC
        )

        assert config.preferred_stt == ProviderType.GROQ
        assert config.preferred_llm == ProviderType.ANTHROPIC

    def test_from_dict_basic(self):
        """Test ProviderConfig.from_dict with basic data."""
        data = {
            "apiKeys": {
                "gemini": "gemini-key",
                "groq": "groq-key"
            }
        }

        config = ProviderConfig.from_dict(data)

        assert config.gemini_api_key == "gemini-key"
        assert config.groq_api_key == "groq-key"
        assert config.openai_api_key is None

    def test_from_dict_with_preferences(self):
        """Test ProviderConfig.from_dict with provider preferences."""
        data = {
            "apiKeys": {
                "gemini": "key"
            },
            "preferences": {
                "sttProvider": "groq",
                "llmProvider": "openai"
            }
        }

        config = ProviderConfig.from_dict(data)

        assert config.preferred_stt == ProviderType.GROQ
        assert config.preferred_llm == ProviderType.OPENAI

    def test_from_dict_auto_preference(self):
        """Test ProviderConfig.from_dict with 'auto' preference."""
        data = {
            "apiKeys": {},
            "preferences": {
                "sttProvider": "auto",
                "llmProvider": "auto"
            }
        }

        config = ProviderConfig.from_dict(data)

        # 'auto' should result in None (use fallback chain)
        assert config.preferred_stt is None
        assert config.preferred_llm is None

    def test_from_dict_empty(self):
        """Test ProviderConfig.from_dict with empty dict."""
        config = ProviderConfig.from_dict({})

        assert config.gemini_api_key is None
        assert config.preferred_stt is None

    def test_from_dict_all_keys(self):
        """Test ProviderConfig.from_dict with all API keys."""
        data = {
            "apiKeys": {
                "gemini": "g-key",
                "groq": "gr-key",
                "deepgram": "d-key",
                "openai": "o-key",
                "anthropic": "a-key"
            }
        }

        config = ProviderConfig.from_dict(data)

        assert config.gemini_api_key == "g-key"
        assert config.groq_api_key == "gr-key"
        assert config.deepgram_api_key == "d-key"
        assert config.openai_api_key == "o-key"
        assert config.anthropic_api_key == "a-key"

    def test_has_api_key_for_provider(self):
        """Test checking if config has API key for a provider."""
        config = ProviderConfig(gemini_api_key="key", openai_api_key="key2")

        assert config.has_api_key(ProviderType.GEMINI) is True
        assert config.has_api_key(ProviderType.OPENAI) is True
        assert config.has_api_key(ProviderType.GROQ) is False
        assert config.has_api_key(ProviderType.ANTHROPIC) is False

    def test_get_api_key(self):
        """Test getting API key for a provider."""
        config = ProviderConfig(gemini_api_key="test-key")

        assert config.get_api_key(ProviderType.GEMINI) == "test-key"
        assert config.get_api_key(ProviderType.GROQ) is None


# =============================================================================
# ProviderFactory Tests
# =============================================================================

class TestProviderFactory:
    """Tests for ProviderFactory."""

    def test_factory_initialization(self):
        """Test ProviderFactory initializes with config."""
        config = ProviderConfig(gemini_api_key="key")
        factory = ProviderFactory(config)

        assert factory.config == config

    def test_factory_get_available_stt_providers(self):
        """Test listing available STT providers based on API keys."""
        config = ProviderConfig(
            gemini_api_key="g-key",
            groq_api_key="gr-key"
        )
        factory = ProviderFactory(config)

        available = factory.get_available_stt_providers()

        assert ProviderType.GEMINI in available
        assert ProviderType.GROQ in available
        assert ProviderType.OPENAI not in available

    def test_factory_get_available_llm_providers(self):
        """Test listing available LLM providers based on API keys."""
        config = ProviderConfig(
            openai_api_key="o-key",
            anthropic_api_key="a-key"
        )
        factory = ProviderFactory(config)

        available = factory.get_available_llm_providers()

        assert ProviderType.OPENAI in available
        assert ProviderType.ANTHROPIC in available
        assert ProviderType.GEMINI not in available

    def test_factory_stt_fallback_order_default(self):
        """Test default STT fallback order only includes providers with API keys."""
        # Without any API keys, fallback order should be empty
        config = ProviderConfig()
        factory = ProviderFactory(config)

        order = factory.get_stt_fallback_order()
        assert order == []
        
        # With API keys, fallback order contains those providers
        config_with_keys = ProviderConfig(
            groq_api_key="groq-key",
            deepgram_api_key="deepgram-key"
        )
        factory_with_keys = ProviderFactory(config_with_keys)
        
        order_with_keys = factory_with_keys.get_stt_fallback_order()
        assert ProviderType.GROQ in order_with_keys
        assert ProviderType.DEEPGRAM in order_with_keys
        assert ProviderType.OPENAI not in order_with_keys  # No key provided

    def test_factory_stt_fallback_order_with_preference(self):
        """Test STT fallback order with preferred provider first (only if key available)."""
        # Preference without key - preference is still added but needs key to work
        config = ProviderConfig(
            preferred_stt=ProviderType.GEMINI,
            gemini_api_key="gemini-key"
        )
        factory = ProviderFactory(config)

        order = factory.get_stt_fallback_order()

        # Gemini should be first since we have the key and it's preferred
        assert order[0] == ProviderType.GEMINI
        # No other providers without keys
        assert len(order) == 1

    def test_factory_llm_fallback_order_default(self):
        """Test default LLM fallback order only includes providers with API keys."""
        # Without any API keys, fallback order should be empty
        config = ProviderConfig()
        factory = ProviderFactory(config)

        order = factory.get_llm_fallback_order()
        assert order == []
        
        # With API keys, fallback order contains those providers in priority order
        config_with_keys = ProviderConfig(
            openai_api_key="openai-key",
            anthropic_api_key="anthropic-key"
        )
        factory_with_keys = ProviderFactory(config_with_keys)
        
        order_with_keys = factory_with_keys.get_llm_fallback_order()
        assert ProviderType.OPENAI in order_with_keys
        assert ProviderType.ANTHROPIC in order_with_keys
        assert ProviderType.GEMINI not in order_with_keys  # No key provided

    def test_factory_llm_fallback_order_with_preference(self):
        """Test LLM fallback order with preferred provider first."""
        config = ProviderConfig(preferred_llm=ProviderType.ANTHROPIC)
        factory = ProviderFactory(config)

        order = factory.get_llm_fallback_order()

        assert order[0] == ProviderType.ANTHROPIC


class TestProviderFactoryWithMocks:
    """Tests for ProviderFactory using mock providers."""

    @pytest.fixture
    def factory_with_mocks(self):
        """Create a factory with mock provider creators."""
        config = ProviderConfig(
            gemini_api_key="g-key",
            groq_api_key="gr-key",
            openai_api_key="o-key"
        )
        factory = ProviderFactory(config)

        # Inject mock creators
        factory._mock_stt_providers = {
            ProviderType.GEMINI: MockSTTProvider("gemini", available=True),
            ProviderType.GROQ: MockSTTProvider("groq", available=True),
        }
        factory._mock_llm_providers = {
            ProviderType.OPENAI: MockLLMProvider("openai", available=True),
            ProviderType.GEMINI: MockLLMProvider("gemini", available=True),
        }

        return factory

    def test_get_stt_provider_uses_preferred(self, factory_with_mocks):
        """Test get_stt_provider uses preferred provider."""
        factory_with_mocks.config.preferred_stt = ProviderType.GEMINI

        provider = factory_with_mocks.get_stt_provider()

        assert provider.name == "gemini"

    def test_get_stt_provider_fallback_on_unavailable(self, factory_with_mocks):
        """Test get_stt_provider falls back when preferred unavailable."""
        factory_with_mocks.config.preferred_stt = ProviderType.GROQ
        factory_with_mocks._mock_stt_providers[ProviderType.GROQ]._available = False

        provider = factory_with_mocks.get_stt_provider()

        # Should fall back to next available
        assert provider.name != "groq"

    def test_get_llm_provider_uses_preferred(self, factory_with_mocks):
        """Test get_llm_provider uses preferred provider."""
        factory_with_mocks.config.preferred_llm = ProviderType.OPENAI

        provider = factory_with_mocks.get_llm_provider()

        assert provider.name == "openai"

    def test_no_providers_available_raises_error(self):
        """Test ProviderError raised when no providers available."""
        config = ProviderConfig()  # No API keys
        factory = ProviderFactory(config)

        with pytest.raises(ProviderError) as exc_info:
            factory.get_stt_provider()

        assert "No STT providers available" in str(exc_info.value)

    def test_no_llm_providers_available_raises_error(self):
        """Test ProviderError raised when no LLM providers available."""
        config = ProviderConfig()  # No API keys
        factory = ProviderFactory(config)

        with pytest.raises(ProviderError) as exc_info:
            factory.get_llm_provider()

        assert "No LLM providers available" in str(exc_info.value)


class TestProviderFactoryCaching:
    """Tests for ProviderFactory provider caching."""

    def test_factory_caches_stt_providers(self):
        """Test that factory caches STT provider instances."""
        config = ProviderConfig(gemini_api_key="key")
        factory = ProviderFactory(config)

        # Mock the creator to track calls
        created_count = [0]
        original_create = factory._create_stt_provider

        def tracking_create(provider_type):
            created_count[0] += 1
            return MockSTTProvider(provider_type.value)

        factory._create_stt_provider = tracking_create

        # Get provider twice
        p1 = factory.get_stt_provider()
        p2 = factory.get_stt_provider()

        # Should only create once
        assert created_count[0] == 1
        assert p1 is p2

    def test_factory_caches_llm_providers(self):
        """Test that factory caches LLM provider instances."""
        config = ProviderConfig(openai_api_key="key")
        factory = ProviderFactory(config)

        created_count = [0]

        def tracking_create(provider_type):
            created_count[0] += 1
            return MockLLMProvider(provider_type.value)

        factory._create_llm_provider = tracking_create

        p1 = factory.get_llm_provider()
        p2 = factory.get_llm_provider()

        assert created_count[0] == 1
        assert p1 is p2

    def test_factory_clear_cache(self):
        """Test clearing provider cache."""
        config = ProviderConfig(gemini_api_key="key")
        factory = ProviderFactory(config)

        factory._create_stt_provider = lambda pt: MockSTTProvider(pt.value)

        p1 = factory.get_stt_provider()
        factory.clear_cache()
        p2 = factory.get_stt_provider()

        # After clearing, should be new instance
        assert p1 is not p2


class TestProviderFactoryStatus:
    """Tests for provider status reporting."""

    def test_get_provider_status(self):
        """Test getting overall provider status."""
        config = ProviderConfig(
            gemini_api_key="g-key",
            openai_api_key="o-key"
        )
        factory = ProviderFactory(config)

        # Mock providers
        factory._stt_cache[ProviderType.GEMINI] = MockSTTProvider("gemini", available=True)
        factory._llm_cache[ProviderType.OPENAI] = MockLLMProvider("openai", available=True)

        status = factory.get_status()

        assert "stt" in status
        assert "llm" in status
        assert status["stt"]["available"]
        assert status["llm"]["available"]
