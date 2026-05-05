<#
.SYNOPSIS
    Build the portable Spanglish Dictation release zip.

.DESCRIPTION
    Runs PyInstaller in onedir mode, stages the output into a versioned
    release folder under dist/release/, enforces the blocked-artifact
    policy (no models or CUDA/cuDNN DLLs), copies licence/docs bundles,
    and creates a portable zip.

.PARAMETER SkipBuild
    Skip the PyInstaller build step — useful when dist/spanglish-dictation/
    already exists.

.PARAMETER Version
    Release version tag (default: 0.1.0).
#>

param(
    [switch]$SkipBuild,
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# ------------------------------------------------------------------
# Blocked artifact patterns (must match test_release_packaging.py)
# ------------------------------------------------------------------
# Blocked patterns: models/*, *.bin, *.gguf, cudnn*.dll, cublas*.dll, cudart*.dll
$blockedPatterns = @(
    "models*",
    "*.bin",
    "*.gguf",
    "cudnn*.dll",
    "cublas*.dll",
    "cudart*.dll"
)

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
$releaseDir = Join-Path (Join-Path $root "dist") "release"
$stagingName = "spanglish-dictation-portable-$Version"
$stagingDir = Join-Path $releaseDir $stagingName
$pyinstallerOutput = Join-Path (Join-Path $root "dist") "spanglish-dictation"

# ------------------------------------------------------------------
# Step 1 — Build with PyInstaller (onedir)
# ------------------------------------------------------------------
if (-not $SkipBuild) {
    Write-Host "Running PyInstaller onedir build..."
    python -m PyInstaller (Join-Path (Join-Path $root "packaging") "spanglish-dictation.spec") --noconfirm
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed (exit code $LASTEXITCODE)"
    }
}

if (-not (Test-Path $pyinstallerOutput)) {
    throw "PyInstaller output directory not found: $pyinstallerOutput"
}

# ------------------------------------------------------------------
# Step 2 — Prepare staging directory
# ------------------------------------------------------------------
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
if (Test-Path $stagingDir) {
    Remove-Item -Recurse -Force $stagingDir
}
Copy-Item -Recurse $pyinstallerOutput $stagingDir

# ------------------------------------------------------------------
# Step 3 — Blocked-artifact policy enforcement (fail closed)
# ------------------------------------------------------------------
$violations = Get-ChildItem -Recurse -File $stagingDir | ForEach-Object {
    $relative = $_.FullName.Substring($stagingDir.Length + 1)
    foreach ($pattern in $blockedPatterns) {
        if ($_.Name -like $pattern) {
            return $relative
        }
    }
} | Where-Object { $_ }

if ($violations) {
    $msg = "BLOCKED: The following staged files match forbidden release patterns:`n" +
           ($violations -join "`n")
    throw $msg
}

# ------------------------------------------------------------------
# Step 4 — Copy documentation and licence bundles
# ------------------------------------------------------------------
$docs = @(
    @{Src = (Join-Path $root "README.md"); Dest = (Join-Path $stagingDir "README.md")},
    @{Src = (Join-Path $root "LICENSE"); Dest = (Join-Path $stagingDir "LICENSE")}
)
foreach ($doc in $docs) {
    if (Test-Path $doc.Src) {
        Copy-Item $doc.Src $doc.Dest -Force
    }
}

$licensesSrc = Join-Path $root "LICENSES"
if (Test-Path $licensesSrc) {
    $licensesDest = Join-Path $stagingDir "LICENSES"
    Copy-Item -Recurse $licensesSrc $licensesDest -Force
}

$sbomSrc = Join-Path $releaseDir "sbom.cdx.json"
if (Test-Path $sbomSrc) {
    Copy-Item $sbomSrc (Join-Path $stagingDir "sbom.cdx.json") -Force
}

# ------------------------------------------------------------------
# Step 5 — Create portable zip (spanglish-dictation-portable-$Version.zip)
# ------------------------------------------------------------------
$zipDest = Join-Path $releaseDir "$stagingName.zip"
if (Test-Path $zipDest) {
    Remove-Item $zipDest -Force
}
Compress-Archive -Path $stagingDir -DestinationPath $zipDest -CompressionLevel Optimal
Write-Host "Release zip created: $zipDest"
