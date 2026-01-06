"""
Tests for the audio capture module.

Following TDD: these tests are written first, before implementation.
"""

import asyncio
import sys
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import numpy as np
import pytest
import pytest_asyncio

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestCircularBuffer:
    """Tests for the CircularBuffer class."""

    def test_circular_buffer_creation(self):
        """Circular buffer should be created with specified capacity."""
        from audio.capture import CircularBuffer

        buffer = CircularBuffer(capacity=80000)
        assert buffer.capacity == 80000
        assert buffer.size == 0

    def test_circular_buffer_write_and_read(self):
        """Buffer should allow writing and reading audio samples."""
        from audio.capture import CircularBuffer

        buffer = CircularBuffer(capacity=80000)

        # Write some samples
        samples = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        buffer.write(samples)

        assert buffer.size == 5

        # Read samples
        read_samples = buffer.read(5)
        np.testing.assert_array_equal(read_samples, samples)
        assert buffer.size == 0  # Reading should consume the samples

    def test_circular_buffer_overwrites_on_full(self):
        """Buffer should overwrite oldest data when full."""
        from audio.capture import CircularBuffer

        buffer = CircularBuffer(capacity=10)

        # Write more samples than capacity
        first_batch = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.int16)
        buffer.write(first_batch)
        assert buffer.size == 10

        # Write more - should overwrite oldest
        second_batch = np.array([11, 12, 13, 14, 15], dtype=np.int16)
        buffer.write(second_batch)

        # Size should still be capacity
        assert buffer.size == 10

        # Should read most recent 10 samples (6-15)
        read_samples = buffer.read(10)
        expected = np.array([6, 7, 8, 9, 10, 11, 12, 13, 14, 15], dtype=np.int16)
        np.testing.assert_array_equal(read_samples, expected)

    def test_circular_buffer_read_less_than_available(self):
        """Buffer should support reading less samples than available."""
        from audio.capture import CircularBuffer

        buffer = CircularBuffer(capacity=80000)

        # Write 10 samples
        samples = np.arange(10, dtype=np.int16)
        buffer.write(samples)

        # Read only 5
        read_samples = buffer.read(5)
        np.testing.assert_array_equal(read_samples, np.arange(5, dtype=np.int16))
        assert buffer.size == 5  # 5 samples remaining

    def test_circular_buffer_read_more_than_available(self):
        """Buffer should return available samples when requesting more."""
        from audio.capture import CircularBuffer

        buffer = CircularBuffer(capacity=80000)

        # Write 5 samples
        samples = np.arange(5, dtype=np.int16)
        buffer.write(samples)

        # Request 10, should get 5
        read_samples = buffer.read(10)
        np.testing.assert_array_equal(read_samples, samples)
        assert buffer.size == 0

    def test_circular_buffer_thread_safety(self):
        """Buffer should be thread-safe for concurrent read/write."""
        from audio.capture import CircularBuffer

        buffer = CircularBuffer(capacity=80000)
        errors = []
        written_count = [0]
        read_count = [0]

        def writer():
            try:
                for i in range(100):
                    samples = np.array([i, i + 1, i + 2], dtype=np.int16)
                    buffer.write(samples)
                    written_count[0] += 3
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(100):
                    samples = buffer.read(2)
                    read_count[0] += len(samples)
            except Exception as e:
                errors.append(e)

        # Run writer and reader concurrently
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join()
        reader_thread.join()

        # No errors should occur
        assert len(errors) == 0

    def test_circular_buffer_clear(self):
        """Buffer should support clearing all data."""
        from audio.capture import CircularBuffer

        buffer = CircularBuffer(capacity=80000)
        samples = np.arange(100, dtype=np.int16)
        buffer.write(samples)

        assert buffer.size == 100
        buffer.clear()
        assert buffer.size == 0

    def test_circular_buffer_5_second_capacity(self):
        """Buffer should hold 5 seconds of 16kHz mono audio (80000 samples)."""
        from audio.capture import CircularBuffer

        # 5 seconds at 16kHz = 80000 samples
        buffer = CircularBuffer(capacity=80000)

        # Fill with 5 seconds of audio
        samples = np.zeros(80000, dtype=np.int16)
        buffer.write(samples)

        assert buffer.size == 80000


