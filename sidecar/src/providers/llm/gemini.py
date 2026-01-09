"""
Gemini LLM Provider.

Implements LLMProvider interface using Google's Gemini model
for generating contextual answers in interviews.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

import google.generativeai as genai

from ..base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiLLMProviderError(Exception):
    """Exception raised when Gemini LLM provider operations fail."""
    pass


class GeminiLLMProvider(LLMProvider):
    """
    LLM provider using Google Gemini.

    Implements the LLMProvider interface for the provider factory system.
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

    DEFAULT_MODEL = "gemini-3-flash-preview"

    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        Initialize Gemini LLM provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-3-flash-preview)

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
            self._model = genai_any.GenerativeModel(self._model_name)
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
        Build the full prompt including context and history.

        Args:
            prompt: The user's question/prompt
            context: Retrieved context from RAG
            history: Conversation history

        Returns:
            Formatted prompt string
        """
        parts = []

        # System instruction
        parts.append(
            "You are a helpful interview assistant for a job candidate. "
            "Respond in first person as the candidate (use 'I'). "
            "Prefer facts supported by the provided context; do not invent schools, titles, companies, dates, or metrics. "
            "If a detail is not supported by the context, omit it or say it's not in the context. "
            "Do not repeat sentences or paragraphs; if you start repeating, stop and continue with new information. "
            "For introductory questions (e.g., 'Who are you?', 'Tell me about yourself', 'What have you studied?', 'What's your experience?'), "
            "answer as a 30–60 second pitch: one-line headline (role + focus); one line education; 2–3 experience bullets; one-line current focus + relevance."
        )


        # Add context if provided
        if context:
            parts.append(f"\nContext:\n{context}")

        # Add conversation history if provided
        if history:
            parts.append("\nConversation history:")
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role.capitalize()}: {content}")

        # Add the current question
        parts.append(f"\nQuestion:\n{prompt}")

        # Add instruction for response style
        parts.append(
            "\nAnswer the question clearly and concisely based on the context provided. "
            "If the context is not relevant, answer based on your general knowledge "
            "but mention that the context didn't help. "
            "Keep the answer conversational but professional."
        )

        return "\n".join(parts)

    async def generate_response(
        self,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.

        Implements the LLMProvider interface.

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
