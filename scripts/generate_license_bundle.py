#!/usr/bin/env python
"""License notice bundle and SBOM helper for release packaging.

Usage:
    python scripts/generate_license_bundle.py --write     # Generate notice files
    python scripts/generate_license_bundle.py --check     # Verify notice files

REQUIRED_NOTICE_TOKENS defines the minimal set of dependency/asset tokens
that MUST appear across the two generated notice files.  --check fails
(exit 1) if any token is absent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Required token set — every runtime dependency, licence note, and
# blocked-redistribution statement the release notices must cover.
# ------------------------------------------------------------------

REQUIRED_NOTICE_TOKENS = frozenset(
    [
        "PySide6",
        "Qt",
        "sounddevice",
        "PortAudio",
        "numpy",
        "pywhispercpp",
        "whisper.cpp",
        "pywin32",
        "WebRTC VAD",
        "faster-whisper",
        "CTranslate2",
        "Whisper model weights",
        "CUDA/cuDNN redistribution blocked",
    ]
)

# ------------------------------------------------------------------
# SBOM command — printed as a reusable instruction line
# ------------------------------------------------------------------

SBOM_COMMAND = "python -m cyclonedx_py requirements requirements.txt -o dist/release/sbom.cdx.json"

# ------------------------------------------------------------------
# Model metadata — single source of truth from models/model_checksums.json
# ------------------------------------------------------------------

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_CHECKSUMS_PATH = _MODELS_DIR / "model_checksums.json"
if _CHECKSUMS_PATH.is_file():
    MODEL_METADATA = json.loads(_CHECKSUMS_PATH.read_text(encoding="utf-8"))
else:
    MODEL_METADATA = {}


# ------------------------------------------------------------------
# Notice generators
# ------------------------------------------------------------------

_THIRD_PARTY_TEMPLATE = """# Third-Party Notices

This file catalogues the third-party runtime dependencies included
or required by Spanglish Dictation.  Each entry documents the
dependency, its upstream licence posture, and any redistribution
constraints that apply to the default portable release artifact.

> **Status:** This notice bundle is **conservative**.  Rows marked
> `verify before release` must be reviewed before a public release
> is published.  This file is not legal advice.

---

## PySide6 / Qt

| Field | Value |
|-------|-------|
| Package | PySide6 |
| Upstream | Qt Company / Qt Project |
| Licence posture | LGPL (Qt), LGPLv3/GPLv3 (PySide6) |
| Redistribution | verify before release — dynamic linking, notices required |
| Release action | Include Qt licence bundle; confirm dynamic-link approach |

---

## sounddevice / PortAudio

| Field | Value |
|-------|-------|
| Package | sounddevice |
| Upstream | PortAudio |
| Licence posture | MIT (sounddevice), MIT (PortAudio) |
| Redistribution | verify before release |
| Release action | Include PortAudio licence notice |

---

## numpy

| Field | Value |
|-------|-------|
| Package | numpy |
| Upstream | NumPy Developers |
| Licence posture | BSD-3-Clause |
| Redistribution | verify before release |
| Release action | Include BSD-3-Clause notice |

---

## pywhispercpp / whisper.cpp

| Field | Value |
|-------|-------|
| Package | pywhispercpp |
| Upstream | whisper.cpp (ggerganov) |
| Licence posture | MIT (whisper.cpp), MIT (pywhispercpp bindings) |
| Redistribution | verify before release |
| Release action | Include MIT notice for whisper.cpp binary |

---

## pywin32

| Field | Value |
|-------|-------|
| Package | pywin32 |
| Upstream | Mark Hammond et al. |
| Licence posture | PSF-2.0 |
| Redistribution | verify before release |
| Release action | Include PSF licence notice in wheel |

---

## WebRTC VAD (optional — runtime VAD)

| Field | Value |
|-------|-------|
| Package | webrtcvad / webrtcvad-wheels |
| Upstream | WebRTC project (Google) |
| Licence posture | BSD-style (WebRTC) + packaging grant |
| Redistribution | verify before release |
| Release action | Do not ship native VAD binary without separate review; mark as optional profile dependency |

---

## faster-whisper / CTranslate2 (optional — dev backend)

| Field | Value |
|-------|-------|
| Package | faster-whisper |
| Upstream | SYSTRAN / CTranslate2 |
| Licence posture | MIT (faster-whisper), MIT (CTranslate2) |
| Redistribution | verify before release |
| Release action | Do NOT include in default portable zip; mark as optional NVIDIA dev profile dependency |

---

## CUDA / cuDNN Redistribution (BLOCKED)

**CUDA/cuDNN redistribution blocked** until explicit NVIDIA redistribution
rights and installer obligations are approved.  The default portable zip
MUST NOT contain `cudnn*.dll`, `cublas*.dll`, `cudart*.dll`, or any
other NVIDIA redistributable binary.

