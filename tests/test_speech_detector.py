"""Tests for SpeechDetector.

All tests mock ``webrtcvad`` so the state machine can be verified
independently of the VAD library's internal heuristics.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import speech_detector as sd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vad():
    """Provide a mock VAD backend for deterministic tests."""
    instance = MagicMock()
    yield instance


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------


class TestSpeechDetectorConfig:
    def test_default_parameters(self, mock_vad):
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        assert detector.frame_size == 480  # 16000 * 0.03

    def test_aggressiveness_levels(self, mock_vad):
        for level in (0, 1, 2, 3):
            sd.SpeechDetector(aggressiveness=level, vad_backend=mock_vad)
        assert mock_vad.is_speech is not None

    def test_invalid_aggressiveness_raises(self, mock_vad):
        with pytest.raises(ValueError, match="aggressiveness"):
            sd.SpeechDetector(aggressiveness=4, vad_backend=mock_vad)

    def test_invalid_frame_duration_raises(self, mock_vad):
        with pytest.raises(ValueError, match="frame_duration_ms"):
            sd.SpeechDetector(frame_duration_ms=15, vad_backend=mock_vad)

    def test_invalid_samplerate_raises(self, mock_vad):
        with pytest.raises(ValueError, match="samplerate"):
            sd.SpeechDetector(samplerate=44100, vad_backend=mock_vad)

    def test_durations_produce_correct_frame_size(self, mock_vad):
        detector = sd.SpeechDetector(samplerate=8000, frame_duration_ms=10, vad_backend=mock_vad)
        assert detector.frame_size == 80

        detector = sd.SpeechDetector(samplerate=16000, frame_duration_ms=20, vad_backend=mock_vad)
        assert detector.frame_size == 320

        detector = sd.SpeechDetector(samplerate=32000, frame_duration_ms=30, vad_backend=mock_vad)
        assert detector.frame_size == 960


# ---------------------------------------------------------------------------
# Raw VAD decision
# ---------------------------------------------------------------------------


class TestSpeechDetectorRawDecision:
    def test_is_speech_true(self, mock_vad):
        mock_vad.is_speech.return_value = True
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        frame = np.zeros(480, dtype=np.int16)
        assert detector.is_speech(frame) is True

    def test_is_speech_false(self, mock_vad):
        mock_vad.is_speech.return_value = False
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        frame = np.zeros(480, dtype=np.int16)
        assert detector.is_speech(frame) is False

    def test_is_speech_wrong_size_raises(self, mock_vad):
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        with pytest.raises(ValueError, match="Frame size"):
            detector.is_speech(np.zeros(100, dtype=np.int16))

    def test_is_speech_wrong_dtype_raises(self, mock_vad):
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        with pytest.raises(TypeError, match="int16"):
            detector.is_speech(np.zeros(480, dtype=np.float32))

    def test_is_speech_passes_bytes_to_webrtcvad(self, mock_vad):
        mock_vad.is_speech.return_value = True
        detector = sd.SpeechDetector(samplerate=16000, vad_backend=mock_vad)
        frame = np.ones(480, dtype=np.int16)
        detector.is_speech(frame)

        args = mock_vad.is_speech.call_args
        assert args[0][1] == 16000
        assert isinstance(args[0][0], bytes)
        assert len(args[0][0]) == 480 * 2  # 16-bit = 2 bytes/sample


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class TestSpeechDetectorStateMachine:
    def test_speech_start_after_three_frames(self, mock_vad):
        mock_vad.is_speech.return_value = True
        detector = sd.SpeechDetector(vad_backend=mock_vad)

        assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SILENCE
        assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SILENCE
        event = detector.process_frame(np.zeros(480, dtype=np.int16))
        assert event == sd.VADEvent.SPEECH_START
        assert detector.in_speech is True

    def test_speech_end_after_ten_silence_frames(self, mock_vad):
        # Pattern: 4 speech frames (start + 1 extra), then 10 silence frames
        returns = [True] * 4 + [False] * 10
        mock_vad.is_speech.side_effect = returns
        detector = sd.SpeechDetector(vad_backend=mock_vad)

        # First 3 → SPEECH_START
        detector.process_frame(np.zeros(480, dtype=np.int16))
        detector.process_frame(np.zeros(480, dtype=np.int16))
        assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SPEECH_START

        # 4th speech frame → still in speech (None)
        assert detector.process_frame(np.zeros(480, dtype=np.int16)) is None

        # 9 silence frames → still in speech (None)
        for _ in range(9):
            assert detector.process_frame(np.zeros(480, dtype=np.int16)) is None

        # 10th silence frame → SPEECH_END
        assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SPEECH_END
        assert detector.in_speech is False

    def test_silence_returned_when_not_in_speech(self, mock_vad):
        mock_vad.is_speech.return_value = False
        detector = sd.SpeechDetector(vad_backend=mock_vad)

        for _ in range(5):
            assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SILENCE

    def test_silence_resets_speech_counter(self, mock_vad):
        """A single silence frame between speech frames resets the counter."""
        returns = [True, True, False, True, True, True]
        mock_vad.is_speech.side_effect = returns
        detector = sd.SpeechDetector(vad_backend=mock_vad)

        detector.process_frame(np.zeros(480, dtype=np.int16))  # 1 speech
        detector.process_frame(np.zeros(480, dtype=np.int16))  # 2 speech
        detector.process_frame(np.zeros(480, dtype=np.int16))  # silence → reset
        detector.process_frame(np.zeros(480, dtype=np.int16))  # 1 speech
        detector.process_frame(np.zeros(480, dtype=np.int16))  # 2 speech
        event = detector.process_frame(np.zeros(480, dtype=np.int16))  # 3 speech → start
        assert event == sd.VADEvent.SPEECH_START

    def test_buffer_accumulates_during_speech(self, mock_vad):
        returns = [True] * 6 + [False] * 10
        mock_vad.is_speech.side_effect = returns
        detector = sd.SpeechDetector(vad_backend=mock_vad)

        for _ in range(16):
            detector.process_frame(np.ones(480, dtype=np.int16))

        buffer = detector.speech_buffer
        # SPEECH_START on frame 3 (index 2), SPEECH_END on frame 16 (index 15)
        # Buffer includes the triggering silence frame, so frames 2-15 inclusive = 14 frames
        assert len(buffer) == 14 * 480
        assert buffer.dtype == np.int16


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestSpeechDetectorReset:
    def test_reset_clears_state(self, mock_vad):
        mock_vad.is_speech.return_value = True
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        detector.process_frame(np.zeros(480, dtype=np.int16))
        detector.process_frame(np.zeros(480, dtype=np.int16))
        detector.process_frame(np.zeros(480, dtype=np.int16))  # SPEECH_START

        detector.reset()
        assert detector.in_speech is False
        assert len(detector.speech_buffer) == 0

    def test_reset_allows_fresh_start(self, mock_vad):
        mock_vad.is_speech.return_value = True
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        detector.process_frame(np.zeros(480, dtype=np.int16))
        detector.process_frame(np.zeros(480, dtype=np.int16))
        detector.process_frame(np.zeros(480, dtype=np.int16))
        detector.reset()

        # Need 3 fresh speech frames to trigger again
        assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SILENCE
        assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SILENCE
        assert detector.process_frame(np.zeros(480, dtype=np.int16)) == sd.VADEvent.SPEECH_START


# ---------------------------------------------------------------------------
# Buffer retrieval
# ---------------------------------------------------------------------------


class TestSpeechDetectorBuffer:
    def test_buffer_empty_before_speech(self, mock_vad):
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        assert len(detector.speech_buffer) == 0

    def test_buffer_available_after_speech_end(self, mock_vad):
        returns = [True] * 5 + [False] * 10
        mock_vad.is_speech.side_effect = returns
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        for _ in range(15):
            detector.process_frame(np.zeros(480, dtype=np.int16))
        assert len(detector.speech_buffer) > 0

    def test_buffer_cleared_on_next_speech_start(self, mock_vad):
        returns = [True] * 5 + [False] * 10 + [True] * 3
        mock_vad.is_speech.side_effect = returns
        detector = sd.SpeechDetector(vad_backend=mock_vad)
        for _ in range(15):
            detector.process_frame(np.zeros(480, dtype=np.int16))
        old_len = len(detector.speech_buffer)
        assert old_len > 0

        # Next speech start clears buffer and starts with the triggering frame only
        for _ in range(3):
            detector.process_frame(np.zeros(480, dtype=np.int16))
        assert len(detector.speech_buffer) == 1 * 480


# ---------------------------------------------------------------------------
# Synthetic audio integration (no mocking — validates wrapper behaviour)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sd.webrtcvad is None, reason="webrtcvad not installed")
class TestSpeechDetectorSyntheticAudio:
    def test_silence_classified_as_silence(self):
        """A frame of pure zeros should not be speech."""
        detector = sd.SpeechDetector()
        frame = np.zeros(480, dtype=np.int16)
        assert not detector.is_speech(frame)

    def test_sine_wave_may_be_classified_as_speech(self):
        """A strong sine wave is often classified as speech by WebRTC VAD."""
        detector = sd.SpeechDetector()
        t = np.linspace(0, 0.03, 480, endpoint=False)
        frame = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        # We don't assert the result — this test documents behaviour
        detector.is_speech(frame)
