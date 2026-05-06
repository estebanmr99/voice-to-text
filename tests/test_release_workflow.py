"""Release workflow and artifact verifier tests.

Validates:
- Release artifact verifier rejects missing files and blocked artifacts
- GitHub release workflow contains required triggers and assets
- Workflow does not reference model downloads or CUDA/cuDNN
- Release checklist covers pre-publish requirements
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))

import verify_release_artifacts as vra  # noqa: E402


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestReleaseVerifier:
    def test_missing_checksums_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d / "spanglish-dictation-portable-0.1.0.zip")

            found, missing, blocked = vra.verify_release_dir(d)
            assert "SHA256SUMS.txt" in missing

    def test_requires_portable_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d / "SHA256SUMS.txt")
            _write(d / "sbom.cdx.json")

            found, missing, blocked = vra.verify_release_dir(d)
            portable_missing = [m for m in missing if "portable" in m.lower()]
            assert portable_missing

    def test_verifier_rejects_blocked_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d / "spanglish-dictation-portable-0.1.0.zip")
            _write(d / "SHA256SUMS.txt")
            _write(d / "sbom.cdx.json")
            _write(d / "ggml-base.bin", "fake model")
            _write(d / "cudnn64_9.dll", "fake dll")

            found, missing, blocked = vra.verify_release_dir(d)
            assert blocked, f"blocked should not be empty, got {blocked}"
            assert any("ggml-base.bin" in b for b in blocked)
            assert any("cudnn64_9.dll" in b for b in blocked)

    def test_accepts_valid_release_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d / "spanglish-dictation-portable-0.1.0.zip")
            _write(d / "SHA256SUMS.txt", "dummy hash")
            _write(d / "sbom.cdx.json")
            lic = d / "LICENSES"
            lic.mkdir()
            _write(lic / "THIRD-PARTY-NOTICES.md", "notices")
            _write(lic / "MODEL-NOTICES.md", "model notices")

            found, missing, blocked = vra.verify_release_dir(d)
            assert not missing
            assert not blocked

    def test_rejects_nested_model_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d / "spanglish-dictation-portable-0.1.0.zip")
            _write(d / "SHA256SUMS.txt", "dummy")
            _write(d / "sbom.cdx.json")
            _write(d / "models" / "ggml-small.bin", "model")

            found, missing, blocked = vra.verify_release_dir(d)
            assert any("models" in b for b in blocked)

    def test_rejects_gguf_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write(d / "spanglish-dictation-portable-0.1.0.zip")
            _write(d / "SHA256SUMS.txt", "dummy")
            _write(d / "sbom.cdx.json")
            _write(d / "whisper-large-v3.gguf", "model")

            found, missing, blocked = vra.verify_release_dir(d)
            assert any(".gguf" in b for b in blocked)


class TestWorkflowContent:
    def _workflow_text(self) -> str:
        wf = ROOT / ".github" / "workflows" / "release.yml"
        if not wf.is_file():
            return ""
        return wf.read_text(encoding="utf-8")

    def test_workflow_has_tag_trigger(self) -> None:
        text = self._workflow_text()
        assert "tags:" in text
        assert "v*" in text or "'v*'" in text or '"v*"' in text

    def test_workflow_is_release_only_not_general_ci(self) -> None:
        text = self._workflow_text()
        assert "pull_request:" not in text
        assert "branches:" not in text
        assert "action-gh-release" in text

    def test_workflow_has_release_action(self) -> None:
        text = self._workflow_text()
        assert "softprops/action-gh-release" in text

    def test_workflow_uploads_sbom(self) -> None:
        text = self._workflow_text()
        assert "sbom.cdx.json" in text
        assert "SHA256SUMS.txt" in text

    def test_workflow_forbidden_strings_absent(self) -> None:
        text = self._workflow_text()
        for forbidden in ("huggingface-cli", "cudnn", "cublas", "cudart"):
            assert forbidden not in text, (
                f"forbidden string '{forbidden}' found in release workflow"
            )

    def test_workflow_not_contain_model_download(self) -> None:
        text = self._workflow_text()
        for forbidden in ("curl", "Invoke-WebRequest"):
            assert forbidden not in text, (
                f"forbidden download command '{forbidden}' found in release workflow"
            )


class TestReleaseChecklist:
    def _checklist_text(self) -> str:
        cl = ROOT / "docs" / "GITHUB-RELEASE-CHECKLIST.md"
        if not cl.is_file():
            return ""
        return cl.read_text(encoding="utf-8")

    def test_checklist_contains_no_bundled_models(self) -> None:
        text = self._checklist_text()
        assert "No bundled models" in text

    def test_checklist_references_sbom(self) -> None:
        text = self._checklist_text()
        assert "SBOM" in text

    def test_checklist_references_checksums(self) -> None:
        text = self._checklist_text()
        assert "SHA-256" in text or "SHA256" in text

    def test_checklist_references_smoke(self) -> None:
        text = self._checklist_text()
        assert "smoke" in text.lower() or "pytest" in text.lower()

    def test_checklist_explains_ci_time_only_network_activity(self) -> None:
        text = self._checklist_text()
        assert "ci-time" in text.lower()
        assert "no-runtime-network" in text.lower() or "no runtime network" in text.lower()

    def test_checklist_requires_sisyphus_exclusion(self) -> None:
        text = self._checklist_text()
        assert ".sisyphus/" in text
        assert "excluded" in text.lower() or "ignore" in text.lower()


class TestPublishHygiene:
    def test_gitignore_excludes_sisyphus(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".sisyphus/" in text
        assert "# .sisyphus/" not in text

    def test_release_docs_do_not_require_sisyphus(self) -> None:
        for relative in ("docs/RELEASE.md", "docs/GITHUB-RELEASE-CHECKLIST.md", "README.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            assert "required for release" not in text.lower() or ".sisyphus" not in text.lower()


class TestPrepareRelease:
    def _script_text(self) -> str:
        ps1 = ROOT / "scripts" / "prepare_release.ps1"
        if not ps1.is_file():
            return ""
        return ps1.read_text(encoding="utf-8")

    def test_prepare_release_references_generate_license_bundle(self) -> None:
        text = self._script_text()
        assert "generate_license_bundle.py" in text

    def test_prepare_release_references_build_portable(self) -> None:
        text = self._script_text()
        assert "build_portable.ps1" in text

    def test_prepare_release_creates_checksums(self) -> None:
        text = self._script_text()
        assert "SHA256" in text

    def test_prepare_release_has_version_parameter(self) -> None:
        text = self._script_text()
        assert "Version" in text

    def test_prepare_release_uses_nested_join_path_for_script_calls(self) -> None:
        text = self._script_text()
        assert 'Join-Path (Join-Path $root "scripts") "generate_license_bundle.py"' in text
        assert 'Join-Path (Join-Path $root "scripts") "build_portable.ps1"' in text
        assert 'Join-Path (Join-Path $root "scripts") "verify_release_artifacts.py"' in text

    def test_prepare_release_uses_positional_requirements_file_for_sbom(self) -> None:
        text = self._script_text()
        assert 'python -m cyclonedx_py requirements (Join-Path $root "requirements.txt") -o' in text
        assert 'python -m cyclonedx_py requirements -i (Join-Path $root "requirements.txt")' not in text
