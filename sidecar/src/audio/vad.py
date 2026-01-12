"""
Voice Activity Detection (VAD) module using Silero VAD v4.

Processes audio chunks to detect speech segments and filter silence.
Uses a sliding window of 512 samples (32ms at 16kHz) with 0.5 threshold.

Audio Format:
- Sample rate: 16kHz
- Channels: mono (1 channel)
- Format: 16-bit PCM (int16)
"""

import logging
import threading
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import torch

# Import SAMPLE_RATE from capture module (single source of truth)
from src.audio.capture import SAMPLE_RATE

# Configure logging
logger = logging.getLogger(__name__)

# VAD configuration constants
DEFAULT_VAD_THRESHOLD: float = 0.5
DEFAULT_VAD_WINDOW_SIZE: int = 512  # 512 samples = 32ms at 16kHz

SUPPORTED_SAMPLE_RATES = (8000, 16000)


def _expected_window_size(sample_rate: int) -> int:
    if sample_rate == 16000:
        return 512
    if sample_rate == 8000:
        return 256

    raise ValueError(
        f"Unsupported sample rate {sample_rate} (supported values: {SUPPORTED_SAMPLE_RATES})"
    )


# Smoothing configuration - require consecutive frames for speech start/end
# These represent number of consecutive windows (32ms each at 16kHz/8kHz defaults).
SPEECH_START_FRAMES: int = 5   # Approx 160ms to confirm speech start
SPEECH_END_FRAMES: int = 25    # Approx 800ms silence to confirm speech end


class VADModelError(Exception):
    """Exception raised when VAD model fails to load or process audio."""
    pass


@dataclass
class SpeechSegment:
    """
    Represents a detected speech segment.

    Attributes:
        audio: Raw audio bytes for this segment (int16 PCM)
        start_time: Start time in seconds relative to chunk start
        end_time: End time in seconds relative to chunk start
        confidence: Average speech probability for this segment (0.0 to 1.0)
    """
    audio: bytes
    start_time: float
    end_time: float
    confidence: float


