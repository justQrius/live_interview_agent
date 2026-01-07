from typing import List, Dict, AsyncGenerator
from anthropic import AsyncAnthropic
from ..base import LLMProvider

class AnthropicLLMProvider(LLMProvider):
    """
    Anthropic Claude implementation of LLMProvider.
    """
    
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20240620"
        
    async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from Claude 3.5 Sonnet.
        """
        # Construct system prompt with context
        system_prompt = f"Use the following context to answer the user's question:\n\n{context}"
        
        # Construct messages list
        # Copy history to avoid modifying the original list
        messages = list(history)
        messages.append({"role": "user", "content": prompt})
        
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
