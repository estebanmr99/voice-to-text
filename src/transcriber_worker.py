"""Worker process entry point for whisper.cpp transcription.

This module is designed to run **inside** a separate Python interpreter
process spawned by :class:`transcriber.Transcriber`.  It loads a
whisper.cpp model via *pywhispercpp*, then loops reading audio arrays
from a :class:`multiprocessing.Queue` and writing results back.

Audio is never persisted to disk — numpy arrays travel directly across
the process boundary via pickling.
"""

from __future__ import annotations

import logging
import multiprocessing
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Minimum audio length (in samples @ 16 kHz) before we bother the model.
_MIN_AUDIO_SAMPLES = 1600  # 100 ms


def run_worker(
    audio_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    cancel_event: multiprocessing.Event,
    model_path: str,
    n_threads: int = 4,
) -> None:
    """Load a whisper.cpp model and transcribe audio from *audio_queue*.

    This function blocks until *cancel_event* is set.  Each audio array
    received is transcribed and a result dict is placed on
    *result_queue*.

    Parameters
    ----------
    audio_queue:
        Queue delivering ``(audio_array, sample_rate)`` tuples.
        ``audio_array`` should be a 1-D numpy array (int16 or float32).
    result_queue:
        Queue receiving result dicts: ``{"text": str, "error": str | None}``.
    cancel_event:
        When set, the worker drains the queue, sends any pending results,
        and exits cleanly.
    model_path:
        Absolute path to the GGML/GGUF model file.
    n_threads:
        Number of CPU threads for whisper.cpp inference.
    """
    try:
        from pywhispercpp.model import Model
    except ImportError as exc:  # pragma: no cover
        logger.error("pywhispercpp not available in worker: %s", exc)
        result_queue.put(
            {
                "text": "",
                "error": (
                    "Transcription backend (pywhispercpp) is not installed. "
                    f"Original error: {exc}"
                ),
            }
        )
        return

    # ------------------------------------------------------------------
    # Load model
    # ------------------------------------------------------------------
    try:
        model = Model(model_path, n_threads=n_threads)
        logger.info(
            "Worker loaded model from %s (n_threads=%d)",
            model_path,
            n_threads,
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to load model: %s", exc)
        result_queue.put(
            {"text": "", "error": f"Failed to load model: {exc}"}
        )
        return

    # ------------------------------------------------------------------
    # Transcription loop
    # ------------------------------------------------------------------
    while not cancel_event.is_set():
        try:
            payload = audio_queue.get(timeout=0.5)
        except Exception:
            # Queue empty or closed — loop back and check cancel_event
            continue

        if payload is None:
            # Sentinel value — graceful shutdown request
            logger.debug("Worker received shutdown sentinel")
            break

        # Support both (audio, sample_rate) and (audio, sample_rate, language)
        if len(payload) == 3:
            audio_array, sample_rate, language = payload
        else:
            audio_array, sample_rate = payload
            language = "auto"

        # Skip very short / empty audio
        if (
            audio_array is None
            or len(audio_array) < _MIN_AUDIO_SAMPLES
        ):
            result_queue.put({"text": "", "error": None})
            continue

        try:
            # pywhispercpp expects float32 audio normalized to [-1.0, 1.0]
            if audio_array.dtype == np.int16:
                audio_array = audio_array.astype(np.float32) / 32768.0
            elif audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)

            # Pass language to whisper for better multilingual detection.
            # "auto" is a valid pywhispercpp value — whisper.cpp uses it for
            # auto-detection (same as "" or None per PARAMS_SCHEMA).
            transcribe_kwargs: dict[str, str] = {}
            if language:
                transcribe_kwargs["language"] = language

            segments = model.transcribe(audio_array, **transcribe_kwargs)
            text = " ".join(s.text for s in segments).strip()
            result_queue.put({"text": text, "error": None})
        except Exception as exc:  # pragma: no cover
            logger.exception("Transcription error: %s", exc)
            result_queue.put({"text": "", "error": str(exc)})

    logger.info("Worker exiting")
