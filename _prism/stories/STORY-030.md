# Story 030: Anthropic LLM Provider

## Description
Implement Anthropic as an LLM provider using the `LLMProvider` interface. This enables using Claude 3.5 Sonnet for answer generation, offering another high-quality alternative for reasoning and coding tasks.

## Rationale
Claude 3.5 Sonnet is highly regarded for its reasoning capabilities and concise, natural-sounding responses. Adding it as a provider gives users access to one of the best models available, increasing the tool's versatility.

## Requirements
1.  **Anthropic Integration**: Add `anthropic` to `sidecar/requirements.txt`.
2.  **Provider Implementation**: Create `sidecar/src/providers/llm/anthropic.py`.
3.  **Class Structure**: Implement `AnthropicLLMProvider` class inheriting from `LLMProvider`.
4.  **Method**: Implement `generate_response(prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]`.
    - Construct messages: System prompt + History + Context/User prompt.
    - Use model `claude-3-5-sonnet-20240620` (or latest stable alias).
    - Enable streaming (`stream=True`).
    - Yield chunks as they arrive (`chunk.delta.text`).
5.  **Configuration**: Use `ProviderConfig` to retrieve `anthropic_api_key`.

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Class Structure
```python
from typing import List, Dict, AsyncGenerator
from sidecar.src.providers.base import LLMProvider
from anthropic import AsyncAnthropic

class AnthropicLLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20240620"
        
    async def generate_response(self, prompt: str, context: str, history: List[Dict]) -> AsyncGenerator[str, None]:
        # Implementation details...
        pass
```

## Acceptance Criteria
- [ ] `sidecar/src/providers/llm/anthropic.py` created.
- [ ] `AnthropicLLMProvider` correctly implements `LLMProvider` interface.
- [ ] Streaming works correctly (yields chunks).
- [ ] Unit tests (`sidecar/tests/test_anthropic_llm_provider.py`) pass with mocked API responses.
- [ ] Integration works with `ProviderFactory`.

## Tasks
1. [ ] Add `anthropic` to requirements.
2. [ ] Create `sidecar/src/providers/llm/anthropic.py`.
3. [ ] Implement `AnthropicLLMProvider`.
4. [ ] Export provider in `sidecar/src/providers/llm/__init__.py`.
5. [ ] Write unit tests.
