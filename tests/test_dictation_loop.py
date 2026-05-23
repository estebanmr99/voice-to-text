"""Tests for dictation_loop.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from dictation_loop import DictationLoop, DictationState
from transcriber import TranscriberInterface


def _wait_for_transcription(loop: DictationLoop, qapp, timeout: float = 5.0) -> None:
    """Wait for the background transcription thread to finish and process Qt events."""
    thread = loop._transcribe_thread
    if thread is not None:
        thread.join(timeout=timeout)
    qapp.processEvents()


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
        _wait_for_transcription(loop, qapp)

        assert loop.state is DictationState.READY

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
        _wait_for_transcription(loop, qapp)

        mock_deps["transcriber"].transcribe.assert_called_once()
        mock_deps["paste_controller"].paste.assert_called_once_with("hello world")
        assert received == ["hello world"]

    def test_empty_audio_goes_ready_no_paste(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = ""

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        mock_deps["paste_controller"].paste.assert_not_called()
        assert loop.state is DictationState.READY

    def test_confirmation_mode_emits_transcription_ready(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        mock_deps["settings"].paste_mode = "confirmation"
        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "raw text"

        received = []
        loop.transcription_ready.connect(lambda t: received.append(t))
        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        assert received == ["raw text"]
        assert loop.state is DictationState.READY

    def test_confirmation_mode_does_not_paste_automatically(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        mock_deps["settings"].paste_mode = "confirmation"
        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "raw text"

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        mock_deps["paste_controller"].paste.assert_not_called()

    def test_confirm_paste_uses_edited_text(self, loop, mock_deps):
        loop.confirm_paste("edited text")
        mock_deps["paste_controller"].paste.assert_called_once_with("edited text")
        assert loop.state is DictationState.READY

    def test_cancel_paste_returns_idle(self, loop):
        loop.cancel_paste()
        assert loop.state is DictationState.IDLE

    def test_immediate_mode_still_pastes(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        mock_deps["settings"].paste_mode = "immediate"
        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "hello world"
        mock_deps["paste_controller"].paste.return_value = True

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        mock_deps["paste_controller"].paste.assert_called_once_with("hello world")


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
        _wait_for_transcription(loop, qapp)
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
        _wait_for_transcription(loop, qapp)
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
        _wait_for_transcription(loop, qapp)

        assert loop.state is DictationState.ERROR


class TestAutoReset:
    def test_ready_auto_resets(self, loop, mock_deps, qapp):
        from speech_detector import VADEvent

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = ""

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)
        assert loop.state is DictationState.READY

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


class TestPostProcessorIntegration:
    """Tests for DictationLoop with PostProcessor normalization."""

    @pytest.fixture
    def pp_mock_deps(self):
        """Return mock dependencies with a mock PostProcessor."""
        settings = MagicMock()
        settings.paste_mode = "immediate"

        audio_capture = MagicMock()
        speech_detector = MagicMock()
        transcriber = MagicMock()
        paste_controller = MagicMock()
        diagnostics = MagicMock()
        post_processor = MagicMock()
        post_processor.normalize.side_effect = lambda t: t.upper()

        return {
            "settings": settings,
            "audio_capture": audio_capture,
            "speech_detector": speech_detector,
            "transcriber": transcriber,
            "paste_controller": paste_controller,
            "diagnostics": diagnostics,
            "post_processor": post_processor,
        }

    @pytest.fixture
    def pp_loop(self, pp_mock_deps, qapp):
        return DictationLoop(
            settings=pp_mock_deps["settings"],
            audio_capture=pp_mock_deps["audio_capture"],
            speech_detector=pp_mock_deps["speech_detector"],
            transcriber=pp_mock_deps["transcriber"],
            paste_controller=pp_mock_deps["paste_controller"],
            diagnostics=pp_mock_deps["diagnostics"],
            post_processor=pp_mock_deps["post_processor"],
        )

    def test_normalizes_before_paste_immediate(self, pp_loop, pp_mock_deps, qapp):
        """PostProcessor normalizes text before pasting in immediate mode."""
        from speech_detector import VADEvent

        pp_loop.start()
        frame = np.zeros(480, dtype=np.int16)
        pp_mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        pp_mock_deps["transcriber"].transcribe.return_value = "mergear el pr"
        pp_mock_deps["post_processor"].normalize.side_effect = None
        pp_mock_deps["post_processor"].normalize.return_value = "mergear el PR"
        pp_mock_deps["paste_controller"].paste.return_value = True

        pp_loop._on_audio_block(frame)
        _wait_for_transcription(pp_loop, qapp)

        pp_mock_deps["post_processor"].normalize.assert_called_once_with("mergear el pr")
        pp_mock_deps["paste_controller"].paste.assert_called_once_with("mergear el PR")

    def test_normalizes_before_confirmation_emit(self, pp_loop, pp_mock_deps, qapp):
        """PostProcessor normalizes text in confirmation mode too."""
        from speech_detector import VADEvent

        pp_mock_deps["settings"].paste_mode = "confirmation"
        pp_mock_deps["post_processor"].normalize.side_effect = None
        pp_mock_deps["post_processor"].normalize.return_value = "mergear el PR"

        pp_loop.start()
        frame = np.zeros(480, dtype=np.int16)
        pp_mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        pp_mock_deps["transcriber"].transcribe.return_value = "mergear el pr"

        received = []
        pp_loop.transcription_ready.connect(lambda t: received.append(t))
        pp_loop._on_audio_block(frame)
        _wait_for_transcription(pp_loop, qapp)

        assert received == ["mergear el PR"]
        pp_mock_deps["post_processor"].normalize.assert_called_once_with("mergear el pr")

    def test_none_post_processor_falls_back_to_raw(self, mock_deps, qapp):
        """When post_processor=None, raw text passes through unchanged."""
        from speech_detector import VADEvent

        loop = DictationLoop(
            settings=mock_deps["settings"],
            audio_capture=mock_deps["audio_capture"],
            speech_detector=mock_deps["speech_detector"],
            transcriber=mock_deps["transcriber"],
            paste_controller=mock_deps["paste_controller"],
            diagnostics=mock_deps["diagnostics"],
            post_processor=None,
        )

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "mergear el pr"
        mock_deps["paste_controller"].paste.return_value = True

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        mock_deps["paste_controller"].paste.assert_called_once_with("mergear el pr")

    def test_normalize_called_once_per_cycle(self, pp_loop, pp_mock_deps, qapp):
        """PostProcessor.normalize is called exactly once per transcription cycle."""
        from speech_detector import VADEvent

        pp_mock_deps["post_processor"].normalize.side_effect = None
        pp_mock_deps["post_processor"].normalize.return_value = "normalized"
        pp_mock_deps["paste_controller"].paste.return_value = True

        pp_loop.start()
        frame = np.zeros(480, dtype=np.int16)
        pp_mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        pp_mock_deps["transcriber"].transcribe.return_value = "raw text"

        pp_loop._on_audio_block(frame)
        _wait_for_transcription(pp_loop, qapp)

        assert pp_mock_deps["post_processor"].normalize.call_count == 1

    def test_normalize_not_called_when_no_post_processor(self, mock_deps, qapp):
        """When no PostProcessor is configured, normalize is never called."""
        from speech_detector import VADEvent

        loop = DictationLoop(
            settings=mock_deps["settings"],
            audio_capture=mock_deps["audio_capture"],
            speech_detector=mock_deps["speech_detector"],
            transcriber=mock_deps["transcriber"],
            paste_controller=mock_deps["paste_controller"],
            diagnostics=mock_deps["diagnostics"],
            post_processor=None,
        )

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END
        mock_deps["transcriber"].transcribe.return_value = "raw text"
        mock_deps["paste_controller"].paste.return_value = True

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        mock_deps["paste_controller"].paste.assert_called_once_with("raw text")


class TestTranscriberRouting:
    """Tests for DictationLoop transcriber routing via set_active_transcriber()."""

    def test_set_active_transcriber_switches_transcriber(self, loop, mock_deps, qapp):
        """set_active_transcriber() replaces the internal transcriber and is used."""
        from speech_detector import VADEvent

        new_transcriber = MagicMock()
        new_transcriber.transcribe.return_value = "switched transcriber"
        mock_deps["paste_controller"].paste.return_value = True

        loop.set_active_transcriber(new_transcriber)
        assert loop._transcriber is new_transcriber

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        new_transcriber.transcribe.assert_called_once()
        mock_deps["paste_controller"].paste.assert_called_once_with("switched transcriber")

    def test_transcriber_interface_contract(self, loop, mock_deps, qapp):
        """Any TranscriberInterface implementation works as the transcriber."""
        from speech_detector import VADEvent

        interface_transcriber = MagicMock(spec=TranscriberInterface)
        interface_transcriber.transcribe.return_value = "interface transcription"
        mock_deps["paste_controller"].paste.return_value = True

        loop.set_active_transcriber(interface_transcriber)
        assert loop._transcriber is interface_transcriber

        loop.start()
        frame = np.zeros(480, dtype=np.int16)
        mock_deps["speech_detector"].process_frame.return_value = VADEvent.SPEECH_END

        loop._on_audio_block(frame)
        _wait_for_transcription(loop, qapp)

        interface_transcriber.transcribe.assert_called_once()
        mock_deps["paste_controller"].paste.assert_called_once_with(
            "interface transcription"
        )