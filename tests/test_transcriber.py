"""Tests for Transcriber and transcriber_worker.

All tests mock ``pywhispercpp.model.Model`` and
:class:`multiprocessing.Process` so that no real model is loaded and
no actual subprocesses are spawned.
"""

from __future__ import annotations

import multiprocessing
import sys
import time
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from model_manager import ModelInfo, ModelManager
from transcriber import Transcriber, TranscriptionError

# Create a fake pywhispercpp module so tests can patch it without installing it.
_fake_pywhispercpp = ModuleType("pywhispercpp")
_fake_pywhispercpp_model = ModuleType("pywhispercpp.model")
_fake_pywhispercpp_model.Model = object  # placeholder for patching
_fake_pywhispercpp.model = _fake_pywhispercpp_model
sys.modules.setdefault("pywhispercpp", _fake_pywhispercpp)
sys.modules.setdefault("pywhispercpp.model", _fake_pywhispercpp_model)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_model_info(tmp_path) -> ModelInfo:
    """Return a ModelInfo backed by a real temporary file."""
    model_file = tmp_path / "ggml-base.bin"
    model_file.write_bytes(b"fake model data")
    return ModelInfo(
        name="base",
        path=model_file,
        size_mb=1,
        parameters={"n_threads": 4},
    )


@pytest.fixture
def mock_process():
    """Patch multiprocessing.Process to a MagicMock."""
    with patch("transcriber.multiprocessing.Process") as mock_cls:
        instance = MagicMock()
        instance.is_alive.return_value = True
        instance.pid = 12345
        mock_cls.return_value = instance
        yield mock_cls, instance


@pytest.fixture
def mock_queues():
    """Patch Queue creation so tests can inspect messages."""
    with patch("transcriber.multiprocessing.Queue") as mock_q_cls:
        audio_q = MagicMock()
        result_q = MagicMock()
        # Return fresh queues on each instantiation
        mock_q_cls.side_effect = [audio_q, result_q]
        yield audio_q, result_q


@pytest.fixture
def mock_event():
    """Patch Event creation."""
    with patch("transcriber.multiprocessing.Event") as mock_e_cls:
        instance = MagicMock()
        instance.is_set.return_value = False
        mock_e_cls.return_value = instance
        yield instance


@pytest.fixture
def transcriber(valid_model_info, tmp_path) -> Transcriber:
    """Return a Transcriber with a mocked ModelManager."""
    mgr = ModelManager(models_dir=tmp_path)
    return Transcriber(mgr)


# ---------------------------------------------------------------------------
# Worker lifecycle
# ---------------------------------------------------------------------------


