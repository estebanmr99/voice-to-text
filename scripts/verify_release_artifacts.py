#!/usr/bin/env python
"""Release artifact verifier.

Usage:
    python scripts/verify_release_artifacts.py dist/release

Scans a release directory and checks:
  - Required files exist (portable zip, SBOM, checksums)
  - Blocked artifact patterns are absent (models, GPU DLLs)
  - Licence notice files are present when LICENSES/ exists

Exit 0 on success, 1 on failure.
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Blocked patterns — must match test_release_packaging.py
# ------------------------------------------------------------------

_BLOCKED_GLOBS = [
    "models/*",
    "*.bin",
    "*.gguf",
    "cudnn*.dll",
    "cublas*.dll",
    "cudart*.dll",
]

_REQUIRED_PATTERNS = [
    "spanglish-dictation-portable-*.zip",
    "sbom.cdx.json",
    "SHA256SUMS.txt",
]

# ------------------------------------------------------------------
# Core verification
# ------------------------------------------------------------------


def _is_blocked(path: str) -> bool:
    name = Path(path).name
    for pattern in _BLOCKED_GLOBS:
        if "/" in pattern or "\\" in pattern:
            if fnmatch.fnmatch(path.replace("\\", "/"), pattern):
                return True
        else:
            if fnmatch.fnmatch(name, pattern):
                return True
    return False


def _match_required(release_dir: Path, pattern: str) -> bool:
    return any(release_dir.glob(pattern))


def verify_release_dir(release_dir: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (found, missing, blocked) file paths.

    Args:
        release_dir: Path to the release directory to verify.

    Returns:
        Tuple of:
        - found: relative paths of files found
        - missing: descriptions of required items not found
        - blocked: relative paths of blocked artifacts found
    """
    found: list[str] = []
    missing: list[str] = []
    blocked: list[str] = []

    # Check required patterns
    for pattern in _REQUIRED_PATTERNS:
        matches = list(release_dir.glob(pattern))
        if matches:
            for m in matches:
                found.append(str(m.relative_to(release_dir)))
        else:
            missing.append(pattern)

    # Check licence notices if LICENSES/ exists
    licenses_dir = release_dir / "LICENSES"
    if licenses_dir.is_dir():
        for notice in ("THIRD-PARTY-NOTICES.md", "MODEL-NOTICES.md"):
            notice_path = licenses_dir / notice
            if notice_path.is_file():
                found.append(str(notice_path.relative_to(release_dir)))
            else:
                missing.append(f"LICENSES/{notice}")

    # Scan for blocked artifacts
    for entry in release_dir.rglob("*"):
        if not entry.is_file():
            continue
        rel = str(entry.relative_to(release_dir)).replace("\\", "/")
        if _is_blocked(rel):
            blocked.append(rel)

    return found, missing, blocked


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        print(f"Usage: python {argv[0]} <release_dir>")
        return 1

    release_dir = Path(argv[1]).resolve()
    if not release_dir.is_dir():
        print(f"ERROR: {release_dir} is not a directory")
        return 1

    found, missing, blocked = verify_release_dir(release_dir)

    print(f"Scanning: {release_dir}")
    print()

    if found:
        print(f"Found ({len(found)}):")
        for f in sorted(found):
            print(f"  {f}")
        print()

    exit_code = 0

    if missing:
        exit_code = 1
        print(f"MISSING ({len(missing)}):")
        for m in sorted(missing):
            print(f"  {m}")
        print()

    if blocked:
        exit_code = 1
        print(f"BLOCKED ({len(blocked)}):")
        for b in sorted(blocked):
            print(f"  {b}")
        print()

    if not missing and not blocked:
        print("All required release artifacts present — no blocked files detected.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
