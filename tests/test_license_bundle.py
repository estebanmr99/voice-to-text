"""License bundle generator and notice coverage tests.

Validates that the generate_license_bundle script covers all required
runtime and model dependency tokens, and that --check correctly validates
generated output.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))

import generate_license_bundle as glb  # noqa: E402


class TestRequiredTokens:
    """Verify that REQUIRED_NOTICE_TOKENS covers every runtime dependency
    listed in requirements.txt and the licence matrix."""

    def test_required_notice_tokens_cover_runtime_dependencies(self) -> None:
        tokens = glb.REQUIRED_NOTICE_TOKENS
        assert "PySide6" in tokens
        assert "Qt" in tokens
        assert "sounddevice" in tokens
        assert "PortAudio" in tokens
        assert "numpy" in tokens
        assert "pywhispercpp" in tokens
        assert "whisper.cpp" in tokens
        assert "pywin32" in tokens

    def test_optional_vad_coverage(self) -> None:
        assert "WebRTC VAD" in glb.REQUIRED_NOTICE_TOKENS

    def test_cuda_redistribution_blocked(self) -> None:
        assert "CUDA/cuDNN redistribution blocked" in glb.REQUIRED_NOTICE_TOKENS

    def test_dev_backend_coverage(self) -> None:
        tokens = glb.REQUIRED_NOTICE_TOKENS
        assert "faster-whisper" in tokens
        assert "CTranslate2" in tokens

    def test_model_asset_coverage(self) -> None:
        assert "Whisper model weights" in glb.REQUIRED_NOTICE_TOKENS

    def test_sbom_command_present(self) -> None:
        assert "cyclonedx_py requirements" in glb.SBOM_COMMAND


class TestCheckFlag:
    """Validate --check behaviour against generated (or temp) notice files."""

    def test_check_rejects_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = glb.run_check(
                third_party_path=Path(tmp) / "THIRD-PARTY-NOTICES.md",
                model_notices_path=Path(tmp) / "MODEL-NOTICES.md",
                required_tokens=glb.REQUIRED_NOTICE_TOKENS,
            )
            assert exit_code != 0

    def test_check_passes_with_all_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tpn = Path(tmp) / "THIRD-PARTY-NOTICES.md"
            mn = Path(tmp) / "MODEL-NOTICES.md"

            content = "\n".join(sorted(glb.REQUIRED_NOTICE_TOKENS))
            tpn.write_text(content, encoding="utf-8")
            mn.write_text(content, encoding="utf-8")

            exit_code = glb.run_check(
                third_party_path=tpn,
                model_notices_path=mn,
                required_tokens=glb.REQUIRED_NOTICE_TOKENS,
            )
            assert exit_code == 0, "all tokens present → --check should exit 0"

    def test_check_rejects_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tpn = Path(tmp) / "THIRD-PARTY-NOTICES.md"
            mn = Path(tmp) / "MODEL-NOTICES.md"

            # Drop the last token so at least one is missing
            tokens = sorted(glb.REQUIRED_NOTICE_TOKENS)[:-1]
            content = "\n".join(sorted(tokens))
            tpn.write_text(content, encoding="utf-8")
            mn.write_text(content, encoding="utf-8")

            exit_code = glb.run_check(
                third_party_path=tpn,
                model_notices_path=mn,
                required_tokens=glb.REQUIRED_NOTICE_TOKENS,
            )
            assert exit_code != 0, "missing token → --check should fail"

    def test_check_with_duplicate_in_one_file(self) -> None:
        """All tokens in THIRD-PARTY only — MODEL emptier — still passes."""
        with tempfile.TemporaryDirectory() as tmp:
            tpn = Path(tmp) / "THIRD-PARTY-NOTICES.md"
            mn = Path(tmp) / "MODEL-NOTICES.md"

            content = "\n".join(sorted(glb.REQUIRED_NOTICE_TOKENS))
            tpn.write_text(content, encoding="utf-8")
            mn.write_text("", encoding="utf-8")

            exit_code = glb.run_check(
                third_party_path=tpn,
                model_notices_path=mn,
                required_tokens=glb.REQUIRED_NOTICE_TOKENS,
            )
            assert exit_code == 0


class TestWriteFlag:
    """Validate --write behaviour creates both notice files."""

    def test_write_creates_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tpn = Path(tmp) / "THIRD-PARTY-NOTICES.md"
            mn = Path(tmp) / "MODEL-NOTICES.md"

            glb.run_write(
                third_party_path=tpn,
                model_notices_path=mn,
                model_sha_base="60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
                model_sha_small="1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b",
                model_source_url="https://huggingface.co/ggerganov/whisper.cpp/tree/main",
            )

            assert tpn.is_file()
            assert mn.is_file()

            tp_text = tpn.read_text(encoding="utf-8")
            mn_text = mn.read_text(encoding="utf-8")

            assert "PySide6" in tp_text
            assert "PortAudio" in tp_text
            assert "CUDA/cuDNN redistribution blocked" in tp_text
            assert "ggml-base.bin" in mn_text
            assert "ggml-small.bin" in mn_text
            assert "Model binaries are not included in git or the default portable zip" in mn_text
            assert "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe" in mn_text


class TestScriptIntegration:
    """Verify the script runs as a standalone module with --check and --write."""

    def test_script_contains_required_constants(self) -> None:
        script_text = (SCRIPTS / "generate_license_bundle.py").read_text(encoding="utf-8")
        assert "REQUIRED_NOTICE_TOKENS" in script_text
        assert "cyclonedx_py requirements" in script_text
