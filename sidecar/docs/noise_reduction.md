# Noise Reduction Feature

## Overview

The noise reduction feature uses the `noisereduce` library to improve Speech-to-Text (STT) accuracy in noisy environments by removing background noise while preserving speech.

## Architecture

### Pipeline Integration

The noise reduction is integrated into the audio pipeline at this position:

```
Audio Capture → VAD → **Noise Reducer** → STT → Diarization → RAG → LLM → UI
```

**Why after VAD?**
- Silero VAD is trained on noisy audio and performs well with background noise
- Noise reduction before VAD might remove voice characteristics that VAD needs
- STT benefits most from clean audio
- This allows VAD to detect speech in noisy conditions, then clean it for better transcription

### Performance

- **Latency**: <100ms for 500ms audio chunks (tested)
- **Memory**: Minimal overhead, no accumulation across calls
- **CPU**: Moderate during processing, negligible when disabled

## Configuration

### Default Settings

```python
from audio.noise_reduction import NoiseReducer

# Default configuration (enabled, stationary mode, moderate aggressiveness)
reducer = NoiseReducer()
```

Defaults:
- `enabled=True` - Noise reduction is active
- `stationary=True` - Optimized for consistent background noise (air conditioning, fans)
- `prop_decrease=1.0` - Moderate noise reduction strength

### Disabling Noise Reduction

```python
# Completely disabled (pass-through mode, zero latency)
reducer = NoiseReducer(enabled=False)
```

### Adjusting Aggressiveness

```python
# Gentle mode (preserves more voice characteristics)
reducer = NoiseReducer(prop_decrease=0.5)

# Aggressive mode (for very noisy environments)
reducer = NoiseReducer(prop_decrease=1.5)
```

Parameter range: `0.0` (no reduction) to `1.5` (maximum reduction)

### Non-Stationary Noise

```python
# For changing/intermittent background noise
reducer = NoiseReducer(stationary=False)
```

Use when:
- Background noise changes over time
- Multiple noise sources
- Intermittent sounds (typing, doors, etc.)

## Server Integration

The noise reduction is automatically initialized in `server.py`:

```python
# In _start_audio_processing()
self.noise_reducer = NoiseReducer(enabled=True)

# In _process_speech_segment()
audio_for_stt = segment.audio
if self.noise_reducer and self.noise_reducer.enabled:
    clean_audio = self.noise_reducer.reduce_noise(segment.audio)
    if isinstance(clean_audio, bytes):
        audio_for_stt = clean_audio
```

### Runtime Control

To control noise reduction at runtime, modify the server initialization:

```python
# Option 1: Environment variable (recommended)
import os
noise_reduction_enabled = os.getenv("ENABLE_NOISE_REDUCTION", "true").lower() == "true"
self.noise_reducer = NoiseReducer(enabled=noise_reduction_enabled)

# Option 2: WebSocket message (future enhancement)
# Add support for runtime toggle via WebSocket protocol
```

## Testing

### Unit Tests

```bash
cd sidecar
python -m pytest tests/test_noise_reduction.py -v
```

Tests cover:
- Initialization and configuration
- Processing with various audio types
- Latency requirements
- Edge cases (empty, short, clipped audio)
- Thread safety

### Integration Tests

```bash
cd sidecar
python -m pytest tests/test_noise_reduction_integration.py -v
```

Tests cover:
- VAD pipeline integration
- Server pipeline integration
- Latency in realistic scenarios
- Memory usage

## Troubleshooting

### Issue: Noise reduction not working

**Check:**
1. Is `noisereduce>=3.0.0` installed? Run: `pip install noisereduce`
2. Is it enabled? Check `reducer.enabled`
3. Check logs for warnings/errors

### Issue: Latency increased significantly

**Solutions:**
1. Disable noise reduction: `NoiseReducer(enabled=False)`
2. Reduce aggressiveness: `NoiseReducer(prop_decrease=0.5)`
3. Check system resources (CPU usage)

### Issue: Voice quality degraded

**Solutions:**
1. Use gentler settings: `NoiseReducer(prop_decrease=0.5)`
2. Try non-stationary mode: `NoiseReducer(stationary=False)`
3. Disable if voice clarity is critical: `NoiseReducer(enabled=False)`

## When to Use

### Enable Noise Reduction When:
- User is in a noisy environment (coffee shop, office, etc.)
- Background noise is consistent (AC, fans, traffic)
- STT accuracy is poor due to noise
- Meeting <5sec end-to-end latency target

### Disable Noise Reduction When:
- User is in a quiet environment
- Voice clarity is already good
- Need absolute minimum latency
- User reports voice distortion

## Performance Benchmarks

Based on test results:

| Audio Length | Processing Time | Overhead |
|--------------|----------------|----------|
| 500ms chunk  | <100ms         | <20% of chunk duration |
| 1 second     | <200ms         | <20% of audio duration |

**Latency Budget:**
- Target: <5 seconds end-to-end
- Noise reduction: <100ms (2% of budget)
- Remaining: 4.9s for STT, RAG, LLM

## Implementation Details

### Algorithm

The `noisereduce` library uses:
- **Spectral Gating**: Identifies noise spectrum and reduces it
- **Stationary Mode**: Assumes consistent noise profile
- **Non-Stationary Mode**: Adapts to changing noise

### Audio Format Handling

- Input: `bytes` (int16 PCM) or `np.ndarray` (int16)
- Processing: Converted to float32 [-1, 1] range
- Output: Same format as input (int16)

### Thread Safety

The `reduce_noise()` method is stateless and thread-safe:
- No internal state accumulation
- Safe to call concurrently from multiple threads
- Safe in async/await context

## Future Enhancements

1. **Runtime Toggle**: Add WebSocket message to enable/disable at runtime
2. **Auto-Adjustment**: Detect noise level and adjust aggressiveness automatically
3. **Metrics**: Report noise reduction effectiveness (SNR improvement)
4. **Profile Selection**: Predefined profiles (quiet, moderate, loud)
5. **UI Control**: Allow user to toggle via UI checkbox
