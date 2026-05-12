#!/usr/bin/env python
"""Interactive eval clip recording tool.

Reads ground-truth phrases from data/eval/transcripts.jsonl, displays each
phrase, waits for Enter, records 3 seconds of audio via sounddevice, and
saves data/eval/{id}.wav (16 kHz mono float32).

Usage:
    python scripts/record_eval_clips.py [--device INDEX]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
except ImportError as exc:
    print(f"ERROR: sounddevice is required — install with: pip install sounddevice\n  ({exc})")
    sys.exit(1)

_EVAL_DIR = Path(__file__).resolve().parent.parent / "data" / "eval"
_TRANSCRIPTS_PATH = _EVAL_DIR / "transcripts.jsonl"
_SAMPLE_RATE = 16000
_DURATION = 3  # seconds


def _load_transcripts(path: Path) -> list[dict[str, object]]:
    """Load transcripts.jsonl and return list of entry dicts."""
    if not path.is_file():
        print(f"ERROR: Transcripts file not found: {path}")
        print("  Run this script from the project root, or ensure data/eval/ exists.")
        sys.exit(1)

    entries: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def record_clip(device: int | None, clip_id: str, text: str) -> bool:
    """Record one clip.  Returns True on success."""
    print(f"\n--- Clip {clip_id} ---")
    print(f"  Say: {text}")
    input("  Press Enter when ready to record...")

    try:
        print(f"  Recording {_DURATION} seconds...")
        recording = sd.rec(
            int(_DURATION * _SAMPLE_RATE),
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype=np.float32,
            device=device,
        )
        sd.wait()
        print("  Done.")
    except Exception as exc:
        print(f"  ERROR: Recording failed: {exc}")
        return False

    out_path = _EVAL_DIR / f"{clip_id}.wav"
    try:
        _write_wav(out_path, recording, _SAMPLE_RATE)
        print(f"  Saved: {out_path}")
        return True
    except Exception as exc:
        print(f"  ERROR: Failed to write WAV: {exc}")
        return False


def _write_wav(path: Path, data: np.ndarray, sample_rate: int) -> None:
    """Write mono float32 [-1, 1] numpy array to a 16-bit PCM WAV file."""
    # Convert float32 [-1, 1] to int16
    data_int16 = (data * 32767).clip(-32768, 32767).astype(np.int16)

    import struct
    n_samples = data_int16.shape[0]
    n_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * n_channels * bits_per_sample // 8
    block_align = n_channels * bits_per_sample // 8
    data_size = n_samples * block_align

    with path.open("wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # chunk size
        f.write(struct.pack("<H", 1))   # PCM
        f.write(struct.pack("<H", n_channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", byte_rate))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits_per_sample))
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(data_int16.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record eval audio clips from reference transcripts."
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Input device index (default: system default)",
    )
    args = parser.parse_args()

    if args.device is not None:
        print(f"Using device index: {args.device}")
    else:
        print("Using system default input device.")
        print("Available devices:")
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_input_channels"] > 0:
                    print(f"  {i}: {dev['name']}")
        except Exception:
            pass
        print()

    _EVAL_DIR.mkdir(parents=True, exist_ok=True)
    entries = _load_transcripts(_TRANSCRIPTS_PATH)

    print(f"Found {len(entries)} clips to record.\n")

    successes = 0
    failures = 0
    start_time = time.time()

    for entry in entries:
        clip_id = str(entry.get("id", ""))
        text = str(entry.get("text", ""))
        ok = record_clip(args.device, clip_id, text)
        if ok:
            successes += 1
        else:
            failures += 1

    elapsed = time.time() - start_time
    print(f"\n=== Summary ===")
    print(f"  Recorded: {successes}/{len(entries)}")
    if failures:
        print(f"  Failed:   {failures}")
    print(f"  Time:     {elapsed:.1f}s")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
