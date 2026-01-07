# Story 029: OpenAI LLM Provider

## Description
Implement OpenAI as an LLM provider using the `LLMProvider` interface. This allows using GPT-4o for answer generation, offering a high-quality alternative to Gemini.

## Rationale
OpenAI's GPT-4o is currently one of the most capable models for reasoning and instruction following. Adding it as a provider (potentially the default preferred one) significantly improves the quality of interview answers.

## Requirements
1.  **OpenAI Integration**: Add `openai` to `sidecar/requirements.txt` (if not present).
2.  **Provider Implementation**: Create `sidecar/src/providers/llm/openai.py`.
3.  **Class Structure**: Implement `OpenAILLMProvider` class inheriting from `LLMProvider`.
4.  **Method**: Implement `generate_response(prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]`.
    - Construct messages: System prompt + History + Context/User prompt.
    - Use model `gpt-4o`.
    - Enable streaming (`stream=True`).
    - Yield chunks as they arrive.
5.  **Configuration**: Use `ProviderConfig` to retrieve `openai_api_key`.

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Class Structure
```python
from typing import List, Dict, AsyncGenerator
from sidecar.src.providers.base import LLMProvider
from openai import AsyncOpenAI

class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"
        
    async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
        # Implementation details...
        pass
```

## Acceptance Criteria
- [ ] `sidecar/src/providers/llm/openai.py` created.
- [ ] `OpenAILLMProvider` correctly implements `LLMProvider` interface.
- [ ] Streaming works correctly (yields chunks).
- [ ] Unit tests (`sidecar/tests/test_openai_llm_provider.py`) pass with mocked API responses.
- [ ] Integration works with `ProviderFactory`.

## Tasks
1. [ ] Add `openai` to requirements.
2. [ ] Create `sidecar/src/providers/llm/openai.py`.
3. [ ] Implement `OpenAILLMProvider`.
4. [ ] Export provider in `sidecar/src/providers/llm/__init__.py`.
5. [ ] Write unit tests.
