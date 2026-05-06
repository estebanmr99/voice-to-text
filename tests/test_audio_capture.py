"""Tests for AudioCapture.

All tests mock ``sounddevice`` so no physical microphone is required.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import audio_capture as ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockStream:
    """Stand-in for ``sd.InputStream``."""

    def __init__(self, *args, **kwargs):
        self._callback = kwargs.get("callback")
        self._blocksize = kwargs.get("blocksize", 480)
        self._channels = kwargs.get("channels", 1)
        self.active = False

    def start(self):
        self.active = True

    def stop(self):
        self.active = False

    def close(self):
        self.active = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_sd():
    """Patch ``audio_capture.sd`` with a minimal mock."""
    with patch.object(ac, "sd") as mock:
        devices = [
            {
                "name": "Mock Microphone",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
            {
                "name": "Mock Speaker",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
        ]

        def _side_effect(kind=None):
            if kind == "input":
                return devices[0]
            if isinstance(kind, int):
                return devices[kind]
            return devices

        mock.query_devices.side_effect = _side_effect
        mock.InputStream = _MockStream
        yield mock


# ---------------------------------------------------------------------------
# Device introspection
# ---------------------------------------------------------------------------


class TestAudioCaptureDevices:
    def test_list_devices_returns_only_input(self, mock_sd):
        devices = ac.AudioCapture.list_devices()
        assert len(devices) == 1
        assert devices[0]["name"] == "Mock Microphone"
        assert devices[0]["index"] == 0
        assert devices[0]["display_name"] == "Mock Microphone (2 channels)"

    def test_get_default_device(self, mock_sd):
        dev = ac.AudioCapture.get_default_device()
        assert dev["name"] == "Mock Microphone"

    def test_list_devices_adds_hostapi_labels_and_deduplicates(self, mock_sd):
        mock_sd.query_devices.side_effect = None
        mock_sd.query_devices.return_value = [
            {
                "name": "Logitech BRIO Mic",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
                "hostapi": 0,
            },
            {
                "name": "Logitech BRIO Mic",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
                "hostapi": 0,
            },
        ]
        mock_sd.query_hostapis.return_value = [{"name": "Windows WASAPI"}]

        devices = ac.AudioCapture.list_devices()

        assert len(devices) == 1
        assert devices[0]["hostapi_name"] == "Windows WASAPI"
        assert devices[0]["display_name"] == "Logitech BRIO Mic — Windows WASAPI (1 channel)"


# ---------------------------------------------------------------------------
# Construction / configuration
# ---------------------------------------------------------------------------


class TestAudioCaptureConfig:
    def test_default_samplerate(self):
        cap = ac.AudioCapture()
        assert cap.samplerate == 16000

    def test_default_block_duration(self):
        cap = ac.AudioCapture()
        assert cap.block_duration_ms == 30

    def test_blocksize_calculation(self):
        cap = ac.AudioCapture(samplerate=16000, block_duration_ms=30)
        assert cap.blocksize == 480

    def test_custom_samplerate_blocksize(self):
        cap = ac.AudioCapture(samplerate=8000, block_duration_ms=20)
        assert cap.blocksize == 160

    def test_set_device_index_updates_preferred_device(self):
        cap = ac.AudioCapture()
        cap.set_device_index(5)
        assert cap.device_index == 5


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestAudioCaptureLifecycle:
    def test_start_stop(self, mock_sd):
        cap = ac.AudioCapture()
        callback = MagicMock()
        cap.start(callback)
        assert cap.is_active()
        cap.stop()
        assert not cap.is_active()

    def test_double_start_raises(self, mock_sd):
        cap = ac.AudioCapture()
        cap.start(MagicMock())
        with pytest.raises(RuntimeError, match="already active"):
            cap.start(MagicMock())
        cap.stop()

    def test_stop_when_inactive_is_safe(self):
        cap = ac.AudioCapture()
        cap.stop()  # should not raise

    def test_fallback_on_stream_open_failure(self, mock_sd):
        """T-02-05: fallback to an available input device when specified device fails."""
        calls = []

        def failing_then_ok(*args, **kwargs):
            calls.append(kwargs.get("device"))
            if kwargs.get("device") == 99:
                raise RuntimeError("bad device")
            return _MockStream(*args, **kwargs)

        mock_sd.InputStream = failing_then_ok
        cap = ac.AudioCapture(device_index=99)
        cap.start(MagicMock())
        assert calls == [99, 0]
        assert cap.is_active()
        cap.stop()

    def test_fallback_when_default_device_is_invalid(self, mock_sd):
        """Recover when PortAudio's default input maps to an invalid device."""
        calls = []

        def default_fails_then_explicit_ok(*args, **kwargs):
            calls.append(kwargs.get("device"))
            if "device" not in kwargs:
                raise RuntimeError("Error querying device -1")
            return _MockStream(*args, **kwargs)

        mock_sd.InputStream = default_fails_then_explicit_ok
        cap = ac.AudioCapture()
        cap.start(MagicMock())
        assert calls == [None, 0]
        assert cap.is_active()
        cap.stop()

    def test_retry_with_device_default_samplerate(self, mock_sd):
        """Retry the same device at its native rate before falling back."""
        calls = []

        def invalid_16k_then_ok(*args, **kwargs):
            calls.append((kwargs.get("device"), kwargs.get("samplerate")))
            if kwargs.get("samplerate") == 16000:
                raise RuntimeError("Invalid sample rate [PaErrorCode -9997]")
            return _MockStream(*args, **kwargs)

        mock_sd.query_devices.side_effect = None
        mock_sd.query_devices.return_value = [
            {
                "name": "Logitech BRIO Mic",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            }
        ]
        mock_sd.InputStream = invalid_16k_then_ok

        cap = ac.AudioCapture(device_index=0)
        cap.start(MagicMock())

        assert calls == [(0, 16000), (0, 48000)]
        assert cap.is_active()
        cap.stop()

    def test_start_failure_does_not_leave_consumer_thread_running(self, mock_sd):
        """A failed stream open must not leave capture in a half-running state."""
        mock_sd.query_devices.return_value = []
        mock_sd.query_devices.side_effect = None
        mock_sd.InputStream = MagicMock(side_effect=RuntimeError("no usable input"))

        cap = ac.AudioCapture(device_index=99)
        with pytest.raises(RuntimeError, match="no usable input"):
            cap.start(MagicMock())

        assert cap._stream is None
        assert cap._running is False
        assert cap._consumer_thread is None


