"""
Audio capture module for Live Interview Agent.

Provides platform-specific audio capture with loopback support:
- Windows: pyaudiowpatch (WASAPI loopback)
- macOS/Linux: sounddevice (Core Audio / PulseAudio)

Audio Format:
- Sample rate: 16kHz
- Channels: mono (1 channel)
- Format: 16-bit PCM (int16)
"""

import asyncio
import logging
import sys
import threading
from typing import AsyncIterator, Optional

import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

# Audio configuration constants
SAMPLE_RATE: int = 16000  # 16kHz
CHANNELS: int = 1  # Mono
SAMPLE_DTYPE = np.int16  # 16-bit PCM

# Chunk configuration (500ms)
CHUNK_DURATION_MS: int = 500
CHUNK_SAMPLES: int = (SAMPLE_RATE * CHUNK_DURATION_MS) // 1000  # 8000 samples

# Buffer configuration (5 seconds)
BUFFER_DURATION_SEC: int = 5
BUFFER_SAMPLES: int = SAMPLE_RATE * BUFFER_DURATION_SEC  # 80000 samples


class AudioCaptureError(Exception):
    """Exception raised for audio capture errors."""
    pass


def get_platform_backend() -> str:
    """
    Determine the appropriate audio backend for the current platform.

    Returns:
        str: 'pyaudiowpatch' for Windows, 'sounddevice' for other platforms
    """
    if sys.platform == "win32":
        return "pyaudiowpatch"
    else:
        return "sounddevice"


def samples_to_bytes(samples: np.ndarray) -> bytes:
    """
    Convert int16 numpy array to bytes.

    Args:
        samples: numpy array of int16 audio samples

    Returns:
        bytes: Raw audio data in little-endian format
    """
    return samples.astype(np.int16).tobytes()


def bytes_to_samples(data: bytes) -> np.ndarray:
    """
    Convert bytes to int16 numpy array.

    Args:
        data: Raw audio data in little-endian format

    Returns:
        numpy array of int16 audio samples
    """
    return np.frombuffer(data, dtype=np.int16)


class CircularBuffer:
    """
    Thread-safe circular buffer for audio samples.

    Stores int16 audio samples with automatic overwriting when full.
    """

    def __init__(self, capacity: int):
        """
        Initialize circular buffer.

        Args:
            capacity: Maximum number of samples to store
        """
        self._capacity = capacity
        self._buffer = np.zeros(capacity, dtype=np.int16)
        self._write_pos = 0
        self._read_pos = 0
        self._size = 0
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        """Return the buffer capacity."""
        return self._capacity

    @property
    def size(self) -> int:
        """Return the current number of samples in the buffer."""
        with self._lock:
            return self._size

    def write(self, samples: np.ndarray) -> None:
        """
        Write samples to the buffer.

        If buffer is full, oldest samples are overwritten.

        Args:
            samples: numpy array of int16 audio samples
        """
        with self._lock:
            samples = samples.astype(np.int16).flatten()
            num_samples = len(samples)

            if num_samples == 0:
                return

            if num_samples >= self._capacity:
                # Data larger than buffer - just keep the most recent samples
                self._buffer[:] = samples[-self._capacity:]
                self._write_pos = 0
                self._read_pos = 0
                self._size = self._capacity
                return

            # Calculate how many samples we can write before wrapping
            space_to_end = self._capacity - self._write_pos

            if num_samples <= space_to_end:
                # All samples fit without wrapping
                self._buffer[self._write_pos:self._write_pos + num_samples] = samples
            else:
                # Need to wrap around
                self._buffer[self._write_pos:] = samples[:space_to_end]
                self._buffer[:num_samples - space_to_end] = samples[space_to_end:]

            # Update write position
            self._write_pos = (self._write_pos + num_samples) % self._capacity

            # Update size and potentially move read position
            new_size = self._size + num_samples
            if new_size > self._capacity:
                # Calculate how much we're overwriting
                overflow = new_size - self._capacity
                self._read_pos = (self._read_pos + overflow) % self._capacity
                self._size = self._capacity
            else:
                self._size = new_size

    def read(self, count: int) -> np.ndarray:
        """
        Read samples from the buffer.

        Consumes the samples (they are removed from the buffer).

        Args:
            count: Maximum number of samples to read

        Returns:
            numpy array of int16 audio samples (may be less than requested)
        """
        with self._lock:
            if self._size == 0:
                return np.array([], dtype=np.int16)

            # Only read what's available
            actual_count = min(count, self._size)

            # Calculate how many samples to end of buffer
            space_to_end = self._capacity - self._read_pos

            if actual_count <= space_to_end:
                # All samples available without wrapping
                result = self._buffer[self._read_pos:self._read_pos + actual_count].copy()
            else:
                # Need to read from wrapped portion
                part1 = self._buffer[self._read_pos:].copy()
                part2 = self._buffer[:actual_count - space_to_end].copy()
                result = np.concatenate([part1, part2])

            # Update read position and size
            self._read_pos = (self._read_pos + actual_count) % self._capacity
            self._size -= actual_count

            return result

    def clear(self) -> None:
        """Clear all data from the buffer."""
        with self._lock:
            self._write_pos = 0
            self._read_pos = 0
            self._size = 0