class TestPlatformDetection:
    """Tests for platform-specific audio backend selection."""

    @patch("sys.platform", "win32")
    def test_windows_uses_pyaudiowpatch(self):
        """Windows should use pyaudiowpatch backend."""
        from audio.capture import get_platform_backend

        backend = get_platform_backend()
        assert backend == "pyaudiowpatch"

    @patch("sys.platform", "darwin")
    def test_macos_uses_sounddevice(self):
        """macOS should use sounddevice backend."""
        from audio.capture import get_platform_backend

        backend = get_platform_backend()
        assert backend == "sounddevice"

    @patch("sys.platform", "linux")
    def test_linux_uses_sounddevice(self):
        """Linux should use sounddevice backend."""
        from audio.capture import get_platform_backend

        backend = get_platform_backend()
        assert backend == "sounddevice"


class TestAudioCaptureConstants:
    """Tests for audio capture configuration constants."""

    def test_sample_rate_is_16khz(self):
        """Sample rate should be 16kHz."""
        from audio.capture import SAMPLE_RATE

        assert SAMPLE_RATE == 16000

    def test_channels_is_mono(self):
        """Audio should be mono (1 channel)."""
        from audio.capture import CHANNELS

        assert CHANNELS == 1

    def test_format_is_int16(self):
        """Audio format should be 16-bit PCM (int16)."""
        from audio.capture import SAMPLE_DTYPE

        assert SAMPLE_DTYPE == np.int16

    def test_chunk_duration_is_500ms(self):
        """Chunk duration should be 500ms."""
        from audio.capture import CHUNK_DURATION_MS

        assert CHUNK_DURATION_MS == 500

    def test_chunk_size_is_8000_samples(self):
        """500ms at 16kHz = 8000 samples."""
        from audio.capture import CHUNK_SAMPLES

        assert CHUNK_SAMPLES == 8000

    def test_buffer_duration_is_5_seconds(self):
        """Buffer should hold 5 seconds of audio."""
        from audio.capture import BUFFER_DURATION_SEC

        assert BUFFER_DURATION_SEC == 5

    def test_buffer_capacity_is_80000_samples(self):
        """5 seconds at 16kHz = 80000 samples."""
        from audio.capture import BUFFER_SAMPLES

        assert BUFFER_SAMPLES == 80000


class TestAudioCaptureClass:
    """Tests for the AudioCapture class."""

    def test_audio_capture_creation(self):
        """AudioCapture should be created successfully."""
        from audio.capture import AudioCapture

        capture = AudioCapture()
        assert capture is not None
        assert capture.is_capturing is False

    def test_audio_capture_has_buffer(self):
        """AudioCapture should have an internal buffer."""
        from audio.capture import AudioCapture

        capture = AudioCapture()
        assert hasattr(capture, "_buffer")
        assert capture._buffer is not None

    @pytest.mark.asyncio
    async def test_start_capture_changes_state(self):
        """start_capture should change is_capturing to True."""
        from audio.capture import AudioCapture

        capture = AudioCapture()

        # Mock the audio backend to prevent actual device access
        with patch.object(capture, "_start_platform_capture", new_callable=AsyncMock):
            await capture.start_capture()
            assert capture.is_capturing is True

            # Cleanup
            await capture.stop_capture()

    @pytest.mark.asyncio
    async def test_stop_capture_changes_state(self):
        """stop_capture should change is_capturing to False."""
        from audio.capture import AudioCapture

        capture = AudioCapture()

        with patch.object(capture, "_start_platform_capture", new_callable=AsyncMock):
            with patch.object(capture, "_stop_platform_capture", new_callable=AsyncMock):
                await capture.start_capture()
                assert capture.is_capturing is True

                await capture.stop_capture()
                assert capture.is_capturing is False

    @pytest.mark.asyncio
    async def test_stop_capture_clears_buffer(self):
        """stop_capture should clear the audio buffer."""
        from audio.capture import AudioCapture

        capture = AudioCapture()

        # Add some data to buffer
        samples = np.arange(1000, dtype=np.int16)
        capture._buffer.write(samples)
        assert capture._buffer.size > 0

        # Simulate that capture was started
        capture._is_capturing = True

        with patch.object(capture, "_stop_platform_capture", new_callable=AsyncMock):
            await capture.stop_capture()
            assert capture._buffer.size == 0

    @pytest.mark.asyncio
    async def test_double_start_capture_is_safe(self):
        """Calling start_capture twice should be safe."""
        from audio.capture import AudioCapture

        capture = AudioCapture()

        with patch.object(capture, "_start_platform_capture", new_callable=AsyncMock) as mock_start:
            await capture.start_capture()
            await capture.start_capture()  # Second call should be ignored

            # Should only start once
            assert mock_start.call_count == 1
            assert capture.is_capturing is True

            # Cleanup
            await capture.stop_capture()

    @pytest.mark.asyncio
    async def test_stop_capture_when_not_started_is_safe(self):
        """Calling stop_capture when not started should be safe."""
        from audio.capture import AudioCapture

        capture = AudioCapture()

        # Should not raise
        await capture.stop_capture()
        assert capture.is_capturing is False


