"""
OpenAI LLM Provider.

Implements LLMProvider interface using OpenAI's GPT models
for generating high-quality interview answers.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, cast

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..base import LLMProvider
from .prompts import build_system_prompt, format_context_for_prompt

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """
    OpenAI implementation of the LLMProvider interface.
    
    Uses GPT-4o for response generation with enhanced prompting
    for high-quality, conversational interview answers.
    """

    # Optimized parameters based on research
    DEFAULT_TEMPERATURE = 0.45  # Balanced: natural variation + consistency
    DEFAULT_FREQUENCY_PENALTY = 0.55  # Stronger penalty to prevent repetition
    DEFAULT_PRESENCE_PENALTY = 0.25  # Encourage topic diversity
    DEFAULT_TOP_P = 0.9  # Nucleus sampling for quality
    
    def __init__(self, api_key: str, model: str = "gpt-4o", thinking_budget: int | None = None):
        """
        Initialize the OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
            thinking_budget: Optional token budget for thinking (simulated via CoT prompt)
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
        
    async def generate_response(
        self, 
        prompt: str, 
        context: str, 
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from OpenAI.
        
        Uses dynamic prompt construction based on question type
        for optimal response quality.
        
        Args:
            prompt: The user query (interview question)
            context: Retrieved context from RAG
            history: Conversation history
            
        Yields:
            String chunks of the response
        """
        messages = self._construct_messages(prompt, context, history)
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=cast(Any, messages),
                stream=True,
                temperature=self.DEFAULT_TEMPERATURE,
                frequency_penalty=self.DEFAULT_FREQUENCY_PENALTY,
                presence_penalty=self.DEFAULT_PRESENCE_PENALTY,
                top_p=self.DEFAULT_TOP_P,
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {e}")
            raise

    def _construct_messages(
        self, prompt: str, context: str, history: List[Dict]
    ) -> List[Dict[str, str]]:
        """
        Construct message list for the API with enhanced prompting.
        
        Uses dynamic system prompt based on question classification
        (behavioral, intro, technical, etc.) for optimal responses.
        
        Args:
            prompt: The user query (interview question)
            context: Retrieved context from RAG
            history: Conversation history
            
        Returns:
            List of message dictionaries for OpenAI API
        """
        system_content, question_type = build_system_prompt(
            prompt,
            candidate_profile=self._candidate_profile or ""
        )
        
        # Add CoT instruction if thinking budget is set
        if self._thinking_budget:
            system_content += "\n\nThinking Process:\nBefore answering, think through the requirements, user intent, and potential pitfalls step-by-step in <thinking> tags. Then provide the final answer."

        formatted_context = format_context_for_prompt(context, question_type)
        
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content}
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
            elif role not in ("user", "assistant", "system"):
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
