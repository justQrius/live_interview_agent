"""
LLM providers package.

Contains implementations of LLMProvider interface for various providers,
along with enhanced prompting utilities for high-quality interview answers.
"""
from .gemini import GeminiLLMProvider, GeminiLLMProviderError
from .openai import OpenAILLMProvider
from .anthropic import AnthropicLLMProvider
from .prompts import (
    classify_question,
    build_system_prompt,
    format_context_for_prompt,
    MASTER_SYSTEM_PROMPT,
)

__all__ = [
    # Providers
    "GeminiLLMProvider",
    "GeminiLLMProviderError",
    "OpenAILLMProvider",
    "AnthropicLLMProvider",
    # Prompt utilities
    "classify_question",
    "build_system_prompt",
    "format_context_for_prompt",
    "MASTER_SYSTEM_PROMPT",
]
