"""Orchestrates the full dictation loop: audio → VAD → transcribe → paste.

:class:`DictationLoop` is a QObject that manages the state machine and
wires together AudioCapture, SpeechDetector, Transcriber, and PasteController.
Audio buffers are strictly in-memory and cleared after each utterance.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, Signal, QTimer

if TYPE_CHECKING:
    from settings_store import SettingsStore
    from diagnostics import Diagnostics
    from audio_capture import AudioCapture
    from speech_detector import SpeechDetector, VADEvent
    from transcriber import Transcriber
    from paste_controller import PasteController
    from post_processor import PostProcessor

logger = logging.getLogger(__name__)


class DictationState(Enum):
    """States of the dictation state machine."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class DictationLoop(QObject):
    """Full dictation orchestrator with state machine.

    Signals
    -------
    state_changed(state: DictationState, message: str)
        Emitted on every state transition.
    text_pasted(text: str)
        Emitted after a successful paste (text is redacted/omitted for privacy).
    error_occurred(error: str)
        Emitted on unrecoverable errors with a human-readable message.
    """

    state_changed = Signal(object, str)
    text_pasted = Signal(str)
    transcription_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        settings: "SettingsStore",
        audio_capture: "AudioCapture",
        speech_detector: "SpeechDetector",
        transcriber: "Transcriber",
        paste_controller: "PasteController",
        diagnostics: "Diagnostics | None" = None,
        post_processor: "PostProcessor | None" = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._audio_capture = audio_capture
        self._speech_detector = speech_detector
        self._transcriber = transcriber
        self._paste_controller = paste_controller
        self._diagnostics = diagnostics
        self._post_processor = post_processor

        self._state = DictationState.IDLE
        self._audio_buffer: list[np.ndarray] = []
        self._auto_reset_timer: QTimer = QTimer(self)
        self._auto_reset_timer.setSingleShot(True)
        self._auto_reset_timer.timeout.connect(self._auto_reset_to_idle)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    @property
    def state(self) -> DictationState:
        return self._state

    def _set_state(self, state: DictationState, message: str = "") -> None:
        self._state = state
        self.state_changed.emit(state, message)
        self._log_event(f"state_{state.value}", message=message)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin a dictation session.

        Sets LISTENING, starts audio capture, and feeds the VAD.
        On SPEECH_END the capture stops, transcription runs, and the
        result is pasted.
        """
        if self._state is DictationState.LISTENING:
            return
        if self._state is DictationState.PROCESSING:
            return

        self._set_state(DictationState.LISTENING)
        self._audio_buffer = []
        self._speech_detector.reset()

        try:
            self._audio_capture.start(self._on_audio_block)
        except Exception as exc:
            logger.exception("Failed to start audio capture: %s", exc)
            self._handle_error("no_microphone", "No microphone detected.")
            return

    def stop(self) -> None:
        """Cancel the current session and return to IDLE."""
        if self._state is DictationState.IDLE:
            return

        self._audio_capture.stop()
        self._audio_buffer = []
        self._speech_detector.reset()
        self._auto_reset_timer.stop()
        self._set_state(DictationState.IDLE)

    def toggle(self) -> None:
        """Toggle between IDLE and LISTENING/PROCESSING."""
        if self._state is DictationState.IDLE:
            self.start()
        else:
            self.stop()

    # ------------------------------------------------------------------
    # Audio callback
    # ------------------------------------------------------------------

    def _on_audio_block(self, block: np.ndarray) -> None:
        """Called by AudioCapture for each audio block."""
        try:
            event = self._speech_detector.process_frame(block)
        except Exception:
            logger.exception("VAD error on frame")
            return

        if event is None:
            # Still in speech — accumulate if we have started
            if self._speech_detector.in_speech:
                self._audio_buffer.append(block.copy())
            return

        if event.value == "speech_start":
            self._audio_buffer = [block.copy()]
            self._log_event("speech_started")
            return

        if event.value == "speech_end":
            self._audio_buffer.append(block.copy())
            self._on_speech_end()
            return

        # silence — ignore

    def _on_speech_end(self) -> None:
        """Handle end of speech: stop capture, transcribe, paste."""
        self._audio_capture.stop()
        self._set_state(DictationState.PROCESSING)

        # Concatenate buffer
        if not self._audio_buffer:
            self._handle_error("transcription", "Transcription failed. Try again.")
            return

        audio = np.concatenate(self._audio_buffer)
        self._audio_buffer = []

        try:
            text = self._transcriber.transcribe(audio)
        except Exception as exc:
            logger.exception("Transcription failed: %s", exc)
            self._handle_error("transcription", "Transcription failed. Try again.")
            return

        # Normalize text through PostProcessor if available
        if self._post_processor is not None:
            text = self._post_processor.normalize(text)

        if not text:
            # Silent or very short audio — just go back to idle
            self._set_state(DictationState.READY, "No speech detected")
            self._schedule_reset()
            return

        if self._settings.paste_mode == "confirmation":
            self._set_state(DictationState.READY, "Review before paste")
            self.transcription_ready.emit(text)
            return

        # Paste
        try:
            ok = self._paste_controller.paste(text)
        except Exception as exc:
            logger.exception("Paste failed: %s", exc)
            self._handle_error("paste", "Could not paste. Clipboard may be locked.")
            return

        if not ok:
            self._handle_error("paste", "Could not paste. Clipboard may be locked.")
            return

        self._set_state(DictationState.READY, "Dictation complete")
        self.text_pasted.emit(text)
        self._schedule_reset()

    def confirm_paste(self, text: str) -> None:
        """Paste edited text and transition to READY."""
        try:
            ok = self._paste_controller.paste(text)
        except Exception as exc:
            logger.exception("Paste failed: %s", exc)
            self._handle_error("paste", "Could not paste. Clipboard may be locked.")
            return

        if not ok:
            self._handle_error("paste", "Could not paste. Clipboard may be locked.")
            return

        self._set_state(DictationState.READY, "Dictation complete")
        self.text_pasted.emit(text)
        self._schedule_reset(delay_ms=2000)

    def cancel_paste(self) -> None:
        """Discard transcription and return to IDLE."""
        self._set_state(DictationState.IDLE)

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def _handle_error(self, error_type: str, message: str) -> None:
        """Set ERROR state, log, and schedule reset."""
        self._set_state(DictationState.ERROR, message)
        self.error_occurred.emit(message)
        self._log_event("error", error_type=error_type, message=message)
        # Auto-reset after 4s so user can retry
        self._schedule_reset(delay_ms=4000)

    def _schedule_reset(self, delay_ms: int = 2000) -> None:
        """Schedule automatic return to IDLE after *delay_ms*."""
        self._auto_reset_timer.start(delay_ms)

    def _auto_reset_to_idle(self) -> None:
        self._auto_reset_timer.stop()
        if self._state in (DictationState.READY, DictationState.ERROR):
            self._set_state(DictationState.IDLE)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_event(self, name: str, **kwargs: object) -> None:
        if self._diagnostics is not None:
            try:
                self._diagnostics.event(name, **kwargs)
            except Exception:
                pass
        logger.debug("Event: %s %r", name, kwargs)
