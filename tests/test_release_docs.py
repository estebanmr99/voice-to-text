"""Release documentation content validation tests.

Asserts that every public-facing release document contains the
required privacy, licence, model, and release-process claims.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestReadme:
    _RELEASES_URL = "https://github.com/estebanmr99/voice-to-text/releases"

    @staticmethod
    def _read() -> str:
        return (ROOT / "README.md").read_text(encoding="utf-8")

    def test_readme_exists(self) -> None:
        assert (ROOT / "README.md").is_file(), "README.md not found"

    def test_readme_states_offline_privacy_and_side_loading(self) -> None:
        text = self._read()
        assert "fully offline" in text.lower()
        assert "no telemetry" in text.lower()
        assert "docs/MODEL-SIDELOADING.md" in text

    def test_readme_has_install_section(self) -> None:
        text = self._read()
        assert "install" in text.lower()
        assert "portable" in text.lower()

    def test_readme_links_install_release_privacy_and_real_releases_url(self) -> None:
        text = self._read()
        assert "docs/INSTALL.md" in text
        assert "docs/RELEASE.md" in text
        assert "docs/PRIVACY.md" in text
        assert self._RELEASES_URL in text
        assert "https://github.com/..." not in text

    def test_readme_states_no_runtime_model_downloads(self) -> None:
        text = self._read()
        assert "No runtime model downloads" in text


class TestLicense:
    def test_license_exists(self) -> None:
        assert (ROOT / "LICENSE").is_file(), "LICENSE not found"

    def test_license_contains_mit(self) -> None:
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        assert "MIT License" in text

    def test_license_has_copyright_holder(self) -> None:
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        assert "Spanglish Dictation" in text


class TestReleaseDocs:
    def test_install_md_exists(self) -> None:
        assert (ROOT / "docs" / "INSTALL.md").is_file()

    def test_install_md_covers_first_run_flow(self) -> None:
        text = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        required_phrases = (
            "Windows 10",
            "portable zip",
            "extract",
            "models/",
            "first launch",
            "hotkey",
            "toggle mode",
            "settings live",
            "logs live",
        )
        for phrase in required_phrases:
            assert phrase.lower() in text.lower(), f"missing install guidance: {phrase}"

    def test_release_md_exists(self) -> None:
        assert (ROOT / "docs" / "RELEASE.md").is_file()

    def test_release_md_contains_sbom(self) -> None:
        text = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        assert "SBOM" in text
        assert "LICENSES/" in text
        assert "SHA-256" in text

    def test_release_md_contains_smoke_command(self) -> None:
        text = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        assert "powershell -ExecutionPolicy Bypass -File scripts/smoke_offline.ps1" in text

    def test_release_docs_cover_prepare_release_and_manual_verification(self) -> None:
        release_text = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        checklist_text = (ROOT / "docs" / "GITHUB-RELEASE-CHECKLIST.md").read_text(
            encoding="utf-8"
        )
        required_phrases = (
            "scripts/prepare_release.ps1 -Version 0.1.0",
            "side-load",
            "offline smoke",
            "sbom",
            "checksums",
            "GitHub Releases",
        )
        for phrase in required_phrases:
            assert phrase.lower() in release_text.lower() or phrase.lower() in checklist_text.lower(), (
                f"missing release documentation phrase: {phrase}"
            )

    def test_release_md_contains_blocked_artifacts(self) -> None:
        text = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        for pattern in ("*.bin", "*.gguf", "cudnn*.dll", "cublas*.dll", "cudart*.dll"):
            assert pattern in text, f"blocked pattern {pattern!r} missing from RELEASE.md"


class TestModelSideloading:
    _SHA_BASE = "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"
    _SHA_SMALL = "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b"

    def test_sideloading_md_exists(self) -> None:
        assert (ROOT / "docs" / "MODEL-SIDELOADING.md").is_file()

    def test_sideloading_md_contains_model_filenames_and_hashes(self) -> None:
        text = (ROOT / "docs" / "MODEL-SIDELOADING.md").read_text(encoding="utf-8")
        assert "ggml-base.bin" in text
        assert "ggml-small.bin" in text
        assert self._SHA_BASE in text
        assert self._SHA_SMALL in text

    def test_sideloading_md_states_no_runtime_downloads(self) -> None:
        text = (ROOT / "docs" / "MODEL-SIDELOADING.md").read_text(encoding="utf-8")
        assert "never downloads models at runtime" in text.lower()

    def test_sideloading_md_contains_source_url(self) -> None:
        text = (ROOT / "docs" / "MODEL-SIDELOADING.md").read_text(encoding="utf-8")
        assert "huggingface.co/ggerganov/whisper.cpp" in text


class TestPrivacyDocs:
    def test_privacy_md_exists(self) -> None:
        assert (ROOT / "docs" / "PRIVACY.md").is_file()

    def test_privacy_md_contains_core_guarantees(self) -> None:
        text = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
        assert re.search(r"no\s+runtime\s+network", text, re.IGNORECASE)
        assert "no telemetry" in text.lower()
        assert "no retained audio" in text.lower()

    def test_privacy_md_contains_no_retained_transcripts(self) -> None:
        text = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
        assert "no retained transcripts" in text.lower()
        # Exact phrase from plan acceptance criteria
        assert "no retained transcripts by default" in text

    def test_privacy_md_contains_no_cloud_fallback(self) -> None:
        text = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
        assert "no cloud fallback" in text.lower()

    def test_privacy_md_contains_redacted_diagnostics(self) -> None:
        text = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
        assert "redacted" in text.lower()