class VADProcessor:
    """
    Voice Activity Detection processor using Silero VAD v4.

    Processes audio chunks and returns speech segments, filtering silence.
    Uses a sliding window approach with smoothing to prevent jitter.

    Usage:
        processor = VADProcessor()
        segments = await processor.process_chunk(audio_bytes)
        for segment in segments:
            process_speech(segment.audio)
    """

    def __init__(
        self,
        threshold: float = DEFAULT_VAD_THRESHOLD,
        window_size: int = DEFAULT_VAD_WINDOW_SIZE,
        sample_rate: int = SAMPLE_RATE,
    ):
        """
        Initialize VAD processor.

        Args:
            threshold: Speech probability threshold (0.0 to 1.0). Default: 0.5
            window_size: Number of samples per VAD window. Default: 512 (32ms at 16kHz)

        Raises:
            ValueError: If threshold is not between 0 and 1
            VADModelError: If Silero VAD model fails to load
        """
        # Validate threshold
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError(f"threshold must be between 0 and 1, got {threshold}")

        expected_window_size = _expected_window_size(sample_rate)
        if window_size != expected_window_size:
            raise ValueError(
                f"Provided number of samples is {window_size} "
                f"(Supported values: {expected_window_size} for {sample_rate} sample rate)"
            )

        self._threshold = threshold
        self._window_size = window_size
        self._sample_rate = sample_rate

        # State for smoothing
        self._consecutive_speech_frames = 0
        self._consecutive_silence_frames = 0
        self._is_speaking = False
        self._current_segment_samples: List[np.ndarray] = []
        self._current_segment_start_time: float = 0.0
        self._current_segment_probs: List[float] = []

        # Thread safety
        self._lock = threading.Lock()

        # Load the model
        self._model: Optional[torch.jit.ScriptModule] = None
        self._load_model()

    @property
    def threshold(self) -> float:
        """Return the speech probability threshold."""
        return self._threshold

    @property
    def window_size(self) -> int:
        """Return the VAD window size in samples."""
        return self._window_size

    @property
    def sample_rate(self) -> int:
        """Return the configured sample rate."""
        return self._sample_rate

    @property
    def is_speaking(self) -> bool:
        """Return True if currently detecting speech."""
        return self._is_speaking

    @property
    def current_duration(self) -> float:
        """Return duration of current ongoing speech in seconds."""
        with self._lock:
            if not self._is_speaking or not self._current_segment_samples:
                return 0.0
            # Sum length of all arrays in list
            total_samples = sum(len(s) for s in self._current_segment_samples)
            return total_samples / self._sample_rate

    def get_current_audio(self) -> Optional[bytes]:
        """
        Get currently accumulated audio for active speech.
        
        Returns:
            Raw audio bytes of the current ongoing segment, or None if not speaking.
        """
        with self._lock:
            if not self._is_speaking or not self._current_segment_samples:
                return None
            return np.concatenate(self._current_segment_samples).tobytes()

    def _load_model(self) -> None:
        """
        Load the Silero VAD v4 model.

        Raises:
            VADModelError: If model fails to load
        """
        try:
            # Import silero_vad package
            from silero_vad import load_silero_vad

            self._model = load_silero_vad()
            logger.info("Silero VAD model loaded successfully")
        except ImportError as e:
            raise VADModelError(
                f"silero_vad package not installed. Install with: pip install silero-vad. Error: {e}"
            )
        except Exception as e:
            raise VADModelError(f"Failed to load Silero VAD model: {e}")

    def reset(self) -> None:
        """
        Reset VAD processor state for a new session.

        Clears internal state and resets the model's hidden states.
        Call this between audio sessions.
        """
        with self._lock:
            self._consecutive_speech_frames = 0
            self._consecutive_silence_frames = 0
            self._is_speaking = False
            self._current_segment_samples = []
            self._current_segment_start_time = 0.0
            self._current_segment_probs = []

            if self._model is not None:
                self._model.reset_states()
                logger.debug("VAD processor state reset")

    async def process_chunk(self, audio_bytes: bytes) -> List[SpeechSegment]:
        """
        Process an audio chunk and return detected speech segments.

        Args:
            audio_bytes: Raw audio data (16kHz, mono, int16 PCM)

        Returns:
            List of SpeechSegment objects containing detected speech
        """
        if not audio_bytes:
            return []

        # Convert bytes to numpy array
        try:
            samples = np.frombuffer(audio_bytes, dtype=np.int16)
        except ValueError as e:
            logger.warning(f"Invalid audio bytes: {e}")
            return []

        if len(samples) < self._window_size:
            logger.debug(f"Audio chunk too short ({len(samples)} samples), skipping")
            return []

        # Convert to float32 tensor for Silero VAD
        # Silero VAD expects values in range [-1, 1]
        audio_float = samples.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float)

        segments: List[SpeechSegment] = []

        with self._lock:
            # Process audio in windows
            num_windows = len(audio_tensor) // self._window_size
            chunk_start_time = 0.0

            for i in range(num_windows):
                start_idx = i * self._window_size
                end_idx = start_idx + self._window_size
                window = audio_tensor[start_idx:end_idx]

                # Get speech probability from model
                try:
                    speech_prob = self._model(window, self._sample_rate).item()
                except Exception as e:
                    logger.error(f"VAD model inference error: {e}")
                    continue

                # Calculate window time
                window_start_time = start_idx / self._sample_rate
                window_end_time = end_idx / self._sample_rate

                # Get original samples for this window
                window_samples = samples[start_idx:end_idx]

                # Apply smoothing logic
                is_speech = speech_prob >= self._threshold

                if is_speech:
                    self._consecutive_speech_frames += 1
                    self._consecutive_silence_frames = 0
                else:
                    self._consecutive_silence_frames += 1
                    self._consecutive_speech_frames = 0

                # State machine for speech detection
                if not self._is_speaking:
                    # Not speaking - check if we should start
                    if self._consecutive_speech_frames >= SPEECH_START_FRAMES:
                        self._is_speaking = True
                        self._current_segment_start_time = window_start_time - (
                            (SPEECH_START_FRAMES - 1) * self._window_size / self._sample_rate
                        )
                        # Include the previous frames that triggered the start
                        # Already added to current_segment_samples below
                        logger.debug(f"Speech started at {self._current_segment_start_time:.3f}s")

                    # Collect samples even before speech is confirmed (for smoothing)
                    if self._consecutive_speech_frames > 0:
                        self._current_segment_samples.append(window_samples)
                        self._current_segment_probs.append(speech_prob)
                    else:
                        # Reset if we hit silence before reaching threshold
                        self._current_segment_samples = []
                        self._current_segment_probs = []
                else:
                    # Currently speaking - collect samples
                    self._current_segment_samples.append(window_samples)
                    self._current_segment_probs.append(speech_prob)

                    # Check if we should stop
                    if self._consecutive_silence_frames >= SPEECH_END_FRAMES:
                        # End of speech - create segment
                        segment = self._finalize_segment(window_end_time)
                        if segment is not None:
                            segments.append(segment)

                        self._is_speaking = False
                        self._current_segment_samples = []
                        self._current_segment_probs = []
                        logger.debug(f"Speech ended at {window_end_time:.3f}s")

        return segments

    def _finalize_segment(self, end_time: float) -> Optional[SpeechSegment]:
        """
        Create a SpeechSegment from accumulated samples.

        Args:
            end_time: End time of the segment in seconds

        Returns:
            SpeechSegment or None if no valid segment
        """
        if not self._current_segment_samples:
            return None

        # Concatenate all samples
        all_samples = np.concatenate(self._current_segment_samples)

        # Calculate confidence as mean of probabilities
        if self._current_segment_probs:
            confidence = sum(self._current_segment_probs) / len(self._current_segment_probs)
        else:
            confidence = 0.0

        # Adjust end time to exclude trailing silence frames
        adjusted_end_time = end_time - (
            (SPEECH_END_FRAMES - 1) * self._window_size / self._sample_rate
        )

        return SpeechSegment(
            audio=all_samples.tobytes(),
            start_time=max(0.0, self._current_segment_start_time),
            end_time=adjusted_end_time,
            confidence=min(1.0, max(0.0, confidence)),
        )
