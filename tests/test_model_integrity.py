"""Model integrity checksum cross-verification tests.

Verifies that model checksums are consistent across all sources:
  - models/model_checksums.json (source of truth)
  - scripts/generate_license_bundle.py (MODEL_METADATA import)
  - docs/MODEL-SIDELOADING.md (published docs)

These tests run in CI (no model binaries required).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


class TestModelChecksums:
    """Verify model checksums are consistent across all sources."""

    def test_checksums_json_exists(self) -> None:
        assert (ROOT / "models" / "model_checksums.json").is_file()

    def test_checksums_json_has_expected_models(self) -> None:
        c = json.loads((ROOT / "models" / "model_checksums.json").read_text())
        assert "ggml-base.bin" in c
        assert "ggml-small.bin" in c
        assert len(c["ggml-base.bin"]["sha256"]) == 64
        assert len(c["ggml-small.bin"]["sha256"]) == 64

    def test_checksums_match_generate_license_bundle(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        import generate_license_bundle as glb  # noqa: E402

        c = json.loads((ROOT / "models" / "model_checksums.json").read_text())
        assert (
            glb.MODEL_METADATA["ggml-base.bin"]["sha256"]
            == c["ggml-base.bin"]["sha256"]
        )
        assert (
            glb.MODEL_METADATA["ggml-small.bin"]["sha256"]
            == c["ggml-small.bin"]["sha256"]
        )

    def test_checksums_match_sideloading_docs(self) -> None:
        c = json.loads((ROOT / "models" / "model_checksums.json").read_text())
        doc = (ROOT / "docs" / "MODEL-SIDELOADING.md").read_text()
        assert c["ggml-base.bin"]["sha256"] in doc
        assert c["ggml-small.bin"]["sha256"] in doc
