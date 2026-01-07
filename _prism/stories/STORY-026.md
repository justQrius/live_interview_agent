# Story 026: Groq STT Provider

## Description
Implement Groq as a Speech-to-Text (STT) provider using the `STTProvider` interface. This leverages Groq's ultra-fast inference for the Whisper-large-v3 model to minimize transcription latency.

## Rationale
Low latency is the most critical NFR for a real-time interview assistant. Groq provides Whisper-large-v3 inference at speeds significantly faster (~300ms) than standard implementations, directly improving the "Real-Time" aspect of the application.

## Requirements
1.  **Groq Integration**: Add `groq` to `sidecar/requirements.txt` (if not present).
2.  **Provider Implementation**: Create `sidecar/src/providers/stt/groq.py`.
3.  **Class Structure**: Implement `GroqSTTProvider` class inheriting from `STTProvider`.
4.  **Method**: Implement `transcribe(audio_data: bytes, language: str = "en") -> TranscriptionResult`.
    - Convert raw audio bytes to format accepted by Groq (file-like object).
    - Use model `whisper-large-v3`.
    - Map response to `TranscriptionResult`.
5.  **Configuration**: Use `ProviderConfig` to retrieve `groq_api_key`.

## Architecture
Reference: `_prism/architecture/architecture-phase2.md`

### Class Structure
```python
from sidecar.src.providers.base import STTProvider, TranscriptionResult
from groq import Groq

class GroqSTTProvider(STTProvider):
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        
    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        # Implementation details...
        pass
```

## Acceptance Criteria
- [ ] `sidecar/src/providers/stt/groq.py` created.
- [ ] `GroqSTTProvider` correctly implements `STTProvider` interface.
- [ ] Unit tests (`sidecar/tests/test_groq_stt_provider.py`) pass with mocked API responses.
- [ ] Integration works with `ProviderFactory` (verified via tests or manual check).
- [ ] Error handling for invalid keys or API failures is implemented.

## Tasks
1. [ ] Add `groq` to requirements.
2. [ ] Create `sidecar/src/providers/stt/groq.py`.
3. [ ] Implement `GroqSTTProvider`.
4. [ ] Export provider in `sidecar/src/providers/stt/__init__.py`.
5. [ ] Write unit tests.