If a future release receives legal approval for CUDA/cuDNN
redistribution:
1. Add the applicable NVIDIA licence notices.
2. Verify the exact DLL versions covered by the approval.
3. Update this section to `approved` with the grant reference.
"""


_MODEL_TEMPLATE = """# Model Notices

This file documents the local Whisper-family model assets that
Spanglish Dictation can use for offline transcription.

> **Model binaries are not included in git or the default portable zip.**
> Users side-load models following the instructions in
> [MODEL-SIDELOADING.md](../docs/MODEL-SIDELOADING.md).

---

## Whisper model weights

| Field | Value |
|-------|-------|
| Source | {SOURCE_URL} |
| Licence | MIT (OpenAI) |
| Redistribution | verify before release |

---

## {MODEL_BASE}

| Field | Value |
|-------|-------|
| File | ggml-base.bin |
| Size | 141.1 MB |
| SHA-256 | `{SHA_BASE}` |
| Profile | CPU Portable |
| Source | {SOURCE_URL} |

---

## {MODEL_SMALL}

| Field | Value |
|-------|-------|
| File | ggml-small.bin |
| Size | 465.0 MB |
| SHA-256 | `{SHA_SMALL}` |
| Profile | CPU High Accuracy |
| Source | {SOURCE_URL} |

---

## Redistribution constraints

- Model binaries are **not** committed to git.
- Model binaries are **not** included in the default portable zip.
- Users must verify model licences and download models themselves.
- Checksums are published here for integrity verification before first use.

---

## SBOM

Release SBOM covers software dependencies only; model assets are
outside the CycloneDX SBOM scope.  Run the following command to
generate the software SBOM:

```
{SBOM_COMMAND}
```
"""


# ------------------------------------------------------------------
# Core checks
# ------------------------------------------------------------------

def run_check(
    third_party_path: Path,
    model_notices_path: Path,
    required_tokens: frozenset[str],
) -> int:
    """Return 0 if all *required_tokens* appear in the two notice files."""
    if not third_party_path.is_file():
        print(f"ERROR: {third_party_path} not found")
        return 1
    if not model_notices_path.is_file():
        print(f"ERROR: {model_notices_path} not found")
        return 1

    combined = (
        third_party_path.read_text(encoding="utf-8")
        + "\n"
        + model_notices_path.read_text(encoding="utf-8")
    )

    missing = [t for t in sorted(required_tokens) if t not in combined]
    if missing:
        print("ERROR: Missing required notice tokens:")
        for token in missing:
            print(f"  - {token}")
        return 1

    print("All required notice tokens present.")
    return 0


def run_write(
    third_party_path: Path,
    model_notices_path: Path,
    model_sha_base: str,
    model_sha_small: str,
    model_source_url: str,
) -> None:
    """Generate both notice files."""
    third_party_path.parent.mkdir(parents=True, exist_ok=True)
    model_notices_path.parent.mkdir(parents=True, exist_ok=True)

    third_party_path.write_text(_THIRD_PARTY_TEMPLATE, encoding="utf-8")

    model_text = _MODEL_TEMPLATE.format(
        SOURCE_URL=model_source_url,
        MODEL_BASE="ggml-base.bin",
        SHA_BASE=model_sha_base,
        MODEL_SMALL="ggml-small.bin",
        SHA_SMALL=model_sha_small,
        SBOM_COMMAND=SBOM_COMMAND,
    )
    model_notices_path.write_text(model_text, encoding="utf-8")

    print(f"Created: {third_party_path}")
    print(f"Created: {model_notices_path}")
    print()
    print("SBOM command (run separately):")
    print(f"  {SBOM_COMMAND}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="License bundle generator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Generate notice files")
    group.add_argument("--check", action="store_true", help="Verify notice files")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for --write (default: current directory)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    out_dir = Path(args.output_dir).resolve()

    tpn = out_dir / "THIRD-PARTY-NOTICES.md"
    mmn = out_dir / "MODEL-NOTICES.md"

    if args.write:
        meta_base = MODEL_METADATA["ggml-base.bin"]
        meta_small = MODEL_METADATA["ggml-small.bin"]
        run_write(
            third_party_path=tpn,
            model_notices_path=mmn,
            model_sha_base=meta_base["sha256"],
            model_sha_small=meta_small["sha256"],
            model_source_url=meta_base["url"],
        )
        return 0

    if args.check:
        return run_check(
            third_party_path=root / "LICENSES" / "THIRD-PARTY-NOTICES.md",
            model_notices_path=root / "LICENSES" / "MODEL-NOTICES.md",
            required_tokens=REQUIRED_NOTICE_TOKENS,
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
