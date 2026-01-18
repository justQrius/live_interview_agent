import sys
from pathlib import Path
import pytest
import asyncio
from typing import List, Dict, AsyncGenerator

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.providers.base import (
    STTProvider, 
    LLMProvider, 
    TranscriptionResult
)

# --- STT Provider Tests ---

def test_stt_provider_cannot_instantiate_abc():
    """Test that STTProvider ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        STTProvider()

def test_stt_provider_enforces_interface():
    """Test that subclasses must implement transcribe."""
    class IncompleteSTT(STTProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteSTT()

@pytest.mark.asyncio
async def test_stt_provider_concrete_implementation():
    """Test a valid concrete implementation of STTProvider."""
    class MockSTT(STTProvider):
        async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
            return TranscriptionResult(text="test", confidence=1.0)

    provider = MockSTT()
    result = await provider.transcribe(b"audio")
    assert isinstance(result, TranscriptionResult)
    assert result.text == "test"
    assert result.confidence == 1.0

# --- LLM Provider Tests ---

def test_llm_provider_cannot_instantiate_abc():
    with pytest.raises(TypeError):
        LLMProvider()

def test_llm_provider_enforces_interface():
    class IncompleteLLM(LLMProvider):
        pass
    with pytest.raises(TypeError):
        IncompleteLLM()

@pytest.mark.asyncio
async def test_llm_provider_concrete_implementation():
    class MockLLM(LLMProvider):
        async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
            yield "hello"
            yield " world"

    provider = MockLLM()
    chunks = []
    async for chunk in provider.generate_response("prompt", "context", []):
        chunks.append(chunk)
    
    assert "".join(chunks) == "hello world"

# NOTE: EmbeddingProvider ABC was removed as unused.
# The actual embedding implementation inherits from ChromaDB's EmbeddingFunction.
# See rag/gemini_embeddings.py for the concrete implementation.
