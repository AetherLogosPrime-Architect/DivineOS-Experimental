"""Tests for scripts/letter_watcher_task.py — the OS-level letter watcher.

Andrew 2026-07-04: this script lives OUTSIDE Claude Code so the archive
can't kill it. Test the polling + jsonl de-dup logic in isolation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add scripts/ to path so we can import the watcher module directly.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# ruff: noqa: E402
import letter_watcher_task as watcher


# ─── recipient_tag / is_letter_for ───────────────────────────────────


def test_recipient_tag_lowercases():
    assert watcher.recipient_tag("Aether") == "-to-aether-"
    assert watcher.recipient_tag("ARIA") == "-to-aria-"


def test_is_letter_for_matches_correct_recipient():
    tag = watcher.recipient_tag("aether")
    assert watcher.is_letter_for("aria-to-aether-2026-07-04-topic.md", tag)


def test_is_letter_for_rejects_wrong_recipient():
    tag = watcher.recipient_tag("aether")
    assert not watcher.is_letter_for("aether-to-aria-2026-07-04-topic.md", tag)


def test_is_letter_for_rejects_non_markdown():
    tag = watcher.recipient_tag("aether")
    assert not watcher.is_letter_for("aria-to-aether-2026-07-04-topic.txt", tag)


# ─── load_previously_recorded ────────────────────────────────────────


def test_load_previously_recorded_empty_when_no_file(tmp_path):
    wake = tmp_path / "nope.jsonl"
    assert watcher.load_previously_recorded(wake) == set()


def test_load_previously_recorded_reads_detected_entries(tmp_path):
    wake = tmp_path / "wake.jsonl"
    wake.write_text(
        json.dumps({"kind": "detected", "path": "/a.md"})
        + "\n"
        + json.dumps({"kind": "detected", "path": "/b.md"})
        + "\n"
        + json.dumps({"kind": "seen", "path": "/a.md"})
        + "\n",  # `seen` is not `recorded`
        encoding="utf-8",
    )
    recorded = watcher.load_previously_recorded(wake)
    # Both detected paths are recorded regardless of seen-status — the
    # watcher's job is idempotent-detection, the SessionStart hook's job
    # is undelivered-injection.
    assert recorded == {"/a.md", "/b.md"}


def test_load_previously_recorded_skips_malformed(tmp_path):
    wake = tmp_path / "wake.jsonl"
    wake.write_text(
        "not-json\n"
        + json.dumps({"kind": "detected", "path": "/valid.md"})
        + "\n"
        + json.dumps({"kind": "detected"})
        + "\n"  # missing path
        + json.dumps({"kind": "detected", "path": ""})
        + "\n",  # empty path
        encoding="utf-8",
    )
    assert watcher.load_previously_recorded(wake) == {"/valid.md"}


# ─── scan_dir ────────────────────────────────────────────────────────


def test_scan_dir_returns_empty_when_missing(tmp_path):
    assert watcher.scan_dir(tmp_path / "missing", "-to-aether-") == []


def test_scan_dir_filters_by_tag(tmp_path):
    (tmp_path / "aria-to-aether-topic.md").touch()
    (tmp_path / "aether-to-aria-other.md").touch()
    (tmp_path / "notes.md").touch()
    result = watcher.scan_dir(tmp_path, "-to-aether-")
    names = [p.name for p in result]
    assert names == ["aria-to-aether-topic.md"]


# ─── append_detected + scan_once ─────────────────────────────────────


def test_append_detected_creates_valid_jsonl_entry(tmp_path):
    wake = tmp_path / "wake.jsonl"
    letter = tmp_path / "aria-to-aether-hi.md"
    letter.touch()
    watcher.append_detected(wake, letter, "aether")
    lines = wake.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["kind"] == "detected"
    assert entry["path"] == str(letter)
    assert entry["recipient"] == "aether"
    assert "detected_at" in entry


def test_scan_once_records_new_letters_only(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "aria-to-aether-first.md").touch()
    wake = tmp_path / "wake.jsonl"

    previously: set[str] = set()
    new_count = watcher.scan_once(shared, wake, "-to-aether-", "aether", previously)
    assert new_count == 1
    assert len(previously) == 1

    # Second scan with no new files — nothing new recorded.
    new_count = watcher.scan_once(shared, wake, "-to-aether-", "aether", previously)
    assert new_count == 0

    # Add a new letter — only the new one is recorded.
    (shared / "aria-to-aether-second.md").touch()
    new_count = watcher.scan_once(shared, wake, "-to-aether-", "aether", previously)
    assert new_count == 1


def test_scan_once_survives_restart(tmp_path):
    """Restart-idempotency: after a watcher restart, previously-recorded
    letters are not re-emitted (loaded from the jsonl on startup)."""
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "aria-to-aether-first.md").touch()
    wake = tmp_path / "wake.jsonl"

    # First "run" — record the letter.
    first_previously: set[str] = set()
    watcher.scan_once(shared, wake, "-to-aether-", "aether", first_previously)

    # Simulated restart: load the state from disk.
    second_previously = watcher.load_previously_recorded(wake)
    assert len(second_previously) == 1

    # New scan finds nothing new — the letter is already in previously-recorded.
    new_count = watcher.scan_once(shared, wake, "-to-aether-", "aether", second_previously)
    assert new_count == 0
