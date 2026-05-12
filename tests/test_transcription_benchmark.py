"""WER threshold regression tests.

Uses the eval dataset (data/eval/) to assert that available models meet
accuracy thresholds calibrated to measured performance on mixed EN/ES:
  - ggml-base.bin:  ≤ 30% WER (English-only model on mixed dataset)
  - ggml-small.bin: ≤ 20% WER (multilingual model, ~18% measured)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"

# Make scripts importable
sys.path.insert(0, str(SCRIPTS_DIR))

_has_model = any((ROOT / "models").glob("*.bin"))
_has_eval_data = (
    (ROOT / "data" / "eval" / "transcripts.jsonl").is_file()
    and len(list((ROOT / "data" / "eval").glob("*.wav"))) > 0
)

BASE_THRESHOLD = 30.0  # WER % — English-only model on mixed EN/ES dataset
SMALL_THRESHOLD = 20.0  # WER % — multilingual model, ~18% measured


@pytest.mark.skipif(not _has_model, reason="No model files in models/")
@pytest.mark.skipif(not _has_eval_data, reason="No eval WAV or transcripts in data/eval/")
class TestTranscriptionBenchmark:
    """WER benchmark tests for available models."""

    def test_base_model_wer_below_threshold(self) -> None:
        base_path = ROOT / "models" / "ggml-base.bin"
        if not base_path.is_file():
            pytest.skip("ggml-base.bin not found")

        from eval_transcription import compute_wer_for_model

        result = compute_wer_for_model(
            model_path=str(base_path),
            data_dir=str(ROOT / "data" / "eval"),
            n_threads=4,
        )

        assert len(result.clips) > 0, "No eval clips could be processed"
        mean_wer = result.mean_wer * 100
        assert (
            mean_wer <= BASE_THRESHOLD
        ), f"Base model WER {mean_wer:.2f}% exceeds threshold {BASE_THRESHOLD}%"

    def test_small_model_wer_below_threshold(self) -> None:
        small_path = ROOT / "models" / "ggml-small.bin"
        if not small_path.is_file():
            pytest.skip("ggml-small.bin not found")

        from eval_transcription import compute_wer_for_model

        result = compute_wer_for_model(
            model_path=str(small_path),
            data_dir=str(ROOT / "data" / "eval"),
            n_threads=4,
        )

        assert len(result.clips) > 0, "No eval clips could be processed"
        mean_wer = result.mean_wer * 100
        assert (
            mean_wer <= SMALL_THRESHOLD
        ), f"Small model WER {mean_wer:.2f}% exceeds threshold {SMALL_THRESHOLD}%"
