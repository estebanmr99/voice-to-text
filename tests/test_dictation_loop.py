"""Tests for dictation_loop.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from dictation_loop import DictationLoop, DictationState


@pytest.fixture
def mock_deps():
    """Return mock dependencies for DictationLoop."""
    settings = MagicMock()
    settings.paste_mode = "immediate"

    audio_capture = MagicMock()
    speech_detector = MagicMock()
    transcriber = MagicMock()
    paste_controller = MagicMock()
    diagnostics = MagicMock()

    return {
        "settings": settings,
        "audio_capture": audio_capture,
        "speech_detector": speech_detector,
        "transcriber": transcriber,
        "paste_controller": paste_controller,
        "diagnostics": diagnostics,
    }


@pytest.fixture
def loop(mock_deps, qapp):
    return DictationLoop(
        settings=mock_deps["settings"],
        audio_capture=mock_deps["audio_capture"],
        speech_detector=mock_deps["speech_detector"],
        transcriber=mock_deps["transcriber"],
        paste_controller=mock_deps["paste_controller"],
        diagnostics=mock_deps["diagnostics"],
    )


class TestStateMachine:
    def test_initial_state(self, loop):
        assert loop.state is DictationState.IDLE

    def test_start_sets_listening(self, loop, mock_deps):
        loop.start()
        assert loop.state is DictationState.LISTENING
        mock_deps["audio_capture"].start.assert_called_once()

    def test_stop_returns_idle(self, loop, mock_deps):
        loop.start()
        loop.stop()
        assert loop.state is DictationState.IDLE
        mock_deps["audio_capture"].stop.assert_called_once()

    def test_toggle_start(self, loop, mock_deps):
        loop.toggle()
        assert loop.state is DictationState.LISTENING

    def test_toggle_stop(self, loop, mock_deps):
        loop.toggle()
        loop.toggle()
        assert loop.state is DictationState.IDLE

    def test_start_while_listening_is_noop(self, loop, mock_deps):
        loop.start()
        loop.start()
        assert loop.state is DictationState.LISTENING
        assert mock_deps["audio_capture"].start.call_count == 1


class TestAudioFlow:
    def test_speech_start_accumulates_buffer(self, loop, mock_deps):
        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].in_speech = True
        mock_deps["speech_detector"].process_frame.return_value = None

        loop._on_audio_block(frame)
        assert len(loop._audio_buffer) == 1

    def test_speech_end_triggers_transcription(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "hello world"
        mock_deps["paste_controller"].paste.return_value = True

        loop._on_audio_block(frame)
        assert loop.state in (DictationState.READY, DictationState.PROCESSING)

    def test_successful_transcription_pastes_text(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "hello world"
        mock_deps["paste_controller"].paste.return_value = True

        received = []
        loop.text_pasted.connect(lambda t: received.append(t))

        loop._on_audio_block(frame)
        # Wait for timer in tests — directly process if needed
        if loop._auto_reset_timer is not None:
            loop._auto_reset_timer.stop()
        loop._auto_reset_to_idle()

        mock_deps["transcriber"].transcribe.assert_called_once()
        mock_deps["paste_controller"].paste.assert_called_once()
        assert received == ["hello world"]

    def test_empty_audio_goes_ready_no_paste(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = ""

        loop._on_audio_block(frame)
        if loop._auto_reset_timer is not None:
            loop._auto_reset_timer.stop()

        mock_deps["paste_controller"].paste.assert_not_called()


class TestErrorHandling:
    def test_audio_capture_failure(self, loop, mock_deps):
        mock_deps["audio_capture"].start.side_effect = RuntimeError("no device")

        received = []
        loop.error_occurred.connect(lambda e: received.append(e))

        loop.start()
        assert loop.state is DictationState.ERROR
        assert received == ["No microphone detected."]

    def test_transcription_failure(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.side_effect = RuntimeError("model missing")

        received = []
        loop.error_occurred.connect(lambda e: received.append(e))

        loop._on_audio_block(frame)
        if loop._auto_reset_timer is not None:
            loop._auto_reset_timer.stop()

        assert loop.state is DictationState.ERROR
        assert received == ["Transcription failed. Try again."]

    def test_paste_failure(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "hello"
        mock_deps["paste_controller"].paste.return_value = False

        received = []
        loop.error_occurred.connect(lambda e: received.append(e))

        loop._on_audio_block(frame)
        if loop._auto_reset_timer is not None:
            loop._auto_reset_timer.stop()

        assert loop.state is DictationState.ERROR
        assert received == ["Could not paste. Clipboard may be locked."]

    def test_missing_model_error_message(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.side_effect = RuntimeError("model missing")

        loop._on_audio_block(frame)
        assert loop.state is DictationState.ERROR


class TestAutoReset:
    def test_ready_auto_resets(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = ""

        loop._on_audio_block(frame)
        assert loop.state is DictationState.READY
        # Simulate timer timeout
        loop._auto_reset_to_idle()
        assert loop.state is DictationState.IDLE

    def test_buffer_cleared_after_transcription(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = ""

        loop._audio_buffer = [frame]
        loop._on_audio_block(frame)
        assert len(loop._audio_buffer) == 0