class TestAudioStream:
    """Tests for the async audio stream generator."""

    @pytest.mark.asyncio
    async def test_get_audio_stream_returns_async_iterator(self):
        """get_audio_stream should return an async iterator."""
        from audio.capture import AudioCapture

        capture = AudioCapture()

        stream = capture.get_audio_stream()
        assert hasattr(stream, "__aiter__")
        assert hasattr(stream, "__anext__")

    @pytest.mark.asyncio
    async def test_audio_stream_yields_bytes(self):
        """Audio stream should yield bytes objects."""
        from audio.capture import AudioCapture

        capture = AudioCapture()

        # Pre-fill buffer with enough samples for one chunk
        samples = np.zeros(8000, dtype=np.int16)  # 500ms at 16kHz
        capture._buffer.write(samples)

        # Mock capturing state
        capture._is_capturing = True

        # Get one chunk
        stream = capture.get_audio_stream()
        chunk = await asyncio.wait_for(stream.__anext__(), timeout=1.0)

        assert isinstance(chunk, bytes)

        # Cleanup
        capture._is_capturing = False

    @pytest.mark.asyncio
    async def test_audio_stream_chunk_size(self):
        """Each audio chunk should be 500ms (8000 samples = 16000 bytes)."""
        from audio.capture import AudioCapture, CHUNK_SAMPLES

        capture = AudioCapture()

        # Pre-fill buffer with exactly one chunk
        samples = np.zeros(CHUNK_SAMPLES, dtype=np.int16)
        capture._buffer.write(samples)

        # Mock capturing state
        capture._is_capturing = True

        stream = capture.get_audio_stream()
        chunk = await asyncio.wait_for(stream.__anext__(), timeout=1.0)

        # 8000 samples * 2 bytes per int16 = 16000 bytes
        assert len(chunk) == CHUNK_SAMPLES * 2

        # Cleanup
        capture._is_capturing = False

    @pytest.mark.asyncio
    async def test_audio_stream_stops_when_capture_stops(self):
        """Audio stream should stop when capture is stopped."""
        from audio.capture import AudioCapture

        capture = AudioCapture()
        capture._is_capturing = True

        async def stop_capture_after_delay():
            await asyncio.sleep(0.1)
            capture._is_capturing = False

        asyncio.create_task(stop_capture_after_delay())

        stream = capture.get_audio_stream()
        chunks = []
        try:
            async for chunk in stream:
                chunks.append(chunk)
                if len(chunks) > 10:  # Safety limit
                    break
        except StopAsyncIteration:
            pass

        # Stream should have stopped
        assert capture._is_capturing is False


