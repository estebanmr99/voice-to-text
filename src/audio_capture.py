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
        self._stream_samplerate = samplerate
        self._stream_blocksize = self.blocksize

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

        try:
            self._stream = self._open_stream()
        except Exception as exc:
            self._stream = None
            self._running = False
            raise exc

        self._running = True
        self._queue = queue.Queue()
        self._consumer_thread = threading.Thread(
            target=self._consumer_loop,
            args=(callback,),
            daemon=True,
        )
        self._consumer_thread.start()

        try:
            self._stream.start()
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        """Stop capturing and release the PortAudio stream."""
        self._running = False
        if self._consumer_thread is not None:
            if self._consumer_thread is not threading.current_thread():
                self._consumer_thread.join(timeout=1.0)
            self._consumer_thread = None
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def is_active(self) -> bool:
        """Return ``True`` if the input stream is currently running."""
        return self._stream is not None and getattr(self._stream, "active", False)

    def set_device_index(self, device_index: int | None) -> None:
        """Update the preferred input device for the next capture session."""
        self.device_index = device_index

    def _stream_kwargs(self, device: int | None, samplerate: int) -> dict:
        """Return common ``sd.InputStream`` keyword arguments."""
        blocksize = int(samplerate * self.block_duration_ms / 1000)
        kwargs = {
            "samplerate": samplerate,
            "channels": 1,
            "dtype": "int16",
            "blocksize": blocksize,
            "callback": self._stream_callback,
        }
        if device is not None:
            kwargs["device"] = device
        return kwargs

    def _open_stream(self) -> object:
        """Open an input stream, recovering from stale or invalid devices."""
        if sd is None:
            raise RuntimeError("sounddevice is not installed")

        attempts: list[int | None] = [self.device_index]
        fallback = self._find_fallback_input_device_index()
        if fallback not in attempts:
            attempts.append(fallback)

        last_exc: Exception | None = None
        for attempt_no, device in enumerate(attempts):
            samplerates = self._candidate_samplerates_for_device(device)
            for samplerate in samplerates:
                try:
                    stream = sd.InputStream(**self._stream_kwargs(device, samplerate))
                    self._stream_samplerate = samplerate
                    self._stream_blocksize = int(
                        samplerate * self.block_duration_ms / 1000
                    )
                    if attempt_no > 0:
                        logger.info(
                            "Opened fallback input device %s at %s Hz",
                            device,
                            samplerate,
                        )
                    elif samplerate != self.samplerate:
                        logger.info(
                            "Opened input device %s at native %s Hz (requested %s Hz)",
                            device,
                            samplerate,
                            self.samplerate,
                        )
                    return stream
                except Exception as exc:
                    last_exc = exc
                    if attempt_no == 0 and samplerate == samplerates[-1]:
                        logger.warning(
                            "Failed to open stream on device %s: %s. "
                            "Falling back to an available input device.",
                            device,
                            exc,
                        )

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("No input-capable audio device found")

    def _candidate_samplerates_for_device(self, device: int | None) -> list[int]:
        samplerates = [self.samplerate]
        info = self._device_info(device)
        default_samplerate = int(float(info.get("default_samplerate", 0) or 0))
        if default_samplerate > 0 and default_samplerate not in samplerates:
            samplerates.append(default_samplerate)
        return samplerates

    @staticmethod
    def _device_info(device: int | None) -> dict:
        if sd is None:
            raise RuntimeError("sounddevice is not installed")

        if device is None:
            return dict(sd.query_devices(kind="input"))
        try:
            info = sd.query_devices(device)
        except Exception:
            return {}

        if isinstance(info, dict):
            return dict(info)
        if isinstance(info, (list, tuple)) and 0 <= device < len(info):
            item = info[device]
            if isinstance(item, dict):
                return dict(item)
        return {}

    @classmethod
    def _find_fallback_input_device_index(cls) -> int | None:
        """Return an explicit input-capable fallback device index, if any."""
        if sd is None:
            raise RuntimeError("sounddevice is not installed")

        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            info = dict(dev)
            if info.get("max_input_channels", 0) <= 0:
                continue
            if cls._looks_like_loopback_device(str(info.get("name", ""))):
                continue
            return idx

        for idx, dev in enumerate(devices):
            if dict(dev).get("max_input_channels", 0) > 0:
                return idx
        return None

    @staticmethod
    def _looks_like_loopback_device(name: str) -> bool:
        folded = name.strip().casefold()
        loopback_markers = (
            "loopback",
            "stereo mix",
            "what u hear",
            "wave out",
            "system audio",
        )
        return any(marker in folded for marker in loopback_markers)

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
        if self._stream_samplerate != self.samplerate:
            data = self._resample_block(data)
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
        hostapis = AudioCapture._query_hostapi_names()
        result: list[dict] = []
        seen: set[tuple[str, str, int, int]] = set()
        for idx, dev in enumerate(devices):
            info = dict(dev)
            if info.get("max_input_channels", 0) > 0:
                info["index"] = idx
                hostapi_name = AudioCapture._hostapi_name(info, hostapis)
                info["hostapi_name"] = hostapi_name
                info["display_name"] = AudioCapture._build_device_label(info, hostapi_name)
                dedupe_key = (
                    str(info.get("name", "")).strip().casefold(),
                    hostapi_name.casefold(),
                    int(info.get("max_input_channels", 0) or 0),
                    int(float(info.get("default_samplerate", 0) or 0)),
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
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

    def _resample_block(self, block: np.ndarray) -> np.ndarray:
        if len(block) == self.blocksize:
            return block.astype(np.int16, copy=False)
        if len(block) == 0:
            return np.zeros(self.blocksize, dtype=np.int16)
        if len(block) == 1:
            return np.full(self.blocksize, int(block[0]), dtype=np.int16)

        source_positions = np.linspace(0, len(block) - 1, num=len(block), dtype=np.float32)
        target_positions = np.linspace(
            0,
            len(block) - 1,
            num=self.blocksize,
            dtype=np.float32,
        )
        resampled = np.interp(target_positions, source_positions, block.astype(np.float32))
        return np.clip(np.rint(resampled), -32768, 32767).astype(np.int16)

    @staticmethod
    def _query_hostapi_names() -> list[str]:
        if sd is None or not hasattr(sd, "query_hostapis"):
            return []

        try:
            hostapis = sd.query_hostapis()
        except Exception:
            return []

        names: list[str] = []
        for hostapi in hostapis:
            info = dict(hostapi)
            names.append(str(info.get("name", "")).strip())
        return names

    @staticmethod
    def _hostapi_name(info: dict, hostapis: list[str]) -> str:
        raw_hostapi = info.get("hostapi")
        if isinstance(raw_hostapi, int) and 0 <= raw_hostapi < len(hostapis):
            return hostapis[raw_hostapi]
        return ""

    @staticmethod
    def _build_device_label(info: dict, hostapi_name: str) -> str:
        name = str(info.get("name", "Unknown device")).strip() or "Unknown device"
        channels = int(info.get("max_input_channels", 0) or 0)
        channel_label = "1 channel" if channels == 1 else f"{channels} channels"
        if hostapi_name:
            return f"{name} — {hostapi_name} ({channel_label})"
        return f"{name} ({channel_label})"