class TestTranscriberLifecycle:
    """Start, stop, and status checks."""

    def test_start_spawns_process(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        mock_cls, instance = mock_process
        success = transcriber.start(valid_model_info)
        assert success is True
        mock_cls.assert_called_once()
        instance.start.assert_called_once()

    def test_start_validates_model_path(
        self, transcriber
    ) -> None:
        bad_info = ModelInfo(
            name="missing", path=transcriber._model_manager._models_dir / "nope.bin", size_mb=1
        )
        success = transcriber.start(bad_info)
        assert success is False
        assert transcriber.get_last_error() is not None

    def test_is_running_after_start(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber.start(valid_model_info)
        assert transcriber.is_running() is True

    def test_is_running_after_stop(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber.start(valid_model_info)
        _, instance = mock_process
        instance.is_alive.return_value = False
        transcriber.stop()
        assert transcriber.is_running() is False

    def test_stop_joins_with_timeout(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber.start(valid_model_info)
        _, instance = mock_process
        instance.is_alive.return_value = False
        transcriber.stop()
        instance.join.assert_called_once_with(timeout=5.0)

    def test_stop_terminates_if_alive(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber.start(valid_model_info)
        _, instance = mock_process
        # Simulate process still alive after join timeout
        instance.is_alive.side_effect = [True, True, False]
        transcriber.stop()
        instance.terminate.assert_called_once()

    def test_start_same_model_idempotent(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber.start(valid_model_info)
        mock_cls, _ = mock_process
        calls_before = mock_cls.call_count
        success = transcriber.start(valid_model_info)
        assert success is True
        # Should not spawn a second process
        assert mock_cls.call_count == calls_before


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------


class TestTranscriberTranscribe:
    """Audio → text flow."""

    def test_transcribe_returns_text(
        self, transcriber, valid_model_info, mock_process, mock_queues
    ) -> None:
        audio_q, result_q = mock_queues
        result_q.get.return_value = {"text": "hello world", "error": None}

        transcriber.start(valid_model_info)
        audio = np.ones(3200, dtype=np.int16)  # 200 ms
        text = transcriber.transcribe(audio)

        assert text == "hello world"
        audio_q.put.assert_called_once()

    def test_transcribe_raises_on_worker_error(
        self, transcriber, valid_model_info, mock_process, mock_queues
    ) -> None:
        _, result_q = mock_queues
        result_q.get.return_value = {
            "text": "",
            "error": "model load failed",
        }

        transcriber.start(valid_model_info)
        audio = np.ones(3200, dtype=np.int16)
        with pytest.raises(TranscriptionError, match="model load failed"):
            transcriber.transcribe(audio)

    def test_empty_audio_returns_empty_string(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber.start(valid_model_info)
        audio = np.array([], dtype=np.int16)
        text = transcriber.transcribe(audio)
        assert text == ""

    def test_short_audio_returns_empty_string(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber.start(valid_model_info)
        audio = np.ones(800, dtype=np.int16)  # 50 ms
        text = transcriber.transcribe(audio)
        assert text == ""

    def test_transcribe_restarts_worker_if_not_running(
        self, transcriber, valid_model_info, mock_process, mock_queues
    ) -> None:
        mock_cls, instance = mock_process
        audio_q, result_q = mock_queues
        result_q.get.return_value = {"text": "restarted", "error": None}

        transcriber.start(valid_model_info)
        # Simulate worker dying between calls
        instance.is_alive.return_value = False
        instance.reset_mock()

        # Second start should be triggered by _try_restart
        instance.is_alive.return_value = True
        audio = np.ones(3200, dtype=np.int16)
        text = transcriber.transcribe(audio)
        assert text == "restarted"


# ---------------------------------------------------------------------------
# Worker module (transcriber_worker)
# ---------------------------------------------------------------------------


class TestTranscriberWorker:
    """Unit-level tests for ``run_worker`` logic."""

    def test_worker_exits_on_cancel(self) -> None:
        """When cancel_event is set, the loop exits cleanly."""
        from transcriber_worker import run_worker

        audio_q = MagicMock()
        result_q = MagicMock()
        cancel_event = MagicMock()

        # First iteration: queue.get raises (empty)
        # Second iteration: cancel_event is set
        audio_q.get.side_effect = [Exception("empty"), Exception("empty")]
        cancel_event.is_set.side_effect = [False, True]

        with patch("pywhispercpp.model.Model") as mock_model_cls:
            mock_model_cls.return_value = MagicMock()
            run_worker(audio_q, result_q, cancel_event, "/fake/model.bin")

        # Should have exited without putting further results
        assert result_q.put.call_count == 0

    def test_worker_skips_short_audio(self) -> None:
        """Audio below _MIN_AUDIO_SAMPLES returns empty result."""
        from transcriber_worker import run_worker

        audio_q = MagicMock()
        result_q = MagicMock()
        cancel_event = MagicMock()
        cancel_event.is_set.side_effect = [False, True]

        short_audio = np.ones(100, dtype=np.int16)
        audio_q.get.return_value = (short_audio, 16000)

        with patch("pywhispercpp.model.Model") as mock_model_cls:
            mock_model_cls.return_value = MagicMock()
            run_worker(audio_q, result_q, cancel_event, "/fake/model.bin")

        result_q.put.assert_called_once_with({"text": "", "error": None})

    def test_worker_transcribes_audio(self) -> None:
        """Normal audio produces text result."""
        from transcriber_worker import run_worker

        audio_q = MagicMock()
        result_q = MagicMock()
        cancel_event = MagicMock()
        cancel_event.is_set.side_effect = [False, True]

        audio = np.ones(3200, dtype=np.int16)
        audio_q.get.return_value = (audio, 16000)

        mock_segment = MagicMock()
        mock_segment.text = "test result"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = [mock_segment]

        with patch("pywhispercpp.model.Model") as mock_model_cls:
            mock_model_cls.return_value = mock_model
            run_worker(audio_q, result_q, cancel_event, "/fake/model.bin")

        result_q.put.assert_called_once_with(
            {"text": "test result", "error": None}
        )

    def test_worker_catches_transcribe_exception(self) -> None:
        """Exception during transcribe is reported on result queue."""
        from transcriber_worker import run_worker

        audio_q = MagicMock()
        result_q = MagicMock()
        cancel_event = MagicMock()
        cancel_event.is_set.side_effect = [False, True]

        audio = np.ones(3200, dtype=np.int16)
        audio_q.get.return_value = (audio, 16000)

        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("inference failed")

        with patch("pywhispercpp.model.Model") as mock_model_cls:
            mock_model_cls.return_value = mock_model
            run_worker(audio_q, result_q, cancel_event, "/fake/model.bin")

        result_q.put.assert_called_once()
        args, _ = result_q.put.call_args
        assert args[0]["error"] == "inference failed"
        assert args[0]["text"] == ""

    def test_worker_import_error_reported(self) -> None:
        """If pywhispercpp is missing, an error is queued immediately."""
        from transcriber_worker import run_worker

        audio_q = MagicMock()
        result_q = MagicMock()
        cancel_event = MagicMock()

        with patch.dict("sys.modules", {"pywhispercpp": None, "pywhispercpp.model": None}):
            run_worker(
                audio_q, result_q, cancel_event, "/fake/model.bin"
            )

        result_q.put.assert_called_once()
        args, _ = result_q.put.call_args
        assert "pywhispercpp" in args[0]["error"]


# ---------------------------------------------------------------------------
# Crash recovery / backoff
# ---------------------------------------------------------------------------


class TestTranscriberCrashRecovery:
    """Restart behaviour with exponential backoff."""

    def test_backoff_increases_with_attempts(
        self, transcriber, valid_model_info
    ) -> None:
        transcriber._model_info = valid_model_info
        transcriber._restart_attempts = 3
        transcriber._last_restart_time = time.time()  # recent restart, delay not elapsed

        with patch.object(transcriber, "start", return_value=True) as mock_start:
            with patch("transcriber.time.sleep") as mock_sleep:
                result = transcriber._try_restart()

        assert result is True
        mock_sleep.assert_called_once()
        # Delay should be > 1s (backoff formula: 1 * 2^(3-1) = 4)
        delay = mock_sleep.call_args[0][0]
        assert delay >= 2.0

    def test_backoff_resets_on_success(
        self, transcriber, valid_model_info, mock_process
    ) -> None:
        transcriber._model_info = valid_model_info
        transcriber._restart_attempts = 5

        with patch("transcriber.time.sleep"):
            transcriber._try_restart()

        assert transcriber._restart_attempts == 0
