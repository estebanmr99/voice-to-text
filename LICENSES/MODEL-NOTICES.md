# Model Notices

This file documents the local Whisper-family model assets that
Spanglish Dictation can use for offline transcription.

> **Model binaries are not included in git or the default portable zip.**
> Users side-load models following the instructions in
> [MODEL-SIDELOADING.md](../docs/MODEL-SIDELOADING.md).

---

## Whisper model weights

| Field | Value |
|-------|-------|
| Source | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin |
| Licence | MIT (OpenAI) |
| Redistribution | verify before release |

---

## ggml-base.bin

| Field | Value |
|-------|-------|
| File | ggml-base.bin |
| Size | 141.1 MB |
| SHA-256 | `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe` |
| Profile | CPU Portable |
| Source | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin |

---

## ggml-small.bin

| Field | Value |
|-------|-------|
| File | ggml-small.bin |
| Size | 465.0 MB |
| SHA-256 | `1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b` |
| Profile | CPU High Accuracy |
| Source | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin |

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
python -m cyclonedx_py requirements requirements.txt -o dist/release/sbom.cdx.json
```
