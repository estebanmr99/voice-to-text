"""Microphone audio capture via sounddevice/PortAudio.

This module is importable without PySide6 — no GUI dependencies.
Audio buffers are strictly in-memory; no audio data is ever persisted to disk.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None  # type: ignore[assignment]


class AudioCapture:
    """Capture microphone audio using PortAudio via sounddevice.

    Parameters
    ----------
    device_index:
        PortAudio device index, or ``None`` for the default input device.
    samplerate:
        Sampling rate in Hz (default 16000).
    block_duration_ms:
        Duration of each audio block in milliseconds (default 30).
    """

    def __init__(
        self,
        device_index: int | None = None,
        samplerate: int = 16000,
        block_duration_ms: int = 30,
    ) -> None:
        self.device_index = device_index
        self.samplerate = samplerate
        self.block_duration_ms = block_duration_ms
        self.blocksize = int(samplerate * block_duration_ms / 1000)

        self._stream: object | None = None
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._running = False
        self._consumer_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, callback: Callable[[np.ndarray], None]) -> None:
        """Start capturing audio and delivering blocks to *callback*.

        The callback is invoked from a dedicated consumer thread with
        ``np.ndarray`` of shape ``(blocksize,)`` and dtype ``int16``.
        """
        if sd is None:
            raise RuntimeError("sounddevice is not installed")

        if self.is_active():
            raise RuntimeError("AudioCapture is already active")

        self._running = True
        self._queue = queue.Queue()
        self._consumer_thread = threading.Thread(
            target=self._consumer_loop,
            args=(callback,),
            daemon=True,
        )
        self._consumer_thread.start()

        try:
            self._stream = sd.InputStream(
                device=self.device_index,
                samplerate=self.samplerate,
                channels=1,
                dtype="int16",
                blocksize=self.blocksize,
                callback=self._stream_callback,
            )
        except Exception as exc:
            logger.warning(
                "Failed to open stream on device %s: %s. Falling back to default.",
                self.device_index,
                exc,
            )
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=1,
                dtype="int16",
                blocksize=self.blocksize,
                callback=self._stream_callback,
            )
        self._stream.start()

    def stop(self) -> None:
        """Stop capturing and release the PortAudio stream."""
        self._running = False
        if self._consumer_thread is not None:
            self._consumer_thread.join(timeout=1.0)
            self._consumer_thread = None
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def is_active(self) -> bool:
        """Return ``True`` if the input stream is currently running."""
        return self._stream is not None and getattr(self._stream, "active", False)

    # ------------------------------------------------------------------
    # Stream callback helpers
    # ------------------------------------------------------------------

    def _stream_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """PortAudio callback — runs on a dedicated PortAudio thread.

        Copies the first channel into the queue for the consumer thread.
        """
        # indata shape is (frames, channels); extract mono channel
        data = indata[:, 0].copy()
        try:
            self._queue.put_nowait(data)
        except queue.Full:
            # Drop oldest block if consumer can't keep up
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put_nowait(data)

    def _consumer_loop(self, callback: Callable[[np.ndarray], None]) -> None:
        """Read blocks from the queue and forward to the user callback."""
        while self._running:
            try:
                block = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                callback(block)
            except Exception:
                logger.exception("Error in audio capture callback")

    # ------------------------------------------------------------------
    # Device introspection
    # ------------------------------------------------------------------

    @staticmethod
    def list_devices() -> list[dict]:
        """Return a list of available input devices.

        Each entry contains at least ``index``, ``name``, and
        ``default_samplerate``.
        """
        if sd is None:
            raise RuntimeError("sounddevice is not installed")

        devices = sd.query_devices()
        result: list[dict] = []
        for idx, dev in enumerate(devices):
            info = dict(dev)
            if info.get("max_input_channels", 0) > 0:
                info["index"] = idx
                result.append(info)
        return result

    @staticmethod
    def get_default_device() -> dict:
        """Return the default input device information."""
        if sd is None:
            raise RuntimeError("sounddevice is not installed")
        return dict(sd.query_devices(kind="input"))

    # ------------------------------------------------------------------
    # Helpers for synchronous consumers
    # ------------------------------------------------------------------

    def get_audio_callback(
        self,
        q: queue.Queue[np.ndarray],
    ) -> Callable[[np.ndarray, int, object, object], None]:
        """Return a PortAudio-style callback that enqueues buffers.

        Useful when you want to manage the ``sd.InputStream`` yourself
        but still feed blocks into a :class:`queue.Queue`.
        """

        def callback(
            indata: np.ndarray,
            frames: int,
            time_info: object,
            status: object,
        ) -> None:
            data = indata[:, 0].copy()
            try:
                q.put_nowait(data)
            except queue.Full:
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                q.put_nowait(data)

        return callback
