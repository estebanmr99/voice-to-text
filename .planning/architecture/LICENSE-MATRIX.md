# License Matrix

Status: candidate license and release matrix for Task 2. This is not legal approval. Every row must be verified before release.

## Continuation Note

`gsd-sdk` remains shell-invisible, so this license matrix is authored as a continuation artifact under `.planning/architecture/` while generated `.planning/PROJECT.md`, `.planning/config.json`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` remain pending tooling recovery.

## Release Rule

License statuses here are intentionally conservative: `candidate`, `verify before release`, or `blocked`. Do not claim licensing is fully approved until dependency versions, build artifacts, notices, and redistribution paths are reviewed.

## Matrix

| Component | Intended use | Candidate license posture | Redistribution status | Required release action |
|---|---|---|---|---|
| App license | Project source code and docs | candidate | candidate | Choose an OSI-approved app license before public release; ensure dependency compatibility. |
| Qt/PySide6 | Desktop shell, tray, floating panel, settings UI | candidate, verify before release | verify before release | Verify PySide6/Qt LGPL obligations, dynamic linking approach, notices, and installer packaging. |
| whisper.cpp | Shipping CPU ASR backend | candidate, verify before release | verify before release | Verify exact upstream license, bundled binaries, notices, and any linked acceleration libraries. |
| Whisper model weights | Local multilingual Whisper-family model assets | verify before release | verify before release | Verify model license/card, redistribution terms, source URL, checksum, size, and release asset eligibility. Do not commit models to git. |
| faster-whisper/CTranslate2 | NVIDIA dev/benchmark backend | candidate, verify before release | verify before release | Verify Python package licenses, CTranslate2 binaries, GPU runtime assumptions, and mark as optional dev/benchmark dependency. |
| CUDA/cuDNN redistribution | Optional NVIDIA runtime support | blocked | blocked | Do not redistribute CUDA/cuDNN DLLs until exact NVIDIA redistribution rights and installer obligations are approved. |
| WebRTC VAD | Default VAD backend | candidate, verify before release | verify before release | Verify package license, native binary distribution, notices, and compatibility with app license. |
| Silero VAD | Accurate/noisy-room VAD profile | candidate, verify before release | verify before release | Verify model/code licenses, PyTorch or ONNX runtime implications, model redistribution terms, and optional profile packaging. |
| sounddevice/PortAudio | Microphone capture over WASAPI | candidate, verify before release | verify before release | Verify `sounddevice` license, PortAudio license, binary wheel/native library notices, and Windows packaging. |
| pywin32 | Native Win32 hotkey, clipboard, focus, SendInput integration | candidate, verify before release | verify before release | Verify license notices and wheel redistribution behavior. |
| Installer tooling | Portable zip and later per-user Windows installer | candidate, verify before release | verify before release | Select tooling only after license review; ensure no auto-update, network checks, or admin-only install requirement. |
| Model release artifacts | Optional model bundles, checksums, registry metadata | verify before release | verify before release | Publish only approved model assets with source URL, license, checksum, size, and hardware profile docs. |

## GPL Guardrail

GPL-only dependencies are blocked unless the project deliberately chooses a GPL-compatible app license and records that decision. LGPL or permissive dependencies still require notice, linking, and redistribution review.

## Publishable Repository Constraints

Allowed in git:

- Source code after implementation phases.
- Planning docs, architecture docs, tests, benchmark harnesses, manifests, license notices, and checksums.
- Model registry metadata with source URLs and hashes.

Blocked from git:

- Model binaries.
- CUDA/cuDNN binaries unless license review later approves release packaging, and even then not in normal source history.
- Third-party binary blobs without license, source, and checksum metadata.
- Generated installer artifacts unless the release process intentionally tracks them.

## Pre-Release Checklist

- App license selected and recorded.
- SBOM generated for the exact release build.
- `LICENSES/` or equivalent notice bundle covers runtime dependencies.
- PySide6/Qt obligations verified for the packaging method.
- whisper.cpp binary/source notices verified.
- Whisper-family model asset license and redistribution verified.
- faster-whisper/CTranslate2 optional status documented.
- CUDA/cuDNN redistribution remains blocked unless explicitly approved.
- WebRTC VAD and Silero VAD dependency/model notices included.
- sounddevice/PortAudio and pywin32 notices included.
- Installer tooling license and network behavior verified.
- Release docs explain local model side-loading when model redistribution is not approved.
