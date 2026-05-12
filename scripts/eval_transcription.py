#!/usr/bin/env python
"""WER benchmark CLI for Whisper models against the eval dataset.

Computes per-clip and aggregate Word Error Rate for a given model file
against the reference transcripts in data/eval/.

Usage:
    python scripts/eval_transcription.py --model-path models/ggml-base.bin
    python scripts/eval_transcription.py --model-path models/ggml-base.bin --threshold 10.0
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# WER computation — keep the jiwer import optional for the module-level
# compute_wer_for_model function that tests import directly.
# ---------------------------------------------------------------------------

try:
    from jiwer import wer as jiwer_wer
except ImportError:  # pragma: no cover
    jiwer_wer = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Model imports (lazy — only when actually running)
# ---------------------------------------------------------------------------


def _load_transcriber():
    """Lazy-import and return (ModelManager, Transcriber, ModelInfo)."""
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from model_manager import ModelInfo, ModelManager
    from transcriber import Transcriber

    return ModelManager, Transcriber, ModelInfo


# ---------------------------------------------------------------------------
# Audio loading
# ---------------------------------------------------------------------------


def _load_wav(path: Path) -> tuple[np.ndarray, int]:
    """Load a WAV file and return (audio_array, sample_rate).

    Tries scipy.io.wavfile first, falls back to stdlib ``wave``.
    Returns mono int16 audio resampled to 16 kHz.
    """
    try:
        import scipy.io.wavfile as wavfile

        sample_rate, data = wavfile.read(str(path))
    except ImportError:
        data, sample_rate = _load_wav_wave(path)
    except Exception:
        data, sample_rate = _load_wav_wave(path)

    # Convert to mono
    if data.ndim > 1:
        data = data.mean(axis=1).astype(data.dtype)

    # Resample to 16 kHz if needed
    if sample_rate != 16000:
        data = _resample(data, sample_rate, 16000)
        sample_rate = 16000

    return data, sample_rate


def _load_wav_wave(path: Path) -> tuple[np.ndarray, int]:
    """Fallback WAV loader using stdlib ``wave`` module."""
    import struct
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


def _resample(data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Simple linear-interpolation resample."""
    n_orig = len(data)
    n_target = int(n_orig * target_sr / orig_sr)
    indices = np.linspace(0, n_orig - 1, n_target)
    return np.interp(indices, np.arange(n_orig), data).astype(data.dtype)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ClipResult:
    id: str
    ground_truth: str
    hypothesis: str
    wer: float


@dataclass
class BenchmarkResult:
    clips: list[ClipResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def mean_wer(self) -> float:
        if not self.clips:
            return 0.0
        return sum(c.wer for c in self.clips) / len(self.clips)

    @property
    def median_wer(self) -> float:
        if not self.clips:
            return 0.0
        return statistics.median(c.wer for c in self.clips)


# ---------------------------------------------------------------------------
# Core benchmark function
# ---------------------------------------------------------------------------


def compute_wer_for_model(
    model_path: str | Path,
    data_dir: str | Path = "data/eval",
    n_threads: int = 4,
) -> BenchmarkResult:
    """Run WER benchmark against eval dataset.

    Returns a ``BenchmarkResult`` with per-clip results and aggregate stats.
    This function is the public API for test import.
    """
    if jiwer_wer is None:
        raise RuntimeError(
            "jiwer is required — install with: pip install jiwer>=3.0"
        )

    result = BenchmarkResult()
    data_dir = Path(data_dir)
    model_path = Path(model_path)

    # Load transcripts
    transcripts_path = data_dir / "transcripts.jsonl"
    if not transcripts_path.is_file():
        result.errors.append(f"Transcripts not found: {transcripts_path}")
        return result

    transcripts: dict[str, str] = {}
    with transcripts_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entry = json.loads(line)
                transcripts[str(entry["id"])] = str(entry["text"])

    # Check model exists
    if not model_path.is_file():
        result.errors.append(f"Model file not found: {model_path}")
        return result

    # Start transcriber
    ModelManager, Transcriber, ModelInfo = _load_transcriber()
    manager = ModelManager(models_dir=str(model_path.parent))
    transcriber = Transcriber(manager)

    model_info = ModelInfo(
        path=str(model_path),
        name=model_path.name,
        n_threads=n_threads,
    )

    try:
        if not transcriber.start(model_info):
            err = transcriber.get_last_error() or "Unknown error starting transcriber"
            result.errors.append(f"Failed to start transcriber: {err}")
            return result

        # Process each clip
        for clip_id in sorted(transcripts.keys()):
            wav_path = data_dir / f"{clip_id}.wav"
            if not wav_path.is_file():
                continue

            try:
                audio, sr = _load_wav(wav_path)
                hypothesis = transcriber.transcribe(audio)
                if hypothesis is None:
                    hypothesis = ""
                gt = transcripts[clip_id]
                w = jiwer_wer(gt, hypothesis)
                result.clips.append(
                    ClipResult(id=clip_id, ground_truth=gt, hypothesis=hypothesis, wer=w)
                )
            except Exception as exc:
                result.errors.append(f"Clip {clip_id}: {exc}")
    finally:
        transcriber.stop()

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_results(result: BenchmarkResult) -> None:
    """Print per-clip table and aggregate stats."""
    if result.errors:
        for err in result.errors:
            print(f"WARNING: {err}", file=sys.stderr)

    if not result.clips:
        print("No clips processed.")
        return

    # Header
    print(f"{'ID':>4}  {'WER%':>6}  {'Ground truth':<40}  {'Hypothesis':<40}")
    print("-" * 96)

    for clip in result.clips:
        gt_trunc = clip.ground_truth[:38] + ".." if len(clip.ground_truth) > 40 else clip.ground_truth
        hyp_trunc = clip.hypothesis[:38] + ".." if len(clip.hypothesis) > 40 else clip.hypothesis
        print(
            f"{clip.id:>4}  {clip.wer * 100:>5.1f}%  {gt_trunc:<40}  {hyp_trunc:<40}"
        )

    print("-" * 96)
    print(f"Clips processed: {len(result.clips)}")
    print(f"Mean WER:   {result.mean_wer * 100:.2f}%")
    print(f"Median WER: {result.median_wer * 100:.2f}%")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WER benchmark for Whisper models against eval dataset."
    )
    parser.add_argument(
        "--model-path",
        required=True,
        help="Path to the Whisper model .bin file",
    )
    parser.add_argument(
        "--data-dir",
        default="data/eval",
        help="Eval data directory (default: data/eval)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=15.0,
        help="WER %% exit threshold (default: 15.0)",
    )
    parser.add_argument(
        "--n-threads",
        type=int,
        default=4,
        help="Number of CPU threads (default: 4)",
    )
    args = parser.parse_args(argv)

    result = compute_wer_for_model(
        model_path=args.model_path,
        data_dir=args.data_dir,
        n_threads=args.n_threads,
    )

    _print_results(result)

    if not result.clips:
        return 2

    aggregate_wer = result.mean_wer * 100
    if aggregate_wer > args.threshold:
        print(
            f"\nFAIL: Aggregate WER {aggregate_wer:.2f}% exceeds threshold "
            f"{args.threshold}%"
        )
        return 1

    print(f"\nPASS: Aggregate WER {aggregate_wer:.2f}% within threshold {args.threshold}%")
    return 0


if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="numpy.dtype size changed")
    sys.exit(main())