# ---------------------------------------------------------------------------
# Callback / data flow
# ---------------------------------------------------------------------------


class TestAudioCaptureCallback:
    def test_callback_receives_expected_buffer_shape(self, mock_sd):
        cap = ac.AudioCapture()
        received = []

        def callback(block: np.ndarray) -> None:
            received.append(block)

        cap.start(callback)
        # Manually inject a buffer as PortAudio would
        fake = np.zeros((cap.blocksize, 1), dtype=np.int16)
        cap._stream_callback(fake, cap.blocksize, None, None)
        time.sleep(0.05)  # let consumer thread process
        cap.stop()

        assert len(received) == 1
        assert received[0].shape == (cap.blocksize,)
        assert received[0].dtype == np.int16

    def test_callback_receives_multiple_blocks(self, mock_sd):
        cap = ac.AudioCapture()
        received = []

        def callback(block: np.ndarray) -> None:
            received.append(block)

        cap.start(callback)
        for _ in range(5):
            fake = np.ones((cap.blocksize, 1), dtype=np.int16)
            cap._stream_callback(fake, cap.blocksize, None, None)
        time.sleep(0.1)
        cap.stop()

        assert len(received) == 5

    def test_callback_resamples_native_rate_block_to_processing_size(self, mock_sd):
        cap = ac.AudioCapture(samplerate=16000, block_duration_ms=30)
        received = []

        def callback(block: np.ndarray) -> None:
            received.append(block)

        cap.start(callback)
        cap._stream_samplerate = 48000
        native_blocksize = int(48000 * cap.block_duration_ms / 1000)
        fake = np.arange(native_blocksize, dtype=np.int16).reshape(-1, 1)
        cap._stream_callback(fake, native_blocksize, None, None)
        time.sleep(0.05)
        cap.stop()

        assert len(received) == 1
        assert received[0].shape == (cap.blocksize,)
        assert received[0].dtype == np.int16

    def test_queue_bridge_is_thread_safe(self, mock_sd):
        """Smoke-test that the queue-based bridge doesn't explode under load."""
        cap = ac.AudioCapture()
        count = 0

        def callback(_block):
            nonlocal count
            count += 1

        cap.start(callback)
        for _ in range(100):
            fake = np.zeros((cap.blocksize, 1), dtype=np.int16)
            cap._stream_callback(fake, cap.blocksize, None, None)
        time.sleep(0.2)
        cap.stop()

        assert count == 100

    def test_get_audio_callback_helper(self):
        """The standalone callback helper enqueues correctly."""
        cap = ac.AudioCapture()
        q = ac.queue.Queue()
        helper = cap.get_audio_callback(q)

        fake = np.arange(cap.blocksize, dtype=np.int16).reshape(-1, 1)
        helper(fake, cap.blocksize, None, None)

        block = q.get(timeout=0.1)
        assert block.shape == (cap.blocksize,)
        assert np.array_equal(block, fake[:, 0])


# ---------------------------------------------------------------------------
# Threat-model audit: no audio persistence
# ---------------------------------------------------------------------------


class TestAudioCapturePrivacy:
    def test_no_file_writing_patterns(self):
        """T-02-04: verify the module never writes audio to disk."""
        import inspect

        source = inspect.getsource(ac)
        assert "open(" not in source or "'wb'" not in source
        assert "np.save" not in source
        assert "tofile" not in source


class TestAudioCaptureFallbackFiltering:
    def test_find_fallback_prefers_microphone_over_loopback_name(self, mock_sd):
        mock_sd.query_devices.side_effect = None
        mock_sd.query_devices.return_value = [
            {
                "name": "Stereo Mix (Realtek)",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
            {
                "name": "Logitech BRIO Mic",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
        ]

        assert ac.AudioCapture._find_fallback_input_device_index() == 1
