"""Real-model dictation smoke test.

Loads the first available Whisper model and transcribes the first available
eval WAV clip.  This is NOT an accuracy test — it verifies the model loads,
the worker process starts, audio flows through, and text is returned.

Gracefully skips when no model files or eval WAV files are present.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
EVAL_DIR = ROOT / "data" / "eval"

_has_model = any(MODELS_DIR.glob("*.bin"))
_has_eval_wav = len(list(EVAL_DIR.glob("*.wav"))) > 0


def _load_wav(path: Path) -> np.ndarray:
    """Load a WAV file and return mono int16 audio at 16 kHz."""
    try:
        import scipy.io.wavfile as wavfile

        sample_rate, data = wavfile.read(str(path))
    except ImportError:
        data, sample_rate = _load_wav_wave(path)

    # Convert to mono
    if data.ndim > 1:
        data = data.mean(axis=1).astype(data.dtype)

    # Resample to 16 kHz if needed
    if sample_rate != 16000:
        n_target = int(len(data) * 16000 / sample_rate)
        indices = np.linspace(0, len(data) - 1, n_target)
        data = np.interp(indices, np.arange(len(data)), data).astype(data.dtype)

    return data


def _load_wav_wave(path: Path) -> tuple[np.ndarray, int]:
    """Fallback WAV loader using stdlib ``wave`` module."""
    import wave

    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sampwidth, np.int16)
    data = np.frombuffer(raw, dtype=dtype).reshape(-1, n_channels)

    if n_channels > 1:
        data = data.mean(axis=1).astype(dtype)

    return data, framerate


@pytest.mark.skipif(not _has_model, reason="No model files found in models/")
@pytest.mark.skipif(not _has_eval_wav, reason="No eval WAV files in data/eval/")
class TestDictationSmoke:
    """Real transcriber loads model and transcribes without error."""

    def test_model_loads_and_transcribes(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "src"))
        from model_manager import ModelInfo, ModelManager
        from transcriber import Transcriber

        model_path = next(MODELS_DIR.glob("*.bin"))
        wav_path = next(EVAL_DIR.glob("*.wav"))

        audio = _load_wav(wav_path)
        assert len(audio) > 0, "Loaded audio is empty"

        manager = ModelManager(models_dir=str(MODELS_DIR))
        transcriber = Transcriber(manager)

        try:
            model_info = ModelInfo(
                path=str(model_path),
                name=model_path.name,
                n_threads=4,
            )

            started = transcriber.start(model_info)
            if not started:
                err = transcriber.get_last_error() or "unknown"
                pytest.fail(f"Transcriber failed to start: {err}")

            text = transcriber.transcribe(audio)

            assert isinstance(text, str), f"Expected str, got {type(text)}"
            assert len(text) > 0, "Transcription returned empty string"
        finally:
            transcriber.stop()
