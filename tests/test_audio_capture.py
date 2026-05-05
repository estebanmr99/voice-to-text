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

    def test_get_default_device(self, mock_sd):
        dev = ac.AudioCapture.get_default_device()
        assert dev["name"] == "Mock Microphone"


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
        """T-02-05: fallback to default device when specified device fails."""
        calls = []

        def failing_then_ok(*args, **kwargs):
            calls.append(kwargs.get("device"))
            if kwargs.get("device") == 99:
                raise RuntimeError("bad device")
            return _MockStream(*args, **kwargs)

        mock_sd.InputStream = failing_then_ok
        cap = ac.AudioCapture(device_index=99)
        cap.start(MagicMock())
        assert calls == [99, None]
        assert cap.is_active()
        cap.stop()


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
