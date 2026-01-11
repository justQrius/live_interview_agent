"""
Anthropic LLM Provider.

Implements LLMProvider interface using Anthropic's Claude models
for generating high-quality interview answers.
"""

from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, cast

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

if TYPE_CHECKING:
    from anthropic.types import MessageParam
else:
    MessageParam = Any

from ..base import LLMProvider
from .prompts import build_system_prompt, format_context_for_prompt


def _to_anthropic_messages(
    history: List[Dict[str, Any]], 
    prompt: str,
    formatted_context: str
) -> list[MessageParam]:
    """
    Convert conversation history to Anthropic message format.
    
    Args:
        history: Conversation history
        prompt: Current question
        formatted_context: Pre-formatted context string
        
    Returns:
        List of MessageParam for Anthropic API
    """
    messages: list[MessageParam] = []

    for msg in history[-10:]:
        role_raw = str(msg.get("role", "user")).lower()
        content = str(msg.get("content", ""))
        
        if not content:
            continue

        # Anthropic expects roles: "user" | "assistant"
        role = role_raw if role_raw in ("user", "assistant") else "user"
        messages.append(cast(MessageParam, {"role": role, "content": content}))

    # Add current question with context
    user_content = f"""{formatted_context}

Question:
{prompt}"""
    
    messages.append(cast(MessageParam, {"role": "user", "content": user_content}))
    return messages


class AnthropicLLMProvider(LLMProvider):
    """
    Anthropic Claude implementation of LLMProvider.
    
    Uses Claude 3.5 Sonnet for response generation with enhanced
    prompting for high-quality, conversational interview answers.
    """

    DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
    DEFAULT_MAX_TOKENS = 1024

    def __init__(self, api_key: str, model: str | None = None):
        """
        Initialize the Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-5-sonnet-20240620)
        """
        super().__init__()
        
        if AsyncAnthropic is None:
            raise ImportError(
                "anthropic package is not installed. "
                "Please install it with: pip install anthropic"
            )

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL

    async def generate_response(
        self, 
        prompt: str, 
        context: str, 
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from Anthropic Claude.
        
        Uses dynamic prompt construction based on question type
        for optimal response quality.
        
        Args:
            prompt: The user query (interview question)
            context: Retrieved context from RAG
            history: Conversation history
            
        Yields:
            String chunks of the response
        """
        system_content, question_type = build_system_prompt(
            prompt,
            candidate_profile=self._candidate_profile or ""
        )
        
        formatted_context = format_context_for_prompt(context, question_type)

        messages = _to_anthropic_messages(
            history=history, 
            prompt=prompt,
            formatted_context=formatted_context
        )

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=self.DEFAULT_MAX_TOKENS,
            system=system_content,
            messages=cast(Any, messages),
        ) as stream:
            async for text in stream.text_stream:
                yield text
