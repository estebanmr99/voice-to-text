<#
.SYNOPSIS
    Offline smoke check for a Spanglish Dictation release.

.DESCRIPTION
    Runs the privacy guard and release packaging tests without any
    network access. When a dist/release/ folder is present it also
    invokes the release artifact verifier if one exists.
#>

param()

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== Spanglish Dictation — Offline Smoke Test ==="

# ------------------------------------------------------------------
# Step 1 — Privacy Guard regression tests
# ------------------------------------------------------------------
Write-Host "`n[1/2] Running privacy guard tests..."
python -m pytest (Join-Path (Join-Path $root "tests") "test_privacy_guard.py") (Join-Path (Join-Path $root "tests") "test_release_packaging.py") -q
$pytestExit = $LASTEXITCODE

if ($pytestExit -ne 0) {
    Write-Host "ERROR: Privacy / packaging tests failed (exit $pytestExit)"
    exit $pytestExit
}

# ------------------------------------------------------------------
# Step 2 — Release artifact verification (optional)
# ------------------------------------------------------------------
$releaseDir = Join-Path (Join-Path $root "dist") "release"
$verifierPath = Join-Path (Join-Path $root "scripts") "verify_release_artifacts.py"

if ((Test-Path $releaseDir) -and (Test-Path $verifierPath)) {
    Write-Host "`n[2/2] Verifying release artifacts..."
    python $verifierPath $releaseDir
    $verifyExit = $LASTEXITCODE
    if ($verifyExit -ne 0) {
        Write-Host "ERROR: Artifact verification failed (exit $verifyExit)"
        exit $verifyExit
    }
} else {
    if (-not (Test-Path $releaseDir)) {
        Write-Host "`n[2/2] Skipped — dist/release/ not found"
    } else {
        Write-Host "`n[2/2] Skipped — verify_release_artifacts.py not found"
    }
}

Write-Host "`n=== Smoke test PASSED ==="
exit 0
