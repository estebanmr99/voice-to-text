<#
.SYNOPSIS
    Prepare a release by running all build, test, SBOM, and checksum steps.

.DESCRIPTION
    Runs the full release pipeline: tests → licence bundle → SBOM →
    portable build → checksums → artifact verification.

.PARAMETER Version
    Release version tag (default: 0.1.0).
#>

param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path (Join-Path $root "dist") "release"

Write-Host "=== Spanglish Dictation — Release Preparation v$Version ==="

# ------------------------------------------------------------------
# Step 1 — Run tests
# ------------------------------------------------------------------
Write-Host "`n[1/6] Running test suite..."
python -m pytest $root\tests -q
if ($LASTEXITCODE -ne 0) {
    throw "Test suite failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 2 — Generate licence bundle
# ------------------------------------------------------------------
Write-Host "`n[2/6] Generating licence bundle..."
& python (Join-Path $root "scripts" "generate_license_bundle.py") --write --output-dir (Join-Path $root "LICENSES")
if ($LASTEXITCODE -ne 0) {
    throw "Licence bundle generation failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 3 — Generate SBOM
# ------------------------------------------------------------------
Write-Host "`n[3/6] Generating SBOM..."
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
python -m cyclonedx_py requirements -i (Join-Path $root "requirements.txt") -o (Join-Path $releaseDir "sbom.cdx.json")
if ($LASTEXITCODE -ne 0) {
    throw "SBOM generation failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 4 — Build portable zip
# ------------------------------------------------------------------
Write-Host "`n[4/6] Building portable zip..."
& powershell -ExecutionPolicy Bypass -File (Join-Path $root "scripts" "build_portable.ps1") -Version $Version
if ($LASTEXITCODE -ne 0) {
    throw "Portable build failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 5 — Generate SHA-256 checksums
# ------------------------------------------------------------------
Write-Host "`n[5/6] Generating SHA-256 checksums..."
$checksumFile = Join-Path $releaseDir "SHA256SUMS.txt"
if (Test-Path $checksumFile) {
    Remove-Item $checksumFile -Force
}
Get-ChildItem -File $releaseDir | ForEach-Object {
    $hash = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash
    Add-Content -Path $checksumFile -Value "$hash  $($_.Name)"
}
Write-Host "Checksums written to SHA256SUMS.txt"

# ------------------------------------------------------------------
# Step 6 — Verify release artifacts
# ------------------------------------------------------------------
Write-Host "`n[6/6] Verifying release artifacts..."
& python (Join-Path $root "scripts" "verify_release_artifacts.py") $releaseDir
if ($LASTEXITCODE -ne 0) {
    throw "Artifact verification failed (exit $LASTEXITCODE)"
}

Write-Host "`n=== Release preparation complete ==="
Write-Host "Artifacts at: $releaseDir"
