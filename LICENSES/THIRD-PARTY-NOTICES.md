# Third-Party Notices

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
