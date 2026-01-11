# STORY-065: Interim Transcript Streaming

**Phase**: 4D - Continuous-Feel Transcription
**Priority**: Medium
**Effort**: 1 day
**Dependencies**: None

---

## User Story

As a user, I want to see what the interviewer is saying in real-time, so that the system doesn't feel frozen during speech.

---

## Acceptance Criteria

### AC-1: Interim Display
- [ ] Partial transcript shown in UI during speech
- [ ] Interim text styled differently (e.g., italics, lighter color)
- [ ] Updates every ~500ms during active speech

### AC-2: WebSocket Messages
- [ ] New message type: `INTERIM_TRANSCRIPT`
- [ ] Message includes: text, speaker, is_final flag
- [ ] Final transcript replaces interim when segment complete

### AC-3: Provider Support
- [ ] Works with streaming STT providers (Deepgram, Groq streaming)
- [ ] Graceful fallback for non-streaming providers
- [ ] No errors for unsupported providers

### AC-4: UI Rendering
- [ ] Smooth transition from interim to final
- [ ] No flickering or jumps
- [ ] Listening indicator visible during speech

---

## Technical Notes

```python
# File: sidecar/src/audio/streaming.py

class StreamingTranscriber:
    async def transcribe_with_interim(
        self,
        audio_stream: AsyncIterator[bytes],
        callback: Callable[[TranscriptUpdate], Awaitable[None]]
    ):
        """Transcribe with interim result callbacks"""
        
        if self.provider.supports_streaming:
            async for interim in self._stream_transcribe(audio_stream):
                await callback(TranscriptUpdate(
                    text=interim.text,
                    is_final=interim.is_final,
                    confidence=interim.confidence,
                    speaker=Speaker.INTERVIEWER  # Default until diarized
                ))
        else:
            # Fallback: buffer and transcribe on VAD end
            buffer = []
            async for chunk in audio_stream:
                buffer.append(chunk)
                if self.vad.is_segment_end():
                    result = await self.provider.transcribe(b''.join(buffer))
                    await callback(TranscriptUpdate(
                        text=result.text,
                        is_final=True,
                        confidence=result.confidence
                    ))
                    buffer = []
```

```typescript
// UI: src/ui/store/sessionStore.ts

interface SessionState {
  // ... existing
  interimTranscript: string | null;
}

// Handle INTERIM_TRANSCRIPT message
case 'INTERIM_TRANSCRIPT':
  set({ interimTranscript: message.data.text });
  break;

case 'TRANSCRIPTION':
  // Final transcript replaces interim
  set({ interimTranscript: null });
  // ... existing logic
  break;
```

---

## Test Cases

1. **test_interim_sent**: Interim messages sent during speech
2. **test_final_replaces_interim**: Final clears interim
3. **test_non_streaming_fallback**: Works without streaming provider
4. **test_ui_updates**: UI shows interim correctly
5. **test_no_flicker**: Smooth visual transitions

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Works with at least one streaming provider
- [ ] Fallback tested with non-streaming provider
- [ ] UI renders smoothly
- [ ] Code reviewed
