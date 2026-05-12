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

Write-Host "=== Spanglish Dictation - Release Preparation v$Version ==="

# ------------------------------------------------------------------
# Step 1 - Run tests
# ------------------------------------------------------------------
Write-Host "`n[1/8] Running test suite..."
python -m pytest $root\tests -q
if ($LASTEXITCODE -ne 0) {
    throw "Test suite failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 2 - Generate licence bundle
# ------------------------------------------------------------------
Write-Host "`n[2/8] Generating licence bundle..."
& python (Join-Path (Join-Path $root "scripts") "generate_license_bundle.py") --write --output-dir (Join-Path $root "LICENSES")
if ($LASTEXITCODE -ne 0) {
    throw "Licence bundle generation failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 3 - Generate SBOM
# ------------------------------------------------------------------
Write-Host "`n[3/8] Generating SBOM..."
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
python -m cyclonedx_py requirements (Join-Path $root "requirements.txt") -o (Join-Path $releaseDir "sbom.cdx.json")
if ($LASTEXITCODE -ne 0) {
    throw "SBOM generation failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 4 - Build portable zip
# ------------------------------------------------------------------
Write-Host "`n[4/8] Building portable zip..."
& powershell -ExecutionPolicy Bypass -File (Join-Path (Join-Path $root "scripts") "build_portable.ps1") -Version $Version
if ($LASTEXITCODE -ne 0) {
    throw "Portable build failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 5 - Generate SHA-256 checksums
# ------------------------------------------------------------------
Write-Host "`n[5/8] Generating SHA-256 checksums..."
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
# Step 6 - Verify release artifacts
# ------------------------------------------------------------------
Write-Host "`n[6/8] Verifying release artifacts..."
& python (Join-Path (Join-Path $root "scripts") "verify_release_artifacts.py") $releaseDir
if ($LASTEXITCODE -ne 0) {
    throw "Artifact verification failed (exit $LASTEXITCODE)"
}

# ------------------------------------------------------------------
# Step 7 - Verify model integrity
# ------------------------------------------------------------------
Write-Host "`n[7/8] Running model integrity checks..."
python -m pytest (Join-Path (Join-Path $root "tests") "test_model_integrity.py") -q
if ($LASTEXITCODE -ne 0) {
    throw "Model integrity checks failed (exit $LASTEXITCODE)"
}

# Optional: verify local model file hashes if models are present
$checksumsPath = Join-Path $root "models" "model_checksums.json"
if (Test-Path $checksumsPath) {
    $checksums = Get-Content $checksumsPath -Raw | ConvertFrom-Json
    Get-ChildItem (Join-Path $root "models") -Filter "*.bin" | ForEach-Object {
        $hash = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower()
        $expected = $checksums.$($_.Name).sha256
        if ($hash -ne $expected) {
            throw "Model integrity FAILED: $($_.Name) hash mismatch (expected $expected, got $hash)"
        }
        Write-Host "  $($_.Name): SHA-256 OK"
    }
}

# ------------------------------------------------------------------
# Step 8 - Transcription quality eval (optional)
# ------------------------------------------------------------------
$evalDir = Join-Path $root "data" "eval"
$hasEvalWavs = (Get-ChildItem $evalDir -Filter "*.wav" -ErrorAction SilentlyContinue).Count -gt 0
$hasModels = (Get-ChildItem (Join-Path $root "models") -Filter "*.bin" -ErrorAction SilentlyContinue).Count -gt 0

if ($hasEvalWavs -and $hasModels) {
    Write-Host "`n[8/8] Running transcription quality eval..."
    # Pick the first available model
    $modelFile = Get-ChildItem (Join-Path $root "models") -Filter "*.bin" | Select-Object -First 1
    python (Join-Path (Join-Path $root "scripts") "eval_transcription.py") `
        --model-path $modelFile.FullName `
        --data-dir $evalDir
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 2) {
        throw "Transcription eval failed (exit $LASTEXITCODE)"
    }
    if ($LASTEXITCODE -eq 2) {
        Write-Host "  (eval skipped - no processable clips)"
    }
} else {
    Write-Host "`n[8/8] Skipped - eval requires model files + WAV clips in data/eval/"
}

Write-Host "`n=== Release preparation complete ==="
Write-Host "Artifacts at: $releaseDir"
