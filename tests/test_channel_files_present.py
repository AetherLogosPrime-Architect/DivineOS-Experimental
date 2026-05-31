"""Channel-files presence guard.

The 2026-05-30 disconnect bug had one root cause: the ear-watcher lived only
on a branch and a `git checkout` erased it, leaving the channel half-deaf.
This test makes that failure mode loud at CI time — if main loses any of the
three channel files, the merge fails and we know before the channel does.

The test only stats; it doesn't execute. Three files:
  family/ear_watch.py                          — the watcher itself
  .claude/hooks/ear-auto-relaunch.sh           — Stop-hook (auto-relaunch)
  .claude/hooks/ear-surface.sh                 — UserPromptSubmit surface
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

CHANNEL_FILES = [
    "family/ear_watch.py",
    "family/letter_seen.py",
    ".claude/hooks/ear-auto-relaunch.sh",
    ".claude/hooks/ear-surface.sh",
]


@pytest.mark.parametrize("rel", CHANNEL_FILES)
def test_channel_file_exists(rel: str) -> None:
    p = _REPO / rel
    assert p.exists(), (
        f"Channel file missing: {rel}. This file is load-bearing for the "
        "Aria<->Aether comms channel — losing it from main half-deafens the "
        "channel. Restore from history before merging."
    )


@pytest.mark.parametrize("rel", CHANNEL_FILES)
def test_channel_file_nonempty(rel: str) -> None:
    p = _REPO / rel
    if p.exists():
        assert p.stat().st_size > 0, f"Channel file is empty: {rel}"
