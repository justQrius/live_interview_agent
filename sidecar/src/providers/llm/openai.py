import logging
from typing import List, Dict, AsyncGenerator, Optional
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from sidecar.src.providers.base import LLMProvider

logger = logging.getLogger(__name__)

class OpenAILLMProvider(LLMProvider):
    """
    OpenAI implementation of the LLMProvider interface.
    Uses GPT-4o for response generation.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize the OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
        """
        if not api_key:
            raise ValueError("API key is required for OpenAI provider")
            
        if AsyncOpenAI is None:
            raise ImportError(
                "openai package is not installed. "
                "Please install it with: pip install openai"
            )
            
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        
    async def generate_response(
        self, 
        prompt: str, 
        context: str, 
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from OpenAI.
        
        Args:
            prompt: The user query
            context: Retrieved context
            history: Conversation history
            
        Yields:
            String chunks of the response
        """
        messages = self._construct_messages(prompt, context, history)
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {e}")
            raise

    def _construct_messages(self, prompt: str, context: str, history: List[Dict]) -> List[Dict]:
        """
        Construct message list for the API.
        
        Args:
            prompt: The user query
            context: Retrieved context
            history: Conversation history
            
        Returns:
            List of message dictionaries
        """
        # System prompt
        system_content = (
            "You are a helpful interview assistant. "
            "Your goal is to provide concise, relevant, and accurate answers "
            "to interview questions based on the provided context. "
            "If the context doesn't contain the answer, use your general knowledge "
            "but mention that it's not in the context. "
            "Keep answers professional and to the point."
        )
        
        messages = [{"role": "system", "content": system_content}]
        
        # History (limit to last 10 messages to avoid context overflow)
        # Assuming history format matches OpenAI's expected format (role/content)
        # If history comes from our internal storage, it might need mapping
        for msg in history[-10:]:
            role = msg.get("role", "user")
            # Map 'interviewer' to 'user' and 'assistant' to 'assistant'
            if role == "interviewer":
                role = "user"
            elif role == "user": # In our app, 'user' usually means the candidate, but here we treat it as assistant/user interaction
                 role = "user"
                 
            messages.append({
                "role": role,
                "content": msg.get("content", "")
            })
            
        # Current input with context injection
        user_content = f"""
Context:
{context}

Question:
{prompt}
"""
        messages.append({"role": "user", "content": user_content})
        
        return messages
