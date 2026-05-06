# Release Guide

How to build, verify, and publish a Spanglish Dictation release.

## Release checklist

This repository uses GitHub Releases for distribution, but the app itself remains fully offline at runtime. Any GitHub Actions network activity happens only during CI-time publishing.

### 0. Run the end-to-end local release command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_release.ps1 -Version 0.1.0
```

This single command runs tests, regenerates notices, builds the portable zip, creates the SBOM, writes checksums, and verifies the final release directory before you publish to GitHub Releases.

### 1. Build the portable zip

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_portable.ps1 -Version "0.1.0"
```

This runs PyInstaller in onedir mode, stages the output, enforces the blocked
artifact policy, copies documentation and licence notices, and creates
`dist/release/spanglish-dictation-portable-0.1.0.zip`.

### 2. Run the offline smoke test

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_offline.ps1
```

Verifies:

- Privacy guard regression tests pass
- Release packaging policy tests pass (blocked patterns enforced)
- If `dist/release/` exists, the artifact verifier runs

### 3. Verify licence notices

```powershell
python scripts/generate_license_bundle.py --check
```

Confirms all 13 required dependency tokens appear in `LICENSES/THIRD-PARTY-NOTICES.md`
and `LICENSES/MODEL-NOTICES.md`.

### 4. Generate SBOM

```powershell
python -m cyclonedx_py requirements -i requirements.txt -o dist/release/sbom.cdx.json
```

Produces a CycloneDX JSON SBOM covering all runtime dependencies.

### 5. Generate checksums

```powershell
Get-FileHash -Algorithm SHA256 dist/release/spanglish-dictation-portable-0.1.0.zip | Select-Object -ExpandProperty Hash > dist/release/SHA256SUMS
Get-FileHash -Algorithm SHA256 dist/release/sbom.cdx.json | Select-Object -ExpandProperty Hash >> dist/release/SHA256SUMS
```

### 6. Verify release artifacts

```powershell
python scripts/verify_release_artifacts.py dist/release
```

The verifier is the release-boundary safety gate: it fails if blocked files, missing release metadata, or incomplete assets appear in `dist/release/`.

## Side-load models before smoke verification

Before declaring the release candidate ready, side-load at least one supported Whisper model into the test machine's `models/` folder using [MODEL-SIDELOADING.md](MODEL-SIDELOADING.md). The release zip intentionally excludes models, so first-run verification must confirm that a side-loaded model works offline.

## Blocked artifacts

The following patterns are **rejected** from the default portable zip by both
the build script and the release packaging tests:

| Pattern | Reason |
|---------|--------|
| `models/` | Model binaries are user side-loaded, not bundled |
| `*.bin` | Compressed model weights |
| `*.gguf` | GGUF model format |
| `cudnn*.dll` | NVIDIA cuDNN — redistribution blocked |
| `cublas*.dll` | NVIDIA cuBLAS — redistribution blocked |
| `cudart*.dll` | NVIDIA CUDA Runtime — redistribution blocked |

## Artifact inventory

A release produces these files under `dist/release/`:

| File | Description |
|------|-------------|
| `spanglish-dictation-portable-{version}.zip` | Portable application bundle |
| `sbom.cdx.json` | CycloneDX software bill of materials |
| `SHA256SUMS` | SHA-256 checksums for all release assets |

Copied into the portable zip at build time:

- `README.md`
- `LICENSE`
- `LICENSES/` (full notice bundle)
- `sbom.cdx.json` (if present)

## Before publishing

- [ ] `powershell -ExecutionPolicy Bypass -File scripts/prepare_release.ps1 -Version 0.1.0` exits 0
- [ ] Offline smoke test passes
- [ ] Licence check passes (`--check` exits 0)
- [ ] Blocked artifact scan reports zero violations
- [ ] `SHA-256` checksums generated and verified
- [ ] Portable zip extracted and launched on a clean Windows user account
- [ ] Side-loaded model completes a real offline dictation smoke check
- [ ] Release notes drafted (see `.github/workflows/release.yml`)
- [ ] GitHub release draft created with assets attached on [GitHub Releases](https://github.com/estebanmr99/voice-to-text/releases)
