# Story 027: Deepgram STT Provider

## Description
Implement Deepgram as a Speech-to-Text (STT) provider using the `STTProvider` interface. This enables using Deepgram's Nova-2 model, known for its high accuracy and speed.

## Rationale
Deepgram is a leading STT provider with excellent accuracy/speed trade-offs. Adding it as a secondary (or primary) option increases system resilience through redundancy and gives users choice based on their API keys.

## Requirements
1.  **Deepgram Integration**: Add `deepgram-sdk` to `sidecar/requirements.txt`.
2.  **Provider Implementation**: Create `sidecar/src/providers/stt/deepgram.py`.
3.  **Class Structure**: Implement `DeepgramSTTProvider` class inheriting from `STTProvider`.
4.  **Method**: Implement `transcribe(audio_data: bytes, language: str = "en") -> TranscriptionResult`.
    - Use `deepgram-sdk` (AsyncPrerecordedClient).
    - Use model `nova-2`.
    - Use `smart_format=True`.
    - Map response to `TranscriptionResult`.
5.  **Configuration**: Use `ProviderConfig` to retrieve `deepgram_api_key`.

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Class Structure
```python
from sidecar.src.providers.base import STTProvider, TranscriptionResult
from deepgram import DeepgramClient, PrerecordedOptions

class DeepgramSTTProvider(STTProvider):
    def __init__(self, api_key: str):
        self.client = DeepgramClient(api_key)
        
    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        # Implementation details...
        pass
```

## Acceptance Criteria
- [ ] `sidecar/src/providers/stt/deepgram.py` created.
- [ ] `DeepgramSTTProvider` correctly implements `STTProvider` interface.
- [ ] Unit tests (`sidecar/tests/test_deepgram_stt_provider.py`) pass with mocked API responses.
- [ ] Integration works with `ProviderFactory`.

## Tasks
1. [ ] Add `deepgram-sdk` to requirements.
2. [ ] Create `sidecar/src/providers/stt/deepgram.py`.
3. [ ] Implement `DeepgramSTTProvider`.
4. [ ] Export provider in `sidecar/src/providers/stt/__init__.py`.
5. [ ] Write unit tests.
