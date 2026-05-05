"""Tests for Diagnostics."""

import json
from pathlib import Path

import pytest

from diagnostics import Diagnostics


class TestDiagnosticsEventLogging:
    """Verify events are written and redacted."""

    def test_event_creates_log_file(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        diag.event("app_started")
        assert diag.get_log_path().exists()

    def test_event_contains_timestamp_and_name(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        diag.event("dictation_started")
        line = json.loads(diag.get_log_path().read_text(encoding="utf-8").strip())
        assert "t" in line
        assert line["e"] == "dictation_started"

    def test_event_redacts_values(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        diag.event("dictation_started", audio_device="Secret Microphone", transcript="hola mundo")
        raw = diag.get_log_path().read_text(encoding="utf-8")
        line = json.loads(raw.strip())
        assert "keys" in line
        assert sorted(line["keys"]) == ["audio_device", "transcript"]
        assert "Secret Microphone" not in raw
        assert "hola mundo" not in raw

    def test_multiple_events_append(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        diag.event("first")
        diag.event("second")
        lines = diag.get_log_path().read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["e"] == "first"
        assert json.loads(lines[1])["e"] == "second"


class TestDiagnosticsRotation:
    """Verify log rotation and pruning."""

    def test_rotation_on_size_limit(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        # Write a large payload to force rotation
        big = "x" * (2 * 1024 * 1024)  # 2 MB
        diag._current_log.write_text(big, encoding="utf-8")
        diag.event("after_rotation")
        # A new log file should have been started
        assert diag.get_log_path().exists()
        assert diag.get_log_path().stat().st_size < len(big)

    def test_pruning_old_files(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        # Create 12 old log files manually
        for i in range(12):
            old = tmp_path / f"app-2026-01-{i+1:02d}.log"
            old.write_text("{}", encoding="utf-8")
        diag.event("trigger_prune")
        log_files = list(tmp_path.glob("app-*.log*"))
        assert len(log_files) <= 10

    def test_no_pruning_when_under_limit(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        for i in range(3):
            old = tmp_path / f"app-2026-01-{i+1:02d}.log"
            old.write_text("{}", encoding="utf-8")
        diag.event("no_prune")
        log_files = list(tmp_path.glob("app-*.log*"))
        assert len(log_files) == 4


class TestDiagnosticsRedactionAudit:
    """Threat-model audit: transcript content must never appear in logs."""

    def test_transcript_not_in_log(self, tmp_path: Path) -> None:
        diag = Diagnostics(log_dir=tmp_path)
        diag.event("dictation_ended", transcript="este es un secreto")
        raw = diag.get_log_path().read_text(encoding="utf-8")
        assert "secreto" not in raw
        assert "transcript" in raw  # key name IS allowed
