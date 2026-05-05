"""Release packaging policy tests.

Validates that blocked binary and model artifact paths are rejected,
the PyInstaller spec is well-formed, and build/smoke scripts enforce
the same policy.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


_BLOCKED_GLOBS = [
    "models/*",
    "*.bin",
    "*.gguf",
    "cudnn*.dll",
    "cublas*.dll",
    "cudart*.dll",
]


def is_blocked_release_path(path: str) -> bool:
    """Return True if *path* matches any blocked release-artifact pattern.

    Rules (no model binaries, no CUDA/cuDNN DLLs in default artifacts):

    - ``models/`` prefix → blocked
    - ``*.bin`` extension → blocked
    - ``*.gguf`` extension → blocked
    - ``cudnn*.dll`` (any directory) → blocked
    - ``cublas*.dll`` (any directory) → blocked
    - ``cudart*.dll`` (any directory) → blocked

    Everything else is allowed (data files, docs, licence notices, etc.).
    """
    name = Path(path).name

    for pattern in _BLOCKED_GLOBS:
        if "/" in pattern or "\\" in pattern:
            # directory-prefix glob: model/*
            if fnmatch.fnmatch(path.replace("\\", "/"), pattern):
                return True
        else:
            # filename-only glob
            if fnmatch.fnmatch(name, pattern):
                return True

    return False


# ------------------------------------------------------------------
# Unit tests for is_blocked_release_path
# ------------------------------------------------------------------


class TestBlockedReleasePaths:
    def test_blocks_model_binaries(self) -> None:
        assert is_blocked_release_path("models/ggml-base.bin")

    def test_blocks_gguf_files(self) -> None:
        assert is_blocked_release_path("models/whisper-large-v3.gguf")

    def test_blocks_cudnn_dll(self) -> None:
        assert is_blocked_release_path("runtime/cudnn64_9.dll")

    def test_blocks_cublas_dll(self) -> None:
        assert is_blocked_release_path("cublas64_12.dll")

    def test_blocks_cudart_dll(self) -> None:
        assert is_blocked_release_path("cudart64_12.dll")

    def test_allows_glossary_data(self) -> None:
        assert not is_blocked_release_path("data/default_glossary.json")

    def test_allows_docs(self) -> None:
        assert not is_blocked_release_path("README.md")
        assert not is_blocked_release_path("LICENSE")
        assert not is_blocked_release_path("LICENSES/THIRD-PARTY-NOTICES.md")

    def test_allows_python_scripts(self) -> None:
        assert not is_blocked_release_path("scripts/build_portable.ps1")
        assert not is_blocked_release_path("src/main.py")

    def test_blocked_binary_patterns_are_rejected(self) -> None:
        """Metatest: every documented blocked glob matches at least one
        concrete blocked path."""
        blocked_examples = {
            "models/*": ["models/ggml-base.bin", "models/ggml-small.bin"],
            "*.bin": ["somedir/model.bin", "runtime/whatever.bin"],
            "*.gguf": ["models/whisper.gguf", "ggml.gguf"],
            "cudnn*.dll": ["cudnn64_9.dll", "cudnn_ops_infer64_9.dll"],
            "cublas*.dll": ["cublas64_12.dll", "cublasLt64_12.dll"],
            "cudart*.dll": ["cudart64_12.dll"],
        }
        for glob, examples in blocked_examples.items():
            for example in examples:
                assert is_blocked_release_path(example), (
                    f"expected {glob!r} to block {example!r}"
                )


# ------------------------------------------------------------------
# Packaging spec validation
# ------------------------------------------------------------------

SPEC_PATH = Path(__file__).resolve().parent.parent / "packaging" / "spanglish-dictation.spec"
BUILD_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_portable.ps1"
SMOKE_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "smoke_offline.ps1"


class TestPackagingSpec:
    def test_spec_file_exists(self) -> None:
        assert SPEC_PATH.is_file(), f"{SPEC_PATH} not found"

    def test_spec_contains_entry_point(self) -> None:
        text = SPEC_PATH.read_text(encoding="utf-8")
        assert "main.py" in text, "spec must reference src/main.py"

    def test_spec_contains_glossary_data(self) -> None:
        text = SPEC_PATH.read_text(encoding="utf-8")
        assert "default_glossary.json" in text, (
            "spec must bundle data/default_glossary.json"
        )


# ------------------------------------------------------------------
# Build script validation
# ------------------------------------------------------------------


class TestBuildScript:
    def test_build_script_exists(self) -> None:
        assert BUILD_SCRIPT.is_file(), f"{BUILD_SCRIPT} not found"

    def test_build_script_blocks_forbidden_artifacts(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        for token in ("cudnn*.dll", "cublas*.dll", "cudart*.dll",
                       "models*", ".bin", ".gguf"):
            assert token in text.replace('"', "").replace("{", "").replace("}", ""), (
                f"build script must block '{token}'"
            )

    def test_build_script_contains_version_zip_name(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "spanglish-dictation-portable-$Version.zip" in text

    def test_build_script_has_skip_build_switch(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "SkipBuild" in text


class TestSmokeScript:
    def test_smoke_script_exists(self) -> None:
        assert SMOKE_SCRIPT.is_file(), f"{SMOKE_SCRIPT} not found"

    def test_smoke_script_runs_privacy_guard_tests(self) -> None:
        text = SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "test_privacy_guard.py" in text
        assert "test_release_packaging.py" in text

    def test_smoke_script_references_optional_verifier(self) -> None:
        text = SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "verify_release_artifacts.py" in text
