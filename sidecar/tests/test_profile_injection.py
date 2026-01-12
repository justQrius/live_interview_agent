"""
Tests for Profile Injection in LLM Providers (STORY-069).

Tests that:
1. LLMProvider base class handles profile state correctly
2. Profile injection modifies system prompts in all providers
3. Profile injection respects token limits
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.providers.base import LLMProvider
from src.providers.llm.openai import OpenAILLMProvider
from src.providers.llm.anthropic import AnthropicLLMProvider
from src.providers.llm.gemini import GeminiLLMProvider
from src.providers.llm.prompts import build_system_prompt


# ============================================================================
# Base Class Tests
# ============================================================================

class TestLLMProviderBase:
    """Test base class functionality."""
    
    class ConcreteLLMProvider(LLMProvider):
        """Concrete implementation for testing base class."""
        async def generate_response(self, prompt, context, history):
            yield "response"

    def test_set_and_clear_profile(self):
        """Test setting and clearing candidate profile."""
        provider = self.ConcreteLLMProvider()
        
        assert not provider.has_candidate_profile()
        assert provider.candidate_profile is None
        
        profile_text = "## Candidate Profile\nExperienced Engineer..."
        provider.set_candidate_profile(profile_text)
        
        assert provider.has_candidate_profile()
        assert provider.candidate_profile == profile_text
        
        provider.clear_candidate_profile()
        assert not provider.has_candidate_profile()
        assert provider.candidate_profile is None

    def test_token_limit_warning(self):
        """Test that setting a large profile logs a warning."""
        provider = self.ConcreteLLMProvider()
        long_profile = "word " * 2000  # ~2000 tokens, well over 1000 limit
        
        with patch('src.providers.base.logger') as mock_logger:
            provider.set_candidate_profile(long_profile)
            mock_logger.warning.assert_called_once()
            assert "exceeds recommended token limit" in mock_logger.warning.call_args[0][0]


# ============================================================================
# Prompt Builder Tests
# ============================================================================

class TestPromptBuilder:
    """Test prompt construction with profile injection."""
    
    def test_build_system_prompt_with_profile(self):
        """Test that profile is injected at start of system prompt."""
        profile = "## Candidate Profile\nTest Profile Content"
        question = "Tell me about yourself"
        
        system_prompt, q_type = build_system_prompt(question, candidate_profile=profile)
        
        assert profile in system_prompt
        assert system_prompt.startswith(profile)
        assert "\n---\n" in system_prompt
        assert "You are an expert interview coach" in system_prompt
        assert q_type == "intro"

    def test_build_system_prompt_without_profile(self):
        """Test system prompt without profile."""
        question = "Tell me about yourself"
        
        system_prompt, q_type = build_system_prompt(question, candidate_profile="")
        
        assert "## Candidate Profile" not in system_prompt
        assert system_prompt.startswith("You are an expert interview coach")


# ============================================================================
# Provider Integration Tests
# ============================================================================

class TestOpenAILLMProvider:
    """Test OpenAI provider integration."""
    
    @patch('src.providers.llm.openai.AsyncOpenAI')
    def test_construct_messages_includes_profile(self, mock_openai):
        """Test that constructed messages include profile in system prompt."""
        provider = OpenAILLMProvider(api_key="test-key")
        profile = "## Candidate Profile\nTest Content"
        provider.set_candidate_profile(profile)
        
        messages = provider._construct_messages(
            prompt="Test question",
            context="Context",
            history=[]
        )
        
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert profile in system_msg["content"]
        assert "You are an expert interview coach" in system_msg["content"]


class TestAnthropicLLMProvider:
    """Test Anthropic provider integration."""
    
    @patch('src.providers.llm.anthropic.AsyncAnthropic')
    @patch('src.providers.llm.anthropic.build_system_prompt')
    def test_generate_response_uses_profile(self, mock_build_prompt, mock_anthropic):
        """Test that generate_response passes profile to build_system_prompt."""
        mock_build_prompt.return_value = ("System Prompt", "general")
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.stream.return_value.__aenter__.return_value.text_stream = AsyncMock()
        
        provider = AnthropicLLMProvider(api_key="test-key")
        profile = "## Candidate Profile\nTest Content"
        provider.set_candidate_profile(profile)
        
        # Trigger generation
        async def run_gen():
            async for _ in provider.generate_response("Q", "Ctx", []):
                pass
        
        import asyncio
        asyncio.run(run_gen())
        
        # Verify build_system_prompt called with profile
        mock_build_prompt.assert_called_with("Q", candidate_profile=profile)


class TestGeminiLLMProvider:
    """Test Gemini provider integration."""

    @patch("src.providers.llm.gemini.GeminiClient")
    def test_build_prompt_includes_profile(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()

        provider = GeminiLLMProvider(api_key="test-key")
        profile = "## Candidate Profile\nTest Content"
        provider.set_candidate_profile(profile)

        full_prompt, system_prompt = provider._build_prompt(
            prompt="Test question",
            context="Context",
            history=[],
        )

        assert "Test question" in full_prompt
        assert profile in system_prompt
        assert system_prompt.startswith(profile)
        assert "You are an expert interview coach" in system_prompt
