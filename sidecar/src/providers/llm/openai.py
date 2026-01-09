import logging
from typing import Any, AsyncGenerator, Dict, List, cast

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..base import LLMProvider

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
                messages=cast(Any, messages),
                stream=True,
                temperature=0.3,
                frequency_penalty=0.4,
                presence_penalty=0.1,
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
            "You are a helpful interview assistant for a job candidate. "
            "Respond in first person as the candidate (use 'I'). "
            "Prefer facts that are supported by the provided context; do not invent schools, titles, companies, dates, or metrics. "
            "If a detail isn't in the context, either omit it or say 'I can share details if helpful.' "
            "Write in a clean, user-friendly format: 1 short headline sentence, then 3-5 bullet points, then a 1-line close. "
            "Hard constraints: no repeated sentences/phrases; no duplicated paragraphs; keep it ~6-10 lines total. "
            "For intro questions (e.g., 'Tell me about yourself', 'Who are you?', 'Walk me through your background'), use: "
            "Headline (role + focus) → Education (1 line) → Experience highlights (2-3 bullets) → Current focus + why it fits (1 line)."
        )
        
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
        
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
                "content": str(msg.get("content", "")),
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
