# Audio processing module
"""
Contains audio capture, VAD, and speaker diarization components.
"""

from src.audio.capture import (
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

from src.audio.vad import (
    # Constants
    DEFAULT_VAD_THRESHOLD,
    DEFAULT_VAD_WINDOW_SIZE,
    # Classes
    VADProcessor,
    VADModelError,
    SpeechSegment,
)

from src.audio.noise_reduction import (
    # Constants
    DEFAULT_PROP_DECREASE,
    # Classes
    NoiseReducer,
    NoiseReducerError,
)

__all__ = [
    # Audio Capture Constants
    "SAMPLE_RATE",
    "CHANNELS",
    "SAMPLE_DTYPE",
    "CHUNK_DURATION_MS",
    "CHUNK_SAMPLES",
    "BUFFER_DURATION_SEC",
    "BUFFER_SAMPLES",
    # Audio Capture Classes
    "AudioCapture",
    "AudioCaptureError",
    "CircularBuffer",
    # Audio Capture Functions
    "get_platform_backend",
    "samples_to_bytes",
    "bytes_to_samples",
    # VAD Constants
    "DEFAULT_VAD_THRESHOLD",
    "DEFAULT_VAD_WINDOW_SIZE",
    # VAD Classes
    "VADProcessor",
    "VADModelError",
    "SpeechSegment",
    # Noise Reduction Constants
    "DEFAULT_PROP_DECREASE",
    # Noise Reduction Classes
    "NoiseReducer",
    "NoiseReducerError",
]
