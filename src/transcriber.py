"""Transcription orchestrator with worker process isolation.

:class:`Transcriber` spawns a separate Python process that hosts the
whisper.cpp model.  This keeps the main UI thread responsive and
isolates the large model memory footprint.

Audio data is passed directly as numpy arrays via
:class:`multiprocessing.Queue` — no temporary files are created,
ensuring no retained audio on disk.
"""

from __future__ import annotations

import logging
import multiprocessing
import time
from typing import Any

import numpy as np

from model_manager import ModelInfo, ModelManager
from transcriber_worker import run_worker

logger = logging.getLogger(__name__)

# Minimum audio length (in samples @ 16 kHz) before we bother the model.
_MIN_AUDIO_SAMPLES = 1600  # 100 ms

# Backoff constants for crash recovery
_BACKOFF_INITIAL_SECONDS = 1.0
_BACKOFF_MAX_SECONDS = 30.0
_BACKOFF_MULTIPLIER = 2.0


class TranscriptionError(Exception):
    """Raised when transcription fails or the worker reports an error."""

    pass


class Transcriber:
    """Manages a whisper.cpp worker process for offline transcription.

    Usage::

        mgr = ModelManager()
        transcriber = Transcriber(mgr)
        transcriber.start(mgr.get_default_model())
        text = transcriber.transcribe(audio_array)
        transcriber.stop()
    """

    def __init__(self, model_manager: ModelManager) -> None:
        self._model_manager = model_manager
        self._model_info: ModelInfo | None = None
        self._process: multiprocessing.Process | None = None
        self._audio_queue: multiprocessing.Queue | None = None
        self._result_queue: multiprocessing.Queue | None = None
        self._cancel_event: multiprocessing.Event | None = None
        self._last_error: str | None = None
        self._restart_attempts: int = 0
        self._last_restart_time: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, model_info: ModelInfo) -> bool:
        """Spawn the worker process with *model_info*.

        Returns ``True`` if the process was started successfully (or is
        already running with the same model), ``False`` otherwise.
        """
        if self._process is not None and self._process.is_alive():
            if self._model_info == model_info:
                logger.debug("Worker already running with same model")
                return True
            # Different model — stop first
            self.stop()

        if not self._model_manager.validate_model(model_info):
            self._last_error = (
                f"Model '{model_info.name}' is not valid at {model_info.path}"
            )
            logger.error(self._last_error)
            return False

        self._model_info = model_info
        self._audio_queue = multiprocessing.Queue()
        self._result_queue = multiprocessing.Queue()
        self._cancel_event = multiprocessing.Event()
        self._last_error = None

        n_threads = model_info.parameters.get("n_threads", 4)
        self._process = multiprocessing.Process(
            target=run_worker,
            args=(
                self._audio_queue,
                self._result_queue,
                self._cancel_event,
                str(model_info.path),
                n_threads,
            ),
            name="whisper-worker",
            daemon=True,
        )
        self._process.start()
        self._restart_attempts = 0
        self._last_restart_time = time.time()
        logger.info(
            "Started worker PID %d with model '%s'",
            self._process.pid or -1,
            model_info.name,
        )
        return True

    def stop(self) -> None:
        """Signal cancellation and join the worker process.

        Uses a 5-second timeout; if the process is still alive it is
        forcibly terminated.
        """
        if self._process is None:
            return

        logger.info("Stopping worker PID %d", self._process.pid or -1)

        if self._cancel_event is not None:
            self._cancel_event.set()

        # Send sentinel to unblock the worker if it is waiting on queue
        if self._audio_queue is not None:
            try:
                self._audio_queue.put(None, timeout=1.0)
            except Exception:
                pass

        self._process.join(timeout=5.0)
        if self._process.is_alive():
            logger.warning(
                "Worker PID %d did not terminate in 5s; forcing",
                self._process.pid or -1,
            )
            self._process.terminate()
            self._process.join(timeout=2.0)
            if self._process.is_alive():
                logger.error(
                    "Worker PID %d survived terminate(); killing",
                    self._process.pid or -1,
                )
                self._process.kill()
                self._process.join(timeout=2.0)

        self._process = None
        self._cancel_event = None
        self._audio_queue = None
        self._result_queue = None
        self._model_info = None
        logger.info("Worker stopped")

    def is_running(self) -> bool:
        """Return ``True`` if the worker process is alive."""
        return self._process is not None and self._process.is_alive()

    def get_last_error(self) -> str | None:
        """Return the last error message, if any."""
        return self._last_error

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def transcribe(
        self, audio: np.ndarray, sample_rate: int = 16000, language: str = "auto"
    ) -> str:
        """Send *audio* to the worker and block for the result.

        Parameters
        ----------
        audio:
            1-D numpy array of int16 or float32 samples.
        sample_rate:
            Sample rate in Hz (default 16000 for whisper.cpp).
        language:
            Language code (e.g. "en", "es") or "auto" for detection.
        Returns
        -------
        str:
            Transcribed text, or an empty string for silent/short audio.

        Raises
        ------
        TranscriptionError:
            If the worker is not running, the model is invalid, or the
            worker reports an error.
        """
        # Fast-path: empty or very short audio
        if audio is None or len(audio) < _MIN_AUDIO_SAMPLES:
            return ""

        # Ensure worker is running (with crash recovery / backoff)
        if not self.is_running():
            if not self._try_restart():
                raise TranscriptionError(
                    self._last_error or "Worker not running and cannot restart"
                )

        assert self._audio_queue is not None
        assert self._result_queue is not None

        try:
            self._audio_queue.put((audio, sample_rate, language))
        except Exception as exc:
            self._last_error = f"Failed to send audio to worker: {exc}"
            raise TranscriptionError(self._last_error) from exc

        # Block for result
        try:
            result: dict[str, Any] = self._result_queue.get(timeout=60.0)
        except Exception as exc:
            self._last_error = f"No response from worker: {exc}"
            # Mark worker as crashed so next call tries to restart
            self._process = None
            raise TranscriptionError(self._last_error) from exc

        error = result.get("error")
        if error:
            self._last_error = str(error)
            raise TranscriptionError(self._last_error)

        return str(result.get("text", ""))

    # ------------------------------------------------------------------
    # Crash recovery
    # ------------------------------------------------------------------

    def _try_restart(self) -> bool:
        """Attempt to restart the worker with exponential backoff.

        Returns ``True`` on success, ``False`` on failure.
        """
        if self._model_info is None:
            self._last_error = "No model configured; call start() first"
            return False

        # Enforce backoff
        if self._restart_attempts > 0:
            delay = min(
                _BACKOFF_INITIAL_SECONDS
                * (_BACKOFF_MULTIPLIER ** (self._restart_attempts - 1)),
                _BACKOFF_MAX_SECONDS,
            )
            elapsed = time.time() - self._last_restart_time
            if elapsed < delay:
                remaining = delay - elapsed
                logger.debug(
                    "Back-off: waiting %.1fs before restart attempt %d",
                    remaining,
                    self._restart_attempts + 1,
                )
                time.sleep(remaining)

        self._restart_attempts += 1
        self._last_restart_time = time.time()

        success = self.start(self._model_info)
        if success:
            logger.info(
                "Worker restarted successfully (attempt %d)",
                self._restart_attempts,
            )
            self._restart_attempts = 0
        else:
            logger.error(
                "Worker restart failed (attempt %d)", self._restart_attempts
            )
        return success
