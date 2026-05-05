"""Integration tests for AudioCapture + SpeechDetector.

These tests verify that audio blocks produced by AudioCapture can be
fed directly into SpeechDetector and that the expected VAD events are
produced at the correct temporal positions.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from audio_capture import AudioCapture
from speech_detector import SpeechDetector, VADEvent


# ---------------------------------------------------------------------------
# Direct block feeding (no threading)
# ---------------------------------------------------------------------------


class TestDirectBlockFeeding:
    def test_synthetic_audio_produces_expected_events(self, mock_webrtcvad, sample_audio_16khz):
        """Feed 30 ms blocks directly to SpeechDetector and verify events."""
        blocksize = 480
        num_blocks = len(sample_audio_16khz) // blocksize

        # Segment pattern: 10 blocks silence, 10 speech, 10 silence, 10 speech, 10 silence
        is_speech_pattern = (
            [False] * 10
            + [True] * 10
            + [False] * 10
            + [True] * 10
            + [False] * 10
        )
        mock_webrtcvad.is_speech.side_effect = is_speech_pattern[:num_blocks]

        detector = SpeechDetector(aggressiveness=1)
        events = []

        for i in range(num_blocks):
            block = sample_audio_16khz[i * blocksize : (i + 1) * blocksize]
            event = detector.process_frame(block)
            if event is not None:
                events.append((i, event))

        # SPEECH_START after 3 consecutive speech frames (blocks 10,11,12)
        assert events[0] == (12, VADEvent.SPEECH_START)
        # SPEECH_END after 10 consecutive silence frames (blocks 20..29)
        assert events[1] == (29, VADEvent.SPEECH_END)
        # Second speech start (blocks 30,31,32)
        assert events[2] == (32, VADEvent.SPEECH_START)
        # Second speech end (blocks 40..49)
        assert events[3] == (49, VADEvent.SPEECH_END)

    def test_buffer_contains_correct_number_of_frames(self, mock_webrtcvad, sample_audio_16khz):
        """The accumulated buffer should contain every speech frame between start and end."""
        blocksize = 480
        num_blocks = len(sample_audio_16khz) // blocksize

        is_speech_pattern = (
            [False] * 10
            + [True] * 10
            + [False] * 10
            + [True] * 10
            + [False] * 10
        )
        mock_webrtcvad.is_speech.side_effect = is_speech_pattern[:num_blocks]

        detector = SpeechDetector(aggressiveness=1)
        for i in range(num_blocks):
            block = sample_audio_16khz[i * blocksize : (i + 1) * blocksize]
            detector.process_frame(block)

        buffer = detector.speech_buffer
        # First utterance: frames 12-19 inclusive = 8 frames = 3840 samples
        # Second utterance: frames 32-39 inclusive = 8 frames = 3840 samples
        # Total = 7680 samples
        assert len(buffer) == 7680


# ---------------------------------------------------------------------------
# Full pipeline: AudioCapture thread → SpeechDetector
# ---------------------------------------------------------------------------


class TestAudioCaptureToVadPipeline:
    def test_capture_callback_feeds_detector(self, mock_sounddevice, mock_webrtcvad, sample_audio_16khz):
        """AudioCapture's callback mechanism delivers blocks that SpeechDetector can process."""
        blocksize = 480
        num_blocks = len(sample_audio_16khz) // blocksize

        is_speech_pattern = (
            [False] * 10
            + [True] * 10
            + [False] * 10
            + [True] * 10
            + [False] * 10
        )
        mock_webrtcvad.is_speech.side_effect = is_speech_pattern[:num_blocks]

        detector = SpeechDetector(aggressiveness=1)
        events = []

        def capture_callback(block: np.ndarray) -> None:
            event = detector.process_frame(block)
            if event is not None:
                events.append(event)

        cap = AudioCapture()
        cap.start(capture_callback)

        try:
            for i in range(num_blocks):
                block = sample_audio_16khz[i * blocksize : (i + 1) * blocksize]
                # Simulate PortAudio callback injection
                cap._stream_callback(block.reshape(-1, 1), blocksize, None, None)
            # Allow consumer thread to drain the queue
            time.sleep(0.15)
        finally:
            cap.stop()

        assert VADEvent.SPEECH_START in events
        assert VADEvent.SPEECH_END in events
        # Two utterances = two of each event
        assert events.count(VADEvent.SPEECH_START) == 2
        assert events.count(VADEvent.SPEECH_END) == 2

    def test_capture_format_matches_vad_requirements(self, mock_sounddevice, mock_webrtcvad):
        """AudioCapture output shape/dtype must be compatible with SpeechDetector input."""
        cap = AudioCapture(samplerate=16000, block_duration_ms=30)
        detector = SpeechDetector(samplerate=16000, frame_duration_ms=30)

        assert cap.blocksize == detector.frame_size
        assert cap.blocksize == 480

        received = []

        def capture_callback(block: np.ndarray) -> None:
            assert block.ndim == 1
            assert block.dtype == np.int16
            assert len(block) == detector.frame_size
            received.append(block)

        cap.start(capture_callback)
        try:
            fake = np.zeros((cap.blocksize, 1), dtype=np.int16)
            cap._stream_callback(fake, cap.blocksize, None, None)
            time.sleep(0.05)
        finally:
            cap.stop()

        assert len(received) == 1
