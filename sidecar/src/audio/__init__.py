# Audio processing module
"""
Contains audio capture, VAD, and speaker diarization components.
"""

from audio.capture import (
    # Constants
    SAMPLE_RATE,
    CHANNELS,
    SAMPLE_DTYPE,
    CHUNK_DURATION_MS,
    CHUNK_SAMPLES,
    BUFFER_DURATION_SEC,
    BUFFER_SAMPLES,
    # Classes
    AudioCapture,
    AudioCaptureError,
    CircularBuffer,
    # Functions
    get_platform_backend,
    samples_to_bytes,
    bytes_to_samples,
)

__all__ = [
    # Constants
    "SAMPLE_RATE",
    "CHANNELS",
    "SAMPLE_DTYPE",
    "CHUNK_DURATION_MS",
    "CHUNK_SAMPLES",
    "BUFFER_DURATION_SEC",
    "BUFFER_SAMPLES",
    # Classes
    "AudioCapture",
    "AudioCaptureError",
    "CircularBuffer",
    # Functions
    "get_platform_backend",
    "samples_to_bytes",
    "bytes_to_samples",
]
