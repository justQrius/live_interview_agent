"""
Gemini LLM Provider.

Implements LLMProvider interface using Google's Gemini model
for generating high-quality interview answers.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

import google.generativeai as genai

from ..base import LLMProvider
from .prompts import build_system_prompt, format_context_for_prompt

logger = logging.getLogger(__name__)


class GeminiLLMProviderError(Exception):
    """Exception raised when Gemini LLM provider operations fail."""
    pass


class GeminiLLMProvider(LLMProvider):
    """
    LLM provider using Google Gemini.

    Implements the LLMProvider interface for the provider factory system.
    Uses enhanced prompting for high-quality, conversational interview answers.
    Also provides backwards-compatible generate_answer() method for
    existing server.py integration.

    Usage:
        provider = GeminiLLMProvider(api_key="...")
        async for chunk in provider.generate_response(prompt, context, history):
            print(chunk, end="")

        # Or backwards-compatible method:
        async for chunk in provider.generate_answer(question, context_chunks):
            print(chunk, end="")
    """

    DEFAULT_MODEL = "gemini-2.0-flash"
    
    # Gemini generation config - optimized for natural responses
    GENERATION_CONFIG = {
        "temperature": 0.45,  # Balanced: natural variation + consistency
        "top_p": 0.9,  # Nucleus sampling for quality
        "top_k": 40,  # Reasonable diversity
    }

    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        Initialize Gemini LLM provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-2.0-flash)

        Raises:
            ValueError: If API key is empty
            GeminiLLMProviderError: If client initialization fails
        """
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._model_name = model_name or self.DEFAULT_MODEL
        self._available = False
        self._model = None

        try:
            genai_any = cast(Any, genai)
            genai_any.configure(api_key=api_key)
            self._model = genai_any.GenerativeModel(
                self._model_name,
                generation_config=self.GENERATION_CONFIG
            )
            self._available = True
        except Exception as e:
            raise GeminiLLMProviderError(f"Failed to initialize Gemini client: {e}")

    def is_available(self) -> bool:
        """
        Check if the provider is available.

        Returns:
            True if the provider is ready to accept requests
        """
        return self._available

    def _build_prompt(
        self,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> str:
        """
        Build the full prompt including system instructions, context, and history.

        Uses dynamic prompt construction based on question classification
        (behavioral, intro, technical, etc.) for optimal responses.

        Args:
            prompt: The user's question/prompt
            context: Retrieved context from RAG
            history: Conversation history

        Returns:
            Formatted prompt string
        """
        # Build dynamic system prompt based on question type
        system_content, question_type = build_system_prompt(prompt)
        
        # Format context based on question type  
        formatted_context = format_context_for_prompt(context, question_type)
        
        parts = [system_content]

        # Add formatted context if provided
        if formatted_context:
            parts.append(f"\n{formatted_context}")

        # Add conversation history if provided
        if history:
            parts.append("\n## Conversation History:")
            for msg in history[-10:]:  # Limit to last 10
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    # Map roles for clarity
                    display_role = "Interviewer" if role in ("user", "interviewer") else "You (Candidate)"
                    parts.append(f"{display_role}: {content}")

        # Add the current question
        parts.append(f"\n## Current Question:\n{prompt}")

        return "\n".join(parts)

    async def generate_response(
        self,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.

        Implements the LLMProvider interface with enhanced prompting
        for high-quality interview answers.

        Args:
            prompt: The user query or current prompt
            context: Retrieved context from RAG
            history: Conversation history (list of dicts with 'role' and 'content')

        Yields:
            String chunks of the response

        Raises:
            GeminiLLMProviderError: If generation fails
        """
        full_prompt = self._build_prompt(prompt, context, history)

        try:
            if not self._model:
                raise GeminiLLMProviderError("Gemini model is not initialized")

            model = cast(Any, self._model)
            response = await model.generate_content_async(full_prompt, stream=True)

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except GeminiLLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Gemini LLM error: {e}")
            raise GeminiLLMProviderError(f"Generation failed: {e}")

    async def generate_answer(
        self,
        question: str,
        context_chunks: List[str]
    ) -> AsyncGenerator[str, None]:
        """
        Generate an answer for the given question and context.

        This is a backwards-compatible method that matches the old GeminiLLM interface.
        It delegates to generate_response() internally.

        Args:
            question: The user's question
            context_chunks: List of context strings from RAG retrieval

        Yields:
            Chunks of the generated answer

        Raises:
            GeminiLLMProviderError: If generation fails
        """
        # Join context chunks into a single string
        context = "\n\n".join(context_chunks) if context_chunks else ""

        # Delegate to the standard interface method
        async for chunk in self.generate_response(
            prompt=question,
            context=context,
            history=[]  # No history for backwards-compatible interface
        ):
            yield chunk
