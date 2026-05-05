"""WebRTC VAD speech/silence detection.

Audio buffers are strictly in-memory; no audio data is ever persisted to disk.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import webrtcvad
except ImportError:  # pragma: no cover
    webrtcvad = None  # type: ignore[assignment]


class VADEvent(Enum):
    """Events produced by the speech-detection state machine."""

    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    SILENCE = "silence"


class SpeechDetector:
    """Detect speech in an audio stream using WebRTC VAD.

    Parameters
    ----------
    aggressiveness:
        VAD aggressiveness mode (0 = least aggressive, 3 = most aggressive).
    frame_duration_ms:
        Frame size in milliseconds. Must be 10, 20, or 30.
    samplerate:
        Sampling rate in Hz. Must be 8000, 16000, or 32000.

    The state machine declares :attr:`VADEvent.SPEECH_START` after
    ~90 ms (3 frames) of consecutive speech and
    :attr:`VADEvent.SPEECH_END` after ~300 ms (10 frames) of consecutive
    silence.
    """

    _SPEECH_THRESHOLD = 3   # frames
    _SILENCE_THRESHOLD = 10  # frames

    def __init__(
        self,
        aggressiveness: int = 1,
        frame_duration_ms: int = 30,
        samplerate: int = 16000,
    ) -> None:
        if webrtcvad is None:
            raise RuntimeError("webrtcvad is not installed")
        if aggressiveness not in (0, 1, 2, 3):
            raise ValueError("aggressiveness must be 0, 1, 2, or 3")
        if frame_duration_ms not in (10, 20, 30):
            raise ValueError("frame_duration_ms must be 10, 20, or 30")
        if samplerate not in (8000, 16000, 32000):
            raise ValueError("samplerate must be 8000, 16000, or 32000")

        self._aggressiveness = aggressiveness
        self._frame_duration_ms = frame_duration_ms
        self._samplerate = samplerate
        self._frame_size = int(samplerate * frame_duration_ms / 1000)

        self._vad: Any = webrtcvad.Vad(aggressiveness)

        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False
        self._buffer = bytearray()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_speech(self, frame: np.ndarray) -> bool:
        """Return the raw WebRTC VAD decision for a single frame.

        *frame* must be a one-dimensional ``np.ndarray`` of ``int16``
        with length equal to ``frame_size``.
        """
        if len(frame) != self._frame_size:
            raise ValueError(
                f"Frame size {len(frame)} does not match expected "
                f"{self._frame_size} for {self._samplerate} Hz @ "
                f"{self._frame_duration_ms} ms"
            )
        if frame.dtype != np.int16:
            raise TypeError(f"Frame dtype must be int16, got {frame.dtype}")
        return self._vad.is_speech(frame.tobytes(), self._samplerate)

    def process_frame(self, frame: np.ndarray) -> VADEvent | None:
        """Process one frame and return an event on state transitions.

        Returns :attr:`VADEvent.SPEECH_START` when speech is first
        detected, :attr:`VADEvent.SPEECH_END` when silence follows
        speech, :attr:`VADEvent.SILENCE` while no speech is detected,
        or ``None`` when speech continues without a transition.

        While in-speech, audio is accumulated into an internal buffer
        that can be retrieved via :meth:`speech_buffer`.
        """
        speech = self.is_speech(frame)

        if speech:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            self._silence_frames += 1
            self._speech_frames = 0

        if not self._in_speech and self._speech_frames >= self._SPEECH_THRESHOLD:
            self._in_speech = True
            self._buffer = bytearray(frame.tobytes())
            return VADEvent.SPEECH_START

        if self._in_speech:
            self._buffer.extend(frame.tobytes())
            if self._silence_frames >= self._SILENCE_THRESHOLD:
                self._in_speech = False
                return VADEvent.SPEECH_END
            # Still in speech — no transition event
            return None

        return VADEvent.SILENCE

    def reset(self) -> None:
        """Clear the internal state machine and discard any buffer."""
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False
        self._buffer = bytearray()

    @property
    def speech_buffer(self) -> np.ndarray:
        """Return the accumulated speech buffer as ``int16``.

        The buffer is available after :attr:`VADEvent.SPEECH_START` and
        remains valid until the next :attr:`VADEvent.SPEECH_START` or
        a call to :meth:`reset`.
        """
        return np.frombuffer(self._buffer, dtype=np.int16)

    @property
    def frame_size(self) -> int:
        """Number of samples per frame."""
        return self._frame_size

    @property
    def in_speech(self) -> bool:
        """Return ``True`` if currently inside a speech segment."""
        return self._in_speech