class TestAudioCaptureErrorHandling:
    """Tests for error handling in audio capture."""

    @pytest.mark.asyncio
    async def test_start_capture_handles_device_error(self):
        """start_capture should handle device access errors gracefully."""
        from audio.capture import AudioCapture, AudioCaptureError

        capture = AudioCapture()

        # Mock a device access error
        with patch.object(
            capture,
            "_start_platform_capture",
            new_callable=AsyncMock,
            side_effect=AudioCaptureError("No audio device found")
        ):
            with pytest.raises(AudioCaptureError) as exc_info:
                await capture.start_capture()

            assert "No audio device found" in str(exc_info.value)
            assert capture.is_capturing is False

    @pytest.mark.asyncio
    async def test_start_capture_handles_permission_error(self):
        """start_capture should handle permission errors gracefully."""
        from audio.capture import AudioCapture, AudioCaptureError

        capture = AudioCapture()

        # Mock a permission error
        with patch.object(
            capture,
            "_start_platform_capture",
            new_callable=AsyncMock,
            side_effect=PermissionError("Microphone access denied")
        ):
            with pytest.raises(AudioCaptureError) as exc_info:
                await capture.start_capture()

            assert "permission" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()
            assert capture.is_capturing is False


class TestAudioChunkConversion:
    """Tests for audio data conversion to bytes."""

    def test_samples_to_bytes_conversion(self):
        """int16 samples should convert to bytes correctly."""
        from audio.capture import samples_to_bytes

        samples = np.array([0, 100, -100, 32767, -32768], dtype=np.int16)
        result = samples_to_bytes(samples)

        assert isinstance(result, bytes)
        assert len(result) == len(samples) * 2  # 2 bytes per int16

        # Convert back and verify
        recovered = np.frombuffer(result, dtype=np.int16)
        np.testing.assert_array_equal(recovered, samples)

    def test_bytes_to_samples_conversion(self):
        """bytes should convert to int16 samples correctly."""
        from audio.capture import bytes_to_samples

        original = np.array([0, 100, -100, 32767, -32768], dtype=np.int16)
        byte_data = original.tobytes()

        result = bytes_to_samples(byte_data)
        np.testing.assert_array_equal(result, original)


class TestAudioCaptureLifecycle:
    """Tests for complete audio capture lifecycle."""

    @pytest.mark.asyncio
    async def test_full_capture_lifecycle(self):
        """Test complete start -> capture -> stop lifecycle."""
        from audio.capture import AudioCapture

        capture = AudioCapture()
        data_feed_task = None

        # Mock platform capture that schedules background data feeding
        async def mock_start():
            nonlocal data_feed_task

            async def feed_data():
                # Simulate audio coming in
                for i in range(10):
                    if capture._is_capturing:
                        samples = np.full(1600, i, dtype=np.int16)  # 100ms of data
                        capture._buffer.write(samples)
                    await asyncio.sleep(0.02)

            data_feed_task = asyncio.create_task(feed_data())

        with patch.object(capture, "_start_platform_capture", side_effect=mock_start):
            with patch.object(capture, "_stop_platform_capture", new_callable=AsyncMock):
                # Start capture
                await capture.start_capture()

                # Wait for some data to be fed
                await asyncio.sleep(0.1)

                # Buffer should have data
                assert capture._buffer.size > 0

                # Stop capture
                await capture.stop_capture()

                # Cancel the feed task
                if data_feed_task:
                    data_feed_task.cancel()
                    try:
                        await data_feed_task
                    except asyncio.CancelledError:
                        pass

                # Should be stopped and buffer cleared
                assert capture.is_capturing is False
                assert capture._buffer.size == 0

    @pytest.mark.asyncio
    async def test_context_manager_support(self):
        """AudioCapture should support async context manager."""
        from audio.capture import AudioCapture

        with patch.object(AudioCapture, "_start_platform_capture", new_callable=AsyncMock):
            with patch.object(AudioCapture, "_stop_platform_capture", new_callable=AsyncMock):
                async with AudioCapture() as capture:
                    assert capture.is_capturing is True

                # After context, should be stopped
                assert capture.is_capturing is False
