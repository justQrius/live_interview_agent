"""
Gemini LLM Provider.

Implements LLMProvider interface using the unified GeminiClient (google-genai SDK)
for generating high-quality interview answers with advanced features like Caching and Thinking.
"""

import asyncio
import logging
import threading
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

from ..gemini_client import GeminiClient
from ..base import LLMProvider
from ..config import GeminiModels
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

    DEFAULT_MODEL = GeminiModels.DEFAULT_LLM
    
    def __init__(
        self, 
        api_key: str, 
        model_name: Optional[str] = None, 
        thinking_budget: Optional[int] = None,
        search_enabled: bool = False
    ):
        """
        Initialize Gemini LLM provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use
            thinking_budget: Optional token budget for thinking
            search_enabled: Enable Google Search grounding for real-time information
        """
        super().__init__()
        
        if not api_key:
            raise ValueError("API key is required")
            
        self._api_key = api_key
        self._model_name = model_name or self.DEFAULT_MODEL
        self._thinking_budget = thinking_budget
        self._search_enabled = search_enabled
        self._cached_content_name = None
        self._client = None
        self._candidate_profile = None  # Store profile for injection
        
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the unified Gemini client."""
        try:
            self._client = GeminiClient(self._api_key)
            logger.info(f"Initialized Gemini Client with model {self._model_name}")
        except Exception as e:
            raise GeminiLLMProviderError(f"Failed to initialize Gemini client: {e}")

    def set_candidate_profile(self, profile: str):
        """Set candidate profile context."""
        self._candidate_profile = profile

    def set_cached_content(self, cached_content_name: str):
        """Set the cached content resource name."""
        self._cached_content_name = cached_content_name
        logger.info(f"Using cached content: {cached_content_name}")

    def has_cached_content(self) -> bool:
        """Check if cached content is currently active."""
        return bool(self._cached_content_name)

    def clear_cache(self):
        """Clear the cached content reference."""
        self._cached_content_name = None

    def _build_prompt(self, prompt: str, context: str, history: List[Dict]) -> tuple[str, str]:
        """
        Build the prompt including system instructions and context.
        Returns (full_user_content, system_instruction).
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
        Generate streaming response with automatic model fallback.
        """
        # Define fallback models in order of preference
        models_to_try = [self._model_name]
        
        # Add fallbacks if not already the default
        if GeminiModels.FLASH_3 != self._model_name:
            models_to_try.append(GeminiModels.FLASH_3)
        if GeminiModels.PRO_2_5 != self._model_name:
            models_to_try.append(GeminiModels.PRO_2_5)
        if GeminiModels.FLASH_2_5 != self._model_name:
            models_to_try.append(GeminiModels.FLASH_2_5)
        
        # Legacy fallbacks (Safety net for real-world API compatibility)
        models_to_try.append(GeminiModels.FLASH_1_5)
        models_to_try.append(GeminiModels.PRO_1_5)
            
        last_error = None
        
        # Configuration for retries
        MAX_RETRIES_PER_MODEL = 3
        BASE_DELAY = 2.0
        
        for attempt_idx, model_attempt in enumerate(models_to_try):
            # Inner retry loop for 503/429/Overloaded errors on the SAME model
            # We try once + MAX_RETRIES_PER_MODEL
            for retry_count in range(MAX_RETRIES_PER_MODEL + 1):
                try:
                    if not self._client:
                        raise GeminiLLMProviderError("Gemini client is not initialized")
                    
                    # Re-build prompt on every retry to support dynamic cache fallback
                    # If cache was cleared due to 403/404, this will re-inject RAG context
                    full_prompt, system_instruction = self._build_prompt(prompt, context, history)

                    # Determine thinking budget
                    # All these models support thinking per user instruction
                    thinking = self._thinking_budget
                    
                    # Log fallback if happening (only on first attempt for this model)
                    if model_attempt != self._model_name and retry_count == 0:
                        logger.warning(
                            f"Fallback attempt {attempt_idx}/{len(models_to_try)-1}: "
                            f"Switching to {model_attempt} due to quota exhaustion or overload"
                        )
                    
                    loop = asyncio.get_running_loop()
                    client = self._client
                    
                    # If we are using a cache, we MUST NOT send system_instruction or tools
                    # (they conflict with the cache configuration)
                    effective_system_instruction = system_instruction
                    if self._cached_content_name:
                        if attempt_idx == 0 and retry_count == 0:
                            logger.info("Using cached content - suppressing per-request system prompt")
                        effective_system_instruction = None
                    
                    # Enable web search if configured and not using cache
                    use_search = self._search_enabled and not self._cached_content_name
                    
                    def run_generate():
                        return client.generate_content(
                            model=model_attempt,
                            contents=full_prompt,
                            cached_content_name=self._cached_content_name,
                            system_instruction=effective_system_instruction,
                            thinking_budget=thinking,
                            web_search=use_search,
                            stream=True
                        )
                    
                    response = await loop.run_in_executor(None, run_generate)
                    
                    # The response is a synchronous iterator/generator
                    # We need to iterate it in a separate thread to avoid blocking the asyncio loop
                    
                    # Queue for bridging sync thread to async loop
                    queue = asyncio.Queue()
                    
                    def consume_stream(iterator):
                        try:
                            for chunk in iterator:
                                loop.call_soon_threadsafe(queue.put_nowait, chunk)
                            loop.call_soon_threadsafe(queue.put_nowait, None) # Sentinel
                        except Exception as e:
                            loop.call_soon_threadsafe(queue.put_nowait, e)
                            
                    # Start consumer thread
                    threading.Thread(target=consume_stream, args=(response,), daemon=True).start()
                    
                    # Flag to track if we successfully yielded at least one chunk
                    # If we yield even one chunk, we consider this model working and don't fallback further
                    yielded_any = False
                    
                    while True:
                        # Wait for next chunk from thread
                        chunk = await queue.get()
                        
                        # Check for sentinel (end of stream)
                        if chunk is None:
                            break
                            
                        # Check for exception from thread
                        if isinstance(chunk, Exception):
                            raise chunk
                            
                        if hasattr(chunk, 'text') and chunk.text:
                            yield chunk.text
                            yielded_any = True
                        elif hasattr(chunk, 'candidates') and chunk.candidates:
                             # Fallback for structured response access
                             if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                                 parts = chunk.candidates[0].content.parts
                                 for part in parts:
                                     # Handle thinking trace (Phase 7 Gen 1)
                                     if hasattr(part, 'thought') and part.thought:
                                         # Format thoughts as blockquotes for UI rendering
                                         yield f"\n> *Thinking: {part.thought}*\n\n"
                                         yielded_any = True
                                     
                                     if hasattr(part, 'text') and part.text:
                                         yield part.text
                                         yielded_any = True
                    
                    # If we finished successfully, break the fallback loop (return from function)
                    return
                
                except Exception as e:
                    error_str = str(e).lower()
                    is_quota_error = "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str
                    is_server_error = "503" in error_str or "overloaded" in error_str or "unavailable" in error_str
                    
                    # New: Check for Cache-specific errors (403 Permission Denied or 404 Not Found)
                    is_cache_error = self._cached_content_name and (
                        "403" in error_str or "permission_denied" in error_str or
                        "404" in error_str or "not found" in error_str or
                        "cachedcontent" in error_str
                    )

                    last_error = e
                    
                    # Handle Cache Failure -> Fallback to RAG
                    if is_cache_error:
                        logger.warning(
                            f"Gemini Cache invalid or expired ({e}). "
                            f"Clearing cache reference and falling back to RAG context."
                        )
                        # Clear cache reference
                        self._cached_content_name = None
                        # DO NOT increment retry_count or sleep - immediately retry with RAG
                        # The next iteration will call _build_prompt again, which detects
                        # self._cached_content_name is None and inserts context.
                        continue
                    
                    # Retry on 503 (Server Error) OR 429 (Rate Limit) for the SAME model first
                    if is_server_error or is_quota_error:
                        if retry_count < MAX_RETRIES_PER_MODEL:
                            delay = BASE_DELAY * (2 ** retry_count)
                            logger.warning(
                                f"Gemini {model_attempt} error ({'Server Error' if is_server_error else 'Rate Limit'}). "
                                f"Retrying in {delay}s (Attempt {retry_count + 1}/{MAX_RETRIES_PER_MODEL})..."
                            )
                            await asyncio.sleep(delay)
                            continue # Retry same model
                        else:
                            # Max retries reached for this model
                            logger.warning(f"Gemini {model_attempt} failed after {MAX_RETRIES_PER_MODEL} retries. Trying next model if available.")
                            break # Break inner loop to try next model
                            
                    else:
                        # Not a retryable error
                        logger.error(f"Gemini LLM error on {model_attempt}: {e}")
                        raise GeminiLLMProviderError(f"Generation failed with non-retryable error: {e}")

            # If loop finished naturally (break from quota/503 max retries), we fall through here.
            # Loop continues to next model if available.
            
            if attempt_idx == len(models_to_try) - 1:
                # If this was the last model, we must raise
                raise GeminiLLMProviderError(f"Generation failed after fallback: {last_error}")

    async def generate_answer(
        self,
        question: str,
        context_chunks: List[str]
    ) -> AsyncGenerator[str, None]:
        """Backwards compatible wrapper."""
        context = "\n\n".join(context_chunks) if context_chunks else ""
        async for chunk in self.generate_response(question, context, []):
            yield chunk
