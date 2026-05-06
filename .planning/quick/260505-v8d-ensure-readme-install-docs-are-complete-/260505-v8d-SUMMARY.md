# Quick Task 260505-v8d Summary

## Outcome

Completed all 3 plan tasks for publish readiness.

## Tasks Completed

1. **Public install and release docs**
   - Added `docs/INSTALL.md` with Windows prerequisites, portable extraction, model side-loading, first launch, hotkey flow, and local settings/log guidance.
   - Updated `README.md`, `docs/RELEASE.md`, and `docs/GITHUB-RELEASE-CHECKLIST.md` with real GitHub Releases links and end-to-end publish steps.
   - Extended `tests/test_release_docs.py` to enforce the public doc contract.

2. **Public repo hygiene**
   - Kept `.github/workflows/release.yml` tag-only and documented it as CI-time release automation only.
   - Added `.sisyphus/` to `.gitignore` and removed tracked `.sisyphus/` planning scratch from the public repo path.
   - Extended `tests/test_release_workflow.py` to guard release-only workflow behavior and `.sisyphus/` exclusion.

3. **GitHub repo + release bundle**
   - Created and pushed `https://github.com/estebanmr99/voice-to-text`.
   - Generated verified release artifacts in `dist/release/`:
     - `spanglish-dictation-portable-0.1.0.zip`
     - `sbom.cdx.json`
     - `SHA256SUMS.txt`
   - Fixed release-pipeline blockers so `scripts/prepare_release.ps1 -Version 0.1.0` now completes successfully.

## Verification

- `python -m pytest tests/test_release_docs.py -q`
- `python -m pytest tests/test_release_workflow.py -q`
- `python -m pytest tests/test_release_packaging.py -q`
- `powershell -ExecutionPolicy Bypass -File scripts/prepare_release.ps1 -Version 0.1.0`
- `gh repo view --json url,defaultBranchRef`
- `git ls-remote --heads origin`

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 3 - Blocking Issue] Fixed invalid script path joins in `prepare_release.ps1`**
   - `Join-Path` was called with too many positional arguments, which stopped release preparation before packaging.

2. **[Rule 3 - Blocking Issue] Fixed incorrect CycloneDX CLI usage**
   - The SBOM command used `-i requirements.txt`, but `-i` is the index URL flag. Updated scripts and docs to use the positional requirements file.

3. **[Rule 3 - Blocking Issue] Fixed PyInstaller spec root resolution**
   - `packaging/spanglish-dictation.spec` relied on `__file__`, then resolved the repo root incorrectly when switched to `SPECPATH`. Updated it so local release builds can find `src/main.py`.

## Commits

- `fef6403` — `test(quick-260505-v8d-publish-readiness-01): add failing install and release doc checks`
- `992937e` — `feat(quick-260505-v8d-publish-readiness-01): complete public install and release docs`
- `4ab382f` — `test(quick-260505-v8d-publish-readiness-01): add failing publish hygiene checks`
- `953f83e` — `feat(quick-260505-v8d-publish-readiness-01): make public publish hygiene explicit`
- `1d97e0c` — `fix(quick-260505-v8d-publish-readiness-01): unblock local release bundle generation`

## Notes

- No project-local skills were present under `.claude/skills` or `.agents/skills`.
- Working tree is clean after task completion.
