"""Pytest fixtures and configuration."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication singleton for the test session.

    Creates the QApplication if it does not already exist.
    This avoids conflicts with PySide6/Qt singleton requirements.
    """
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 not available")

    app = QApplication.instance()
    if app is None:
        app = QApplication(["test"])
    yield app
    # Do not call app.quit() here — session-scoped singleton
    # must remain alive for the full test session.


# ---------------------------------------------------------------------------
# Audio / VAD fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_audio_16khz():
    """Generate ~1.5 seconds of synthetic 16 kHz int16 audio.

    The signal alternates between silence and a 440 Hz sine wave in
    300 ms segments (10 x 30 ms blocks), making it easy to align with
    VAD frame boundaries.
    """
    samplerate = 16000
    blocksize = 480  # 30 ms @ 16 kHz
    segment_blocks = 10  # 300 ms
    segment_samples = segment_blocks * blocksize  # 4800 samples

    # Five segments: silence, sine, silence, sine, silence
    num_segments = 5
    total_samples = num_segments * segment_samples
    t = np.linspace(0, total_samples / samplerate, total_samples, endpoint=False)
    audio = np.zeros(total_samples, dtype=np.float64)

    for seg_idx in range(num_segments):
        start = seg_idx * segment_samples
        end = start + segment_samples
        if seg_idx % 2 == 1:  # odd segments = sine wave
            audio[start:end] = np.sin(2 * np.pi * 440 * t[start:end])

    return (audio * 32767).astype(np.int16)


@pytest.fixture
def mock_sounddevice():
    """Mock ``sounddevice`` so no physical microphone is required."""
    import audio_capture as _ac

    with patch.object(_ac, "sd") as mock:
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

        class MockStream:
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

        mock.InputStream = MockStream
        yield mock


@pytest.fixture
def mock_webrtcvad():
    """Mock ``webrtcvad.Vad`` so state machine tests are deterministic."""
    import speech_detector as _sd

    with patch.object(_sd, "webrtcvad") as mock_module:
        instance = MagicMock()
        mock_module.Vad.return_value = instance
        yield instance
