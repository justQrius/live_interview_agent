import os
import logging
from typing import List, AsyncGenerator
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

class GeminiLLMError(Exception):
    """Base exception for Gemini LLM errors."""
    pass

class GeminiLLM:
    """
    LLM wrapper for Google's Gemini model.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the Gemini LLM.

        Args:
            api_key: Google API key.
            model_name: Model to use (default: gemini-1.5-flash).
        """
        if not api_key:
            raise ValueError("API key is required")

        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            raise GeminiLLMError(f"Initialization failed: {e}") from e

    async def generate_answer(
        self, 
        question: str, 
        context_chunks: List[str]
    ) -> AsyncGenerator[str, None]:
        """
        Generate an answer for the given question and context.

        Args:
            question: The user's question.
            context_chunks: List of context strings.

        Yields:
            Chunks of the generated answer.
        """
        context_str = "\n\n".join(context_chunks)
        
        prompt = f"""You are an expert technical interview assistant. Your goal is to help the candidate answer the interviewer's question using the provided context.

Context:
{context_str}

Question:
{question}

Answer the question clearly and concisely based on the context provided. If the context is not relevant, answer based on your general knowledge but mention that the context didn't help. Keep the answer conversational but professional."""

        try:
            # Set safety settings to be less restrictive for technical content if needed,
            # but default is usually fine.
            # Using stream=True for streaming response
            response = await self.model.generate_content_async(
                prompt,
                stream=True
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise GeminiLLMError(f"Generation failed: {e}") from e
