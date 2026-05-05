# Phase 06: Packaging & Release - Research

**Status:** Complete  
**Phase:** 6 — Packaging & Release  
**Question:** What do we need to know to plan Windows release artifacts with licensing, SBOM, offline smoke tests, and GitHub release readiness?

## Phase Scope

Phase 6 covers release engineering only:

- Build a Windows portable zip that runs without admin.
- Keep model binaries and CUDA/cuDNN DLLs out of git and default release artifacts.
- Generate SBOM and license notices for runtime dependencies and local model metadata.
- Provide release documentation for model side-loading, privacy, checksums, and offline smoke testing.
- Prepare GitHub release automation/checklists without adding runtime network behavior.

## Inputs Read

- `.planning/ROADMAP.md` — Phase goal, REL-01/REL-02, success criteria.
- `.planning/REQUIREMENTS.md` — release requirements and out-of-scope constraints.
- `.planning/STATE.md` — project state, legal/privacy decisions, prior blockers.
- `.planning/architecture/ARCHITECTURE.md` — release constraints and module boundaries.
- `.planning/architecture/PRIVACY.md` — no runtime network, no telemetry, zero retention release constraints.
- `.planning/architecture/LICENSE-MATRIX.md` — conservative dependency/license release checklist.
- `pyproject.toml`, `requirements.txt` — current runtime dependency surface.
- `models/MODEL-REGISTRY.md` — model metadata, side-load guidance, checksum values.

## Findings

### Packaging Approach

- Use PyInstaller in `onedir` mode first, then zip the folder. `onedir` is easier to inspect for license notices and hidden DLLs than one-file extraction.
- Treat `data/default_glossary.json` as an explicit data asset.
- Do not include `models/`, `*.bin`, `*.gguf`, CUDA DLLs, cuDNN DLLs, or faster-whisper/CTranslate2 artifacts in the default portable zip.
- Build scripts should fail closed if blocked artifacts are present in the staged release tree.

### Offline Smoke Test

- The app already enforces `PrivacyGuard().enforce()` at the top of `src/main.py` before third-party imports.
- Existing privacy tests monkeypatch/block `socket`, `urllib.request.urlopen`, `ssl.wrap_socket`, and PySide6 QtNetwork operations when available.
- Phase 6 should add a release smoke script/test that inspects the built portable folder and runs the executable in a constrained smoke mode if available. Because no smoke CLI exists yet, the first release smoke can be artifact-based plus a Python import/privacy test.
- Release smoke should verify: executable exists, README/LICENSES/SBOM exist, blocked binaries absent, model binaries absent, and privacy tests pass.

### SBOM + Notices

- CycloneDX is the most direct SBOM format for GitHub release assets. For Python, use `cyclonedx-py` from an isolated release/dev environment against `requirements.txt` or installed environment.
- SBOM generation should be scripted and produce `dist/release/sbom.cdx.json`.
- License notices should be curated from `.planning/architecture/LICENSE-MATRIX.md`, `requirements.txt`, and `models/MODEL-REGISTRY.md`; generated output should remain conservative and mark unresolved rows as `VERIFY BEFORE RELEASE` rather than claiming approval.

### Documentation

- Repository needs `README.md` because `pyproject.toml` points to it.
- Repository needs `LICENSE` because `pyproject.toml` declares MIT.
- Release docs should explicitly state:
  - Fully offline runtime; no telemetry; no updater; no model downloads.
  - Models are side-loaded by the user unless a model bundle is separately approved.
  - `models/` is excluded from git and default portable zip.
  - CUDA/cuDNN redistribution is blocked.
  - How to verify SHA-256 checksums.

### GitHub Release Preparation

- Use `.github/workflows/release.yml` only for tag-triggered build/release asset creation. CI/network use is not runtime app network use.
- Release automation should upload portable zip, SBOM, license bundle, checksum file, and release notes.
- The workflow should not download model assets, CUDA, cuDNN, telemetry SDKs, or auto-updater tooling.

## Recommended Plan Structure

1. Portable packaging foundation and release smoke checks.
2. SBOM/license bundle generation.
3. Release documentation and legal/privacy docs.
4. GitHub release workflow and checksum verification.

## Validation Architecture

Release validation should use automated checks before any manual release:

- `python -m pytest tests/test_release_packaging.py tests/test_privacy_guard.py -q`
- `python scripts/generate_license_bundle.py --check`
- `python scripts/verify_release_artifacts.py dist/release`
- `powershell -ExecutionPolicy Bypass -File scripts/build_portable.ps1 -SkipBuild` for dry-run layout validation.

## Source Audit Seeds

| Source | Item | Plan Coverage |
|---|---|---|
| GOAL | Windows release artifacts with licensing and documentation | 06-01 through 06-04 |
| REQ REL-01 | Open source, GitHub-legal, installable without cloud/paid APIs | 06-01, 06-03, 06-04 |
| REQ REL-02 | SBOM and license notices | 06-02, 06-04 |
| RESEARCH | PyInstaller onedir portable zip | 06-01 |
| RESEARCH | Block models/CUDA/cuDNN from default artifacts | 06-01, 06-04 |
| RESEARCH | CycloneDX SBOM + conservative notices | 06-02 |
| RESEARCH | Model side-loading docs and checksums | 06-03, 06-04 |

## Out of Scope

- Runtime model downloads.
- Auto-updates.
- Telemetry/crash upload.
- Bundled model binaries in git or default portable zip.
- CUDA/cuDNN redistribution without separate legal approval.

## RESEARCH COMPLETE
