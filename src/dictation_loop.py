"""Orchestrates the full dictation loop: audio → VAD → transcribe → paste.

:class:`DictationLoop` is a QObject that manages the state machine and
wires together AudioCapture, SpeechDetector, Transcriber, and PasteController.
Audio buffers are strictly in-memory and cleared after each utterance.

Thread safety
-------------
Audio callbacks run on a consumer thread (see :class:`AudioCapture`).
All Qt operations (state changes, signals, timers, UI updates) must
happen on the main Qt thread.  Speech-end and transcription-result
signals marshal work from background threads onto the main thread.
"""

from __future__ import annotations

import gc
import logging
import threading
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, Signal, QTimer

if TYPE_CHECKING:
    from settings_store import SettingsStore
    from diagnostics import Diagnostics
    from audio_capture import AudioCapture
    from speech_detector import SpeechDetector, VADEvent
    from transcriber import TranscriberInterface
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
    _schedule_reset_signal = Signal(int)
    _speech_end_signal = Signal(object)
    _transcription_result_signal = Signal(str)
    _transcription_error_signal = Signal(str)

    def __init__(
        self,
        settings: "SettingsStore",
        audio_capture: "AudioCapture",
        speech_detector: "SpeechDetector",
        transcriber: "TranscriberInterface",
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
        self._continuous_mode: bool = False
        self._auto_reset_timer: QTimer = QTimer(self)
        self._auto_reset_timer.setSingleShot(True)
        self._auto_reset_timer.timeout.connect(self._auto_reset_to_idle)
        self._transcribe_thread: threading.Thread | None = None
        self._schedule_reset_signal.connect(self._auto_reset_timer.start)
        self._speech_end_signal.connect(self._handle_speech_end)
        self._transcription_result_signal.connect(self._handle_transcription_result)
        self._transcription_error_signal.connect(self._handle_transcription_error)

    # ------------------------------------------------------------------
    # Transcriber routing
    # ------------------------------------------------------------------

    def set_active_transcriber(self, transcriber: "TranscriberInterface") -> None:
        """Switch the active transcriber at runtime.

        Parameters
        ----------
        transcriber:
            Any ``TranscriberInterface`` implementation (local or cloud).
        """
        self._transcriber = transcriber

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
        """Begin a dictation session (auto-stop on silence).

        Sets LISTENING, starts audio capture, and feeds the VAD.
        On SPEECH_END the capture stops, transcription runs, and the
        result is pasted.
        """
        if self._state is DictationState.LISTENING:
            return
        if self._state is DictationState.PROCESSING:
            return

        self._continuous_mode = False
        self._set_state(DictationState.LISTENING)
        self._audio_buffer = []
        self._speech_detector.reset()

        try:
            self._audio_capture.start(self._on_audio_block)
        except Exception as exc:
            logger.exception("Failed to start audio capture: %s", exc)
            self._handle_error("no_microphone", "No microphone detected.")
            return

    def start_continuous(self) -> None:
        """Begin continuous dictation (manual stop only).

        Like :meth:`start` but ignores VAD speech-end events.
        Recording continues until :meth:`stop` is called.
        """
        if self._state is DictationState.LISTENING:
            return
        if self._state is DictationState.PROCESSING:
            return

        self._continuous_mode = True
        self._set_state(DictationState.LISTENING, "Continuous — press Stop when done")
        self._audio_buffer = []
        self._speech_detector.reset()

        try:
            self._audio_capture.start(self._on_audio_block)
        except Exception as exc:
            logger.exception("Failed to start audio capture: %s", exc)
            self._handle_error("no_microphone", "No microphone detected.")
            return

    def stop(self) -> None:
        """Stop the current session.

        If audio has been captured, triggers transcription.
        If no audio was captured, returns to IDLE.
        """
        if self._state is DictationState.IDLE:
            return

        self._audio_capture.stop()

        if self._audio_buffer:
            audio_buffer = list(self._audio_buffer)
            self._audio_buffer = []
            self._continuous_mode = False
            self._speech_detector.reset()
            self._speech_end_signal.emit(audio_buffer)
            return

        self._audio_buffer = []
        self._continuous_mode = False
        self._speech_detector.reset()
        self._auto_reset_timer.stop()
        self._set_state(DictationState.IDLE)
        gc.collect()

    def toggle(self) -> None:
        """Toggle between IDLE and LISTENING/PROCESSING."""
        if self._state is DictationState.IDLE:
            self.start()
        else:
            self.stop()

    # ------------------------------------------------------------------
    # Audio callback (runs on AudioCapture consumer thread)
    # ------------------------------------------------------------------

    def _on_audio_block(self, block: np.ndarray) -> None:
        """Called by AudioCapture for each audio block.

        Runs on the AudioCapture consumer thread.  VAD is done here,
        but any Qt operations (state changes, signals on QObjects,
        UI updates) must be deferred to the main thread via signals.
        """
        # In continuous mode, always buffer audio regardless of VAD
        if self._continuous_mode:
            self._audio_buffer.append(block.copy())
            return

        try:
            event = self._speech_detector.process_frame(block)
        except Exception:
            logger.exception("VAD error on frame")
            return

        if event is None:
            if self._speech_detector.in_speech:
                self._audio_buffer.append(block.copy())
            return

        if event.value == "speech_start":
            self._audio_buffer = [block.copy()]
            self._log_event("speech_started")
            return

        if event.value == "speech_end":
            self._audio_buffer.append(block.copy())
            self._audio_capture.stop()
            audio_buffer = list(self._audio_buffer)
            self._audio_buffer = []
            self._speech_end_signal.emit(audio_buffer)
            return

    # ------------------------------------------------------------------
    # Speech-end handler (runs on main Qt thread via signal)
    # ------------------------------------------------------------------

    def _handle_speech_end(self, audio_buffer: object) -> None:
        """Handle end of speech on the main Qt thread.

        Connected to :attr:`_speech_end_signal` so it always executes
        on the thread that owns this QObject (the main Qt thread).
        """
        buf: list[np.ndarray] = audio_buffer  # type: ignore[assignment]

        self._set_state(DictationState.PROCESSING)

        if not buf:
            self._handle_error("transcription", "Transcription failed. Try again.")
            return

        audio = np.concatenate(buf)
        language = getattr(self._settings, "language", "auto") or "auto"

        def _transcribe_worker() -> None:
            try:
                text = self._transcriber.transcribe(audio, sample_rate=16000, language=language)
                if self._post_processor is not None:
                    text = self._post_processor.normalize(text)
                if not text:
                    self._transcription_result_signal.emit("")
                else:
                    self._transcription_result_signal.emit(text)
            except Exception as exc:
                logger.exception("Transcription failed: %s", exc)
                self._transcription_error_signal.emit(
                    "Transcription failed. Try again."
                )

        thread = threading.Thread(target=_transcribe_worker, daemon=True)
        self._transcribe_thread = thread
        thread.start()

    # ------------------------------------------------------------------
    # Transcription result handlers (main Qt thread via signal)
    # ------------------------------------------------------------------

    def _handle_transcription_result(self, text: str) -> None:
        """Handle successful transcription on the main Qt thread."""
        if self._state is not DictationState.PROCESSING:
            logger.debug("Discarding transcription result (state=%s)", self._state.value)
            return

        if not text:
            self._set_state(DictationState.READY, "No speech detected")
            self._schedule_reset()
            return

        if self._settings.paste_mode == "confirmation":
            self._set_state(DictationState.READY, "Review before paste")
            self.transcription_ready.emit(text)
            return

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
        gc.collect()

    def _handle_transcription_error(self, message: str) -> None:
        """Handle transcription failure on the main Qt thread."""
        if self._state is not DictationState.PROCESSING:
            logger.debug("Discarding transcription error (state=%s)", self._state.value)
            return
        self._handle_error("transcription", message)

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
        self._schedule_reset(delay_ms=4000)

    def _schedule_reset(self, delay_ms: int = 2000) -> None:
        """Schedule automatic return to IDLE after *delay_ms*."""
        self._schedule_reset_signal.emit(delay_ms)

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
