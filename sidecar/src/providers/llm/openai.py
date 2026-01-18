"""
OpenAI LLM Provider.

Implements LLMProvider interface using OpenAI's GPT models
for generating high-quality interview answers.

Supports:
- GPT-4o and GPT-5 series (gpt-5.2, gpt-5.1, gpt-5-mini, gpt-5-nano)
- Reasoning models (o1, o1-mini, o1-preview, o3, o3-mini, o4-mini)
- Automatic model fallback with retry logic
- Model-specific parameter handling (reasoning models have restrictions)
- Search Grounding via external SearchProvider (e.g. DuckDuckGo)
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, cast

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..base import LLMProvider, SearchProvider
from ..config import OpenAIModels
from .prompts import build_system_prompt, format_context_for_prompt

logger = logging.getLogger(__name__)


class OpenAILLMProviderError(Exception):
    """Exception raised when OpenAI LLM provider operations fail."""
    pass


class OpenAILLMProvider(LLMProvider):
    """
    OpenAI implementation of the LLMProvider interface.
    
    Uses GPT models for response generation with enhanced prompting
    for high-quality, conversational interview answers.
    
    Features:
    - Automatic model fallback chain
    - Retry logic for transient errors (429, 503)
    - Model-specific parameter handling for reasoning models
    - Thinking mode support via reasoning_effort
    - Search Grounding via injected SearchProvider
    """

    # Optimized parameters for non-reasoning models
    DEFAULT_TEMPERATURE = 0.45  # Balanced: natural variation + consistency
    DEFAULT_FREQUENCY_PENALTY = 0.55  # Stronger penalty to prevent repetition
    DEFAULT_PRESENCE_PENALTY = 0.25  # Encourage topic diversity
    DEFAULT_TOP_P = 0.9  # Nucleus sampling for quality
    
    # Models that do NOT support sampling parameters
    # These are reasoning models with fixed temperature=1 and no penalties
    REASONING_MODELS: Set[str] = {
        # O-series reasoning models
        "o1", "o1-mini", "o1-preview",
        "o3", "o3-mini",
        "o4-mini",
        # GPT-5 reasoning models (only support temperature=1)
        "gpt-5.1", "gpt-5.2", "gpt-5-mini", "gpt-5-nano",
    }
    
    # Models that support reasoning_effort parameter
    REASONING_EFFORT_MODELS: Set[str] = {
        "o1", "o1-mini", "o1-preview",
        "o3", "o3-mini",
        "o4-mini",
    }
    
    # Retry configuration
    MAX_RETRIES_PER_MODEL = 3
    BASE_DELAY = 2.0
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-4o", 
        thinking_budget: int | None = None,
        reasoning_effort: str | None = None,
        search_provider: Optional[SearchProvider] = None,
        search_enabled: bool = False
    ):
        """
        Initialize the OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
            thinking_budget: Optional token budget for thinking (used via CoT prompt or reasoning_effort)
            reasoning_effort: Optional reasoning effort level ('low', 'medium', 'high') for o-series models
            search_provider: Optional SearchProvider for grounding
            search_enabled: Whether search is enabled
        """
        super().__init__()
        
        if not api_key:
            raise ValueError("API key is required for OpenAI provider")
            
        if AsyncOpenAI is None:
            raise ImportError(
                "openai package is not installed. "
                "Please install it with: pip install openai"
            )
            
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._thinking_budget = thinking_budget
        self._reasoning_effort = reasoning_effort or self._infer_reasoning_effort(thinking_budget)
        self.search_provider = search_provider
        self.search_enabled = search_enabled
        
    def _infer_reasoning_effort(self, thinking_budget: int | None) -> str | None:
        """
        Infer reasoning effort from thinking budget for o-series models.
        
        Args:
            thinking_budget: Token budget for thinking
            
        Returns:
            Reasoning effort level or None
        """
        if thinking_budget is None:
            return None
        if thinking_budget <= 512:
            return "low"
        elif thinking_budget <= 2048:
            return "medium"
        else:
            return "high"
    
    def _is_reasoning_model(self, model: str) -> bool:
        """
        Check if a model is a reasoning model with parameter restrictions.
        
        Args:
            model: Model name to check
            
        Returns:
            True if model has sampling parameter restrictions
        """
        model_lower = model.lower()
        
        # Check exact matches
        if model_lower in self.REASONING_MODELS:
            return True
        
        # Check prefixes for versioned models (e.g., o1-2024-12-17)
        reasoning_prefixes = ("o1-", "o3-", "o4-", "gpt-5")
        for prefix in reasoning_prefixes:
            if model_lower.startswith(prefix):
                return True
                
        return False
    
    def _supports_reasoning_effort(self, model: str) -> bool:
        """
        Check if a model supports the reasoning_effort parameter.
        
        Args:
            model: Model name to check
            
        Returns:
            True if model supports reasoning_effort
        """
        model_lower = model.lower()
        
        if model_lower in self.REASONING_EFFORT_MODELS:
            return True
            
        # Check prefixes for versioned models
        for prefix in ("o1-", "o3-", "o4-"):
            if model_lower.startswith(prefix):
                return True
                
        return False
        
    async def generate_response(
        self, 
        prompt: str, 
        context: str, 
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response with automatic model fallback.
        
        Uses dynamic prompt construction based on question type
        for optimal response quality. Includes retry logic for
        transient errors and automatic fallback to alternative models.
        
        Args:
            prompt: The user query (interview question)
            context: Retrieved context from RAG
            history: Conversation history
            
        Yields:
            String chunks of the response
        """
        # Perform search if enabled and provider available
        search_results_text = ""
        if self.search_enabled and self.search_provider:
            try:
                # Basic heuristic: Search if the prompt asks for it or context is missing
                # Ideally we'd use an LLM to decide, but for latency we'll search parallel or strictly
                # For now, let's assume we search if the user asks for "current", "news", "latest", etc.
                # or if we want to ground every response. 
                # To save latency, we'll only search if explicitly enabled and appropriate.
                
                # Simple keyword check for now to avoid search on every turn
                # (Gemini handles this automatically, here we do it manually)
                search_triggers = ["current", "latest", "news", "recent", "today", "company", "industry", "trends", "competitors"]
                should_search = any(trigger in prompt.lower() for trigger in search_triggers)
                
                if should_search:
                    logger.info(f"Triggering search for prompt: {prompt[:50]}...")
                    sources = await self.search_provider.search(prompt, limit=3)
                    if sources:
                        source_text = "\n".join(
                            [f"- {s.title}: {s.snippet} ({s.url})" for s in sources]
                        )
                        search_results_text = f"\n\nREAL-TIME SEARCH RESULTS:\n{source_text}\n(Use these results to ground your answer with current information)"
                        logger.info(f"Found {len(sources)} search results")
            except Exception as e:
                logger.warning(f"Search failed: {e}")

        # Build fallback chain
        models_to_try = self._build_fallback_chain()
        last_error: Optional[Exception] = None
        
        for attempt_idx, model_attempt in enumerate(models_to_try):
            for retry_count in range(self.MAX_RETRIES_PER_MODEL + 1):
                try:
                    # Log fallback if happening
                    if model_attempt != self.model and retry_count == 0:
                        logger.warning(
                            f"Fallback attempt {attempt_idx}/{len(models_to_try)-1}: "
                            f"Switching to {model_attempt} due to previous errors"
                        )
                    
                    async for chunk in self._generate_with_model(
                        model_attempt, prompt, context + search_results_text, history
                    ):
                        yield chunk
                    
                    # Success - exit all loops
                    return
                    
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = "429" in error_str or "rate_limit" in error_str
                    is_server_error = "503" in error_str or "502" in error_str or "overloaded" in error_str
                    is_param_error = "unsupported_parameter" in error_str or "unsupported parameter" in error_str
                    
                    last_error = e
                    
                    # Parameter errors should trigger immediate model fallback, not retry
                    if is_param_error:
                        logger.warning(
                            f"OpenAI {model_attempt} parameter error: {e}. "
                            f"Trying next model if available."
                        )
                        break  # Break inner loop, try next model
                    
                    # Retry on transient errors for the same model
                    if is_rate_limit or is_server_error:
                        if retry_count < self.MAX_RETRIES_PER_MODEL:
                            delay = self.BASE_DELAY * (2 ** retry_count)
                            logger.warning(
                                f"OpenAI {model_attempt} error ({'Rate Limit' if is_rate_limit else 'Server Error'}). "
                                f"Retrying in {delay}s (Attempt {retry_count + 1}/{self.MAX_RETRIES_PER_MODEL})..."
                            )
                            await asyncio.sleep(delay)
                            continue  # Retry same model
                        else:
                            logger.warning(
                                f"OpenAI {model_attempt} failed after {self.MAX_RETRIES_PER_MODEL} retries. "
                                f"Trying next model if available."
                            )
                            break  # Break inner loop, try next model
                    else:
                        # Non-retryable error
                        logger.error(f"OpenAI LLM error on {model_attempt}: {e}")
                        raise OpenAILLMProviderError(f"Generation failed: {e}")
            
            # Check if this was the last model
            if attempt_idx == len(models_to_try) - 1:
                raise OpenAILLMProviderError(f"Generation failed after fallback: {last_error}")
    
    def _build_fallback_chain(self) -> List[str]:
        """
        Build the model fallback chain.
        
        Returns:
            List of models to try in order
        """
        models = [self.model]
        
        # Add fallbacks based on model category
        if self._is_reasoning_model(self.model):
            # For reasoning models, fall back to other reasoning models first
            fallbacks = [
                OpenAIModels.O3_MINI,
                OpenAIModels.GPT5_MINI,
                OpenAIModels.GPT4O,  # Ultimate fallback to non-reasoning
            ]
        else:
            # For standard models, fall back within the same category
            fallbacks = [
                OpenAIModels.GPT4O,
                OpenAIModels.GPT5_MINI,
            ]
        
        # Add fallbacks that aren't already in the list
        for fallback in fallbacks:
            if fallback not in models:
                models.append(fallback)
                
        return models
    
    async def _generate_with_model(
        self,
        model: str,
        prompt: str,
        context: str,
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate response with a specific model.
        
        Handles model-specific parameter selection.
        
        Args:
            model: Model to use
            prompt: User query
            context: RAG context (plus search results)
            history: Conversation history
            
        Yields:
            String chunks of the response
        """
        messages = self._construct_messages(prompt, context, history, model)
        
        # Build request parameters
        request_params: Dict[str, Any] = {
            "model": model,
            "messages": cast(Any, messages),
            "stream": True,
        }
        
        # Add model-specific parameters
        if self._is_reasoning_model(model):
            # Reasoning models: NO sampling parameters allowed
            # Use max_completion_tokens instead of max_tokens
            request_params["max_completion_tokens"] = 4096
            
            # Add reasoning_effort for o-series models
            if self._supports_reasoning_effort(model) and self._reasoning_effort:
                request_params["reasoning_effort"] = self._reasoning_effort
                logger.debug(f"Using reasoning_effort={self._reasoning_effort} for {model}")
        else:
            # Standard models: use optimized sampling parameters
            request_params["temperature"] = self.DEFAULT_TEMPERATURE
            request_params["frequency_penalty"] = self.DEFAULT_FREQUENCY_PENALTY
            request_params["presence_penalty"] = self.DEFAULT_PRESENCE_PENALTY
            request_params["top_p"] = self.DEFAULT_TOP_P
        
        logger.debug(f"OpenAI request params for {model}: {list(request_params.keys())}")
        
        stream = await self.client.chat.completions.create(**request_params)
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _construct_messages(
        self, 
        prompt: str, 
        context: str, 
        history: List[Dict],
        model: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Construct message list for the API with enhanced prompting.
        
        Uses dynamic system prompt based on question classification
        (behavioral, intro, technical, etc.) for optimal responses.
        
        Args:
            prompt: The user query (interview question)
            context: Retrieved context from RAG
            history: Conversation history
            model: Optional model name for model-specific adjustments
            
        Returns:
            List of message dictionaries for OpenAI API
        """
        current_model = model or self.model
        
        system_content, question_type = build_system_prompt(
            prompt,
            candidate_profile=self._candidate_profile or ""
        )
        
        # Add CoT instruction for non-reasoning models with thinking budget
        # For reasoning models, the model handles thinking internally
        if self._thinking_budget and not self._is_reasoning_model(current_model):
            system_content += "\n\nThinking Process:\nBefore answering, think through the requirements, user intent, and potential pitfalls step-by-step in <thinking> tags. Then provide the final answer."

        formatted_context = format_context_for_prompt(context, question_type)
        
        # Use 'developer' role for reasoning models, 'system' for standard models
        # Note: As of 2025, OpenAI recommends 'developer' for system prompts with reasoning models
        system_role = "developer" if self._is_reasoning_model(current_model) else "system"
        
        messages: List[Dict[str, str]] = [
            {"role": system_role, "content": system_content}
        ]
        
        # Add conversation history (limit to last 10 to avoid context overflow)
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            
            if not content:
                continue
                
            # Map internal roles to OpenAI roles
            if role == "interviewer":
                role = "user"
            elif role not in ("user", "assistant", "system", "developer"):
                role = "user"
                
            messages.append({
                "role": role,
                "content": content,
            })
            
        # Current input with formatted context
        user_content = f"""{formatted_context}

Question:
{prompt}"""
        
        messages.append({"role": "user", "content": user_content})
        
        return messages
