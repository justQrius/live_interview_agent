"""
Gemini LLM Provider.

Implements LLMProvider interface using the unified GeminiClient (google-genai SDK)
for generating high-quality interview answers with advanced features like Caching and Thinking.
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

from ..gemini_client import GeminiClient
from ..base import LLMProvider
from .prompts import build_system_prompt, format_context_for_prompt

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60


class GeminiLLMProviderError(Exception):
    """Exception raised when Gemini LLM provider operations fail."""
    pass


class GeminiLLMProvider(LLMProvider):
    """
    LLM provider using Google Gemini via Unified Client.
    
    Features:
    - Context Caching
    - Thinking Mode
    - Grounding (Web Search)
    - System Instructions
    """

    DEFAULT_MODEL = "gemini-3-pro-preview"  # Centralized in config.py as GeminiModels.DEFAULT_LLM
    
    def __init__(self, api_key: str, model_name: Optional[str] = None, thinking_budget: Optional[int] = None):
        """
        Initialize Gemini LLM provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use
            thinking_budget: Optional token budget for thinking
        """
        super().__init__()
        
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._model_name = model_name or self.DEFAULT_MODEL
        self._available = False
        self._client: Optional[GeminiClient] = None
        self._cached_content_name: Optional[str] = None
        self._thinking_budget: int = thinking_budget or 1024 

        try:
            self._client = GeminiClient(api_key=api_key)
            self._available = True
        except Exception as e:
            raise GeminiLLMProviderError(f"Failed to initialize Gemini client: {e}")

    def is_available(self) -> bool:
        """Check availability."""
        return self._available
    
    def set_cached_content(self, cache_name: str) -> None:
        """Set the cached content resource name to use for requests."""
        self._cached_content_name = cache_name
        logger.info(f"Gemini provider switched to cached context: {cache_name}")

    def _build_prompt(
        self,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> tuple[str, str]:
        """
        Build prompt and system instruction.
        
        Cache-First Architecture:
        - When file-based cache is available, skip RAG context (cache has full docs)
        - When no cache, include RAG context for grounding
        
        Returns:
            Tuple of (full_prompt_content, system_instruction)
        """
        system_content, question_type = build_system_prompt(
            prompt,
            candidate_profile=self._candidate_profile or ""
        )
        
        parts = []
        
        # Cache-First: Only include RAG context if NO cache is set
        # When cache is available, it contains full documents with proper attribution
        # RAG chunks would be redundant and could cause confusion
        if context and not self._cached_content_name:
            formatted_context = format_context_for_prompt(context, question_type)
            if formatted_context:
                parts.append(f"Relevant Context:\n{formatted_context}")
        elif self._cached_content_name:
            # Cache is set - remind model to use cached documents
            parts.append("(Use the uploaded documents in cache for context. Resume = YOUR background.)")

        if history:
            parts.append("\n## Conversation History:")
            for msg in history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    display_role = "Interviewer" if role in ("user", "interviewer") else "You (Candidate)"
                    parts.append(f"{display_role}: {content}")

        parts.append(f"\n## Current Question:\n{prompt}")

        return "\n".join(parts), system_content

    async def generate_response(
        self,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response.
        """
        full_prompt, system_instruction = self._build_prompt(prompt, context, history)

        try:
            if not self._client:
                raise GeminiLLMProviderError("Gemini client is not initialized")
            
            # Determine thinking budget - disable for simple queries if needed
            # For now, always enable if model supports it (Gemini 2.0 Flash Thinking)
            thinking = self._thinking_budget if "thinking" in self._model_name else None
            
            # Run generation in executor to avoid blocking loop (SDK might be sync or async?)
            # My GeminiClient wrapper uses standard sync client.
            # So I need to wrap it in run_in_executor.
            
            loop = asyncio.get_running_loop()
            
            client = self._client
            
            def run_generate():
                return client.generate_content(
                    model=self._model_name,
                    contents=full_prompt,
                    cached_content_name=self._cached_content_name,
                    system_instruction=system_instruction,
                    thinking_budget=thinking,
                    stream=True
                )
            
            response = await loop.run_in_executor(None, run_generate)
            
            # The response is a synchronous iterator/generator
            # We need to iterate it in a way that yields back to asyncio
            
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text
                elif hasattr(chunk, 'candidates') and chunk.candidates:
                     # Fallback for structured response access
                     parts = chunk.candidates[0].content.parts
                     for part in parts:
                         if part.text:
                             yield part.text
                             
                # Give other tasks a chance to run
                await asyncio.sleep(0)
            
        except Exception as e:
             logger.error(f"Gemini LLM error: {e}")
             raise GeminiLLMProviderError(f"Generation failed: {e}")

    async def generate_answer(
        self,
        question: str,
        context_chunks: List[str]
    ) -> AsyncGenerator[str, None]:
        """Backwards compatible wrapper."""
        context = "\n\n".join(context_chunks) if context_chunks else ""
        async for chunk in self.generate_response(question, context, []):
            yield chunk
