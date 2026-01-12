"""
Noise Reduction module using noisereduce library.

Provides optional noise reduction preprocessing for audio before STT.
Uses spectral gating to reduce stationary and non-stationary background noise.

Audio Format:
- Sample rate: 16kHz (configurable)
- Channels: mono (1 channel)
- Format: 16-bit PCM (int16)
"""

import logging
from typing import Union

import numpy as np

# Import SAMPLE_RATE from capture module (single source of truth)
from src.audio.capture import SAMPLE_RATE

# Configure logging
logger = logging.getLogger(__name__)

# Noise reduction configuration constants
DEFAULT_PROP_DECREASE: float = 1.0  # Moderate aggressiveness (0.0-1.5 range)


class NoiseReducerError(Exception):
    """Exception raised when noise reducer fails to initialize or process audio."""
    pass


class NoiseReducer:
    """
    Noise reduction processor using noisereduce library.

    Reduces background noise from audio while preserving speech.
    Can be disabled for pass-through mode with zero latency.

    Usage:
        reducer = NoiseReducer()
        clean_audio = reducer.reduce_noise(noisy_audio)

        # Disabled mode (pass-through)
        reducer = NoiseReducer(enabled=False)
        audio = reducer.reduce_noise(audio)  # Returns unchanged
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        enabled: bool = True,
        stationary: bool = True,
        prop_decrease: float = DEFAULT_PROP_DECREASE,
    ):
        """
        Initialize noise reducer.

        Args:
            sample_rate: Audio sample rate in Hz. Default: 16000
            enabled: Enable noise reduction. If False, acts as pass-through. Default: True
            stationary: Use stationary noise reduction (True) or non-stationary (False).
                       Default: True (better for consistent background noise)
            prop_decrease: Noise reduction aggressiveness (0.0-1.5).
                          Lower = less aggressive, Higher = more aggressive.
                          Default: 1.0 (moderate)
        """
        self._sample_rate = sample_rate
        self._enabled = enabled
        self._stationary = stationary
        self._prop_decrease = prop_decrease

        # Lazy import noisereduce (only if enabled)
        self._nr = None
        if self._enabled:
            try:
                import noisereduce as nr
                self._nr = nr
                logger.info(
                    f"NoiseReducer initialized: "
                    f"enabled={enabled}, stationary={stationary}, "
                    f"prop_decrease={prop_decrease}"
                )
            except ImportError:
                logger.error(
                    "noisereduce library not installed. "
                    "Install with: pip install noisereduce"
                )
                # Disable if library not available
                self._enabled = False
        else:
            logger.info("NoiseReducer initialized in disabled mode (pass-through)")

    @property
    def sample_rate(self) -> int:
        """Return the configured sample rate."""
        return self._sample_rate

    @property
    def enabled(self) -> bool:
        """Return whether noise reduction is enabled."""
        return self._enabled

    @property
    def stationary(self) -> bool:
        """Return whether stationary mode is used."""
        return self._stationary

    @property
    def prop_decrease(self) -> float:
        """Return the noise reduction aggressiveness."""
        return self._prop_decrease

    def reduce_noise(
        self,
        audio: Union[np.ndarray, bytes]
    ) -> Union[np.ndarray, bytes]:
        """
        Apply noise reduction to audio.

        Args:
            audio: Audio data as numpy array (int16) or bytes (int16 PCM)

        Returns:
            Noise-reduced audio in same format as input
        """
        # Handle input format
        input_is_bytes = isinstance(audio, bytes)
        
        if input_is_bytes:
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio, dtype=np.int16)
        else:
            audio_np = audio

        # Pass-through mode if disabled
        if not self._enabled:
            return audio if input_is_bytes else audio_np.copy()

        # Handle empty or very short audio
        if len(audio_np) == 0:
            return b"" if input_is_bytes else np.array([], dtype=np.int16)

        # Convert int16 to float32 for processing
        # noisereduce expects float values in range [-1, 1]
        audio_float = audio_np.astype(np.float32) / 32768.0

        try:
            # Apply noise reduction
            reduced_float = self._nr.reduce_noise(
                y=audio_float,
                sr=self._sample_rate,
                stationary=self._stationary,
                prop_decrease=self._prop_decrease,
            )

            # Convert back to int16
            # Clip to prevent overflow
            reduced_float = np.clip(reduced_float, -1.0, 1.0)
            reduced_int16 = (reduced_float * 32767).astype(np.int16)

        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}. Returning original audio.")
            # Return original audio on error
            reduced_int16 = audio_np

        # Return in same format as input
        if input_is_bytes:
            return reduced_int16.tobytes()
        else:
            return reduced_int16
