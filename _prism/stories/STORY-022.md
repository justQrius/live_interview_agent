# Story 022: Provider Base Interfaces

## Description
Create abstract base classes (ABCs) for STT, LLM, and Embedding providers to support the new multi-provider strategy. This establishes a common interface for all AI services, allowing interchangeable backends (Gemini, OpenAI, Groq, etc.).

## Rationale
To support multiple providers and fallback strategies (Phase 2), we need a unified interface that abstracts away the specific implementation details of each API. This allows the core application logic to remain agnostic to the underlying provider.

## Requirements
1.  **Base Module**: Create `sidecar/src/providers/base.py`.
2.  **STT Interface**: Define `STTProvider` abstract base class.
    -   `transcribe(audio_data: bytes) -> TranscriptionResult`
3.  **LLM Interface**: Define `LLMProvider` abstract base class.
    -   `generate_response(prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]`
4.  **Embedding Interface**: Define `EmbeddingProvider` abstract base class.
    -   `embed_text(text: str) -> List[float]`
    -   `batch_embed_text(texts: List[str]) -> List[List[float]]`
5.  **Type Definitions**: Define common data classes (e.g., `Message`, `TranscriptionResult`).

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Class Structure
```python
from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator, Union, Optional
from dataclasses import dataclass

@dataclass
class TranscriptionResult:
    text: str
    confidence: float = 0.0
    speaker: Optional[str] = None
    language: str = "en"

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult: ...

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]: ...

class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]: ...
    
    @abstractmethod
    async def batch_embed_text(self, texts: List[str]) -> List[List[float]]: ...
```

## Acceptance Criteria
- [x] `sidecar/src/providers/base.py` created.
- [x] `STTProvider` ABC defined with required methods.
- [x] `LLMProvider` ABC defined with required methods.
- [x] `EmbeddingProvider` ABC defined with required methods.
- [x] Unit tests (`sidecar/tests/test_providers_base.py`) verify abstract methods and inheritance enforcement.

## Tasks
1. [x] Create `sidecar/src/providers/` directory and `__init__.py`.
2. [x] Create `sidecar/src/providers/base.py`.
3. [x] Define data classes (`TranscriptionResult`, etc.).
4. [x] Implement ABCs.
5. [x] Write tests to ensure subclasses must implement methods.