class AudioCapture:
    """
    Platform-specific audio capture with loopback support.

    Captures system audio and provides it as an async stream of audio chunks.

    Usage:
        async with AudioCapture() as capture:
            async for chunk in capture.get_audio_stream():
                process(chunk)
    """

    def __init__(self):
        """Initialize audio capture."""
        self._buffer = CircularBuffer(capacity=BUFFER_SAMPLES)
        self._is_capturing = False
        self._capture_task: Optional[asyncio.Task] = None
        self._backend = get_platform_backend()
        self._stream = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_capturing(self) -> bool:
        """Return True if currently capturing audio."""
        return self._is_capturing

    async def __aenter__(self) -> "AudioCapture":
        """Async context manager entry - starts capture."""
        await self.start_capture()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - stops capture."""
        await self.stop_capture()

    async def start_capture(self) -> None:
        """
        Begin capturing audio to internal buffer.

        Raises:
            AudioCaptureError: If audio device cannot be accessed
        """
        if self._is_capturing:
            logger.debug("Capture already started, ignoring duplicate call")
            return

        try:
            await self._start_platform_capture()
            self._is_capturing = True
            logger.info(f"Audio capture started using {self._backend} backend")
        except PermissionError as e:
            self._is_capturing = False
            raise AudioCaptureError(f"Permission denied: {e}")
        except AudioCaptureError:
            self._is_capturing = False
            raise
        except Exception as e:
            self._is_capturing = False
            raise AudioCaptureError(f"Failed to start audio capture: {e}")

    async def stop_capture(self) -> None:
        """Stop capturing audio and clear buffer."""
        if not self._is_capturing:
            return

        try:
            await self._stop_platform_capture()
        except Exception as e:
            logger.warning(f"Error stopping platform capture: {e}")
        finally:
            self._is_capturing = False
            self._buffer.clear()
            logger.info("Audio capture stopped")

    async def get_audio_stream(self) -> AsyncIterator[bytes]:
        """
        Async iterator that yields audio chunks.

        Yields:
            bytes: 500ms audio chunks (8000 samples * 2 bytes = 16000 bytes)
        """
        poll_interval = 0.05  # 50ms polling interval

        while self._is_capturing:
            # Check if we have enough samples for a chunk
            if self._buffer.size >= CHUNK_SAMPLES:
                samples = self._buffer.read(CHUNK_SAMPLES)
                yield samples_to_bytes(samples)
            else:
                # Wait for more data
                await asyncio.sleep(poll_interval)

    async def _start_platform_capture(self) -> None:
        """
        Start platform-specific audio capture.

        Override point for platform implementations.
        """
        self._loop = asyncio.get_event_loop()

        if self._backend == "pyaudiowpatch":
            await self._start_wasapi_capture()
        else:
            await self._start_sounddevice_capture()

    async def _stop_platform_capture(self) -> None:
        """
        Stop platform-specific audio capture.

        Override point for platform implementations.
        """
        if self._stream is not None:
            try:
                if self._backend == "pyaudiowpatch":
                    self._stream.stop_stream()
                    self._stream.close()
                else:
                    self._stream.stop()
                    self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing audio stream: {e}")
            finally:
                self._stream = None

        if self._capture_task is not None:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None

    async def _start_wasapi_capture(self) -> None:
        """
        Start WASAPI loopback capture (Windows).

        Uses pyaudiowpatch for system audio capture.
        """
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            raise AudioCaptureError(
                "pyaudiowpatch not installed. Install with: pip install pyaudiowpatch"
            )

        try:
            p = pyaudio.PyAudio()

            # Find the default WASAPI loopback device
            wasapi_info = None
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            except OSError:
                raise AudioCaptureError("WASAPI audio API not available")

            # Get default output device info to find its name
            default_output_device = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            default_output_name = default_output_device["name"]
            
            logger.info(f"Default output device: {default_output_name}")

            # Find the corresponding loopback device
            target_loopback_device = None
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info["hostApi"] != wasapi_info["index"]:
                    continue
                    
                if device_info.get("isLoopbackDevice", False):
                    # Check if this loopback device corresponds to our default output
                    # Loopback devices usually have "[Loopback]" appended to the name
                    # e.g. "Speakers (Realtek) [Loopback]" matches "Speakers (Realtek)"
                    dev_name = device_info["name"]
                    
                    # Exact match (some drivers) or name inclusion
                    if default_output_name in dev_name:
                        target_loopback_device = device_info
                        break
            
            # Fallback: Use the first available loopback device if no name match
            if target_loopback_device is None:
                logger.warning("Could not match loopback to default output, trying first available loopback")
                for i in range(p.get_device_count()):
                    device_info = p.get_device_info_by_index(i)
                    if device_info["hostApi"] == wasapi_info["index"] and device_info.get("isLoopbackDevice", False):
                        target_loopback_device = device_info
                        break

            if target_loopback_device is None:
                raise AudioCaptureError("No loopback audio device found")

            # Create audio callback
            def audio_callback(in_data, frame_count, time_info, status):
                if in_data:
                    # Convert to mono 16kHz int16
                    samples = np.frombuffer(in_data, dtype=np.float32)

                    # Handle multi-channel: average channels to mono
                    channels = int(target_loopback_device["maxInputChannels"])
                    if channels > 1:
                        samples = samples.reshape(-1, channels).mean(axis=1)

                    # Resample to 16kHz if needed
                    device_rate = int(target_loopback_device["defaultSampleRate"])
                    if device_rate != SAMPLE_RATE:
                        samples = self._resample(samples, device_rate, SAMPLE_RATE)

                    # Convert to int16
                    samples_int16 = (samples * 32767).astype(np.int16)
                    self._buffer.write(samples_int16)

                return (None, pyaudio.paContinue)

            # Open stream
            self._stream = p.open(
                format=pyaudio.paFloat32,
                channels=int(target_loopback_device["maxInputChannels"]),
                rate=int(target_loopback_device["defaultSampleRate"]),
                input=True,
                input_device_index=int(target_loopback_device["index"]),
                stream_callback=audio_callback,
                frames_per_buffer=1024
            )

            self._stream.start_stream()
            logger.info(f"WASAPI loopback started: {target_loopback_device.get('name', 'Unknown')}")

        except AudioCaptureError:
            raise
        except Exception as e:
            raise AudioCaptureError(f"Failed to start WASAPI capture: {e}")

    async def _start_sounddevice_capture(self) -> None:
        """
        Start sounddevice capture (macOS/Linux).

        Uses sounddevice for system audio capture.
        """
        try:
            import sounddevice as sd
        except ImportError:
            raise AudioCaptureError(
                "sounddevice not installed. Install with: pip install sounddevice"
            )

        try:
            # Audio callback for sounddevice
            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Sounddevice status: {status}")

                # Convert to mono int16
                samples = indata[:, 0] if indata.ndim > 1 else indata.flatten()
                samples_int16 = (samples * 32767).astype(np.int16)
                self._buffer.write(samples_int16)

            # Open input stream
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=np.float32,
                callback=audio_callback,
                blocksize=1024
            )

            self._stream.start()
            logger.info("Sounddevice input stream started")

        except sd.PortAudioError as e:
            raise AudioCaptureError(f"PortAudio error: {e}")
        except Exception as e:
            raise AudioCaptureError(f"Failed to start sounddevice capture: {e}")

    def _resample(
        self,
        samples: np.ndarray,
        orig_rate: int,
        target_rate: int
    ) -> np.ndarray:
        """
        Resample audio from one sample rate to another.

        Args:
            samples: Input audio samples
            orig_rate: Original sample rate
            target_rate: Target sample rate

        Returns:
            Resampled audio samples
        """
        if orig_rate == target_rate:
            return samples

        # Simple linear resampling (scipy would be better but adds dependency)
        ratio = target_rate / orig_rate
        new_length = int(len(samples) * ratio)

        indices = np.linspace(0, len(samples) - 1, new_length)
        return np.interp(indices, np.arange(len(samples)), samples)
