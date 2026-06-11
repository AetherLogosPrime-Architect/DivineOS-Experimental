"""Tests for the docs-architecture sync tracker.

Andrew 2026-06-10 reframe: the goal is NOT to auto-generate doc counts
(that hides drift behind machinery). The goal IS to surface drift and
route the agent to read + update docs with judgment. This module is
the substrate primitive; the briefing-row builder and pre-commit hook
that consume it land separately.

Tests cover the three load-bearing surfaces:

- ``mark_reviewed`` writes a DOCS_REVIEWED event the ledger can find.
- ``last_review`` returns the most recent event with payload intact.
- ``review_status`` composes age + churn into a stale/current verdict
  with reasons named, suitable for direct briefing-row rendering.

Empty-state behavior is verified separately: a never-reviewed substrate
must surface as stale (not silently as fresh).
"""

from __future__ import annotations

import time
from unittest.mock import patch


def test_mark_reviewed_writes_an_event_with_actor_and_payload():
    """After mark_reviewed, last_review must return the recorded payload
    with actor + timestamp + notes preserved."""
    from divineos.core.docs_review_tracker import last_review, mark_reviewed

    before = time.time()
    event_id = mark_reviewed(
        actor="aether",
        notes="walked README + ARCHITECTURE; both still current",
        files=("README.md",),
    )
    assert event_id

    last = last_review()
    assert last is not None
    assert last["actor"] == "aether"
    assert "still current" in last["notes"]
    assert last["files"] == ["README.md"]
    assert last["ts"] >= before


def test_last_review_returns_none_when_no_event_recorded(monkeypatch):
    """When the ledger has no DOCS_REVIEWED events, last_review returns
    None (NOT a stub dict). The composite review_status maps this to
    stale=True with an explanatory reason."""
    from divineos.core import docs_review_tracker

    monkeypatch.setattr(
        "divineos.core.ledger.get_events",
        lambda **_: [],
    )

    assert docs_review_tracker.last_review() is None


def test_review_status_marks_never_reviewed_as_stale(monkeypatch):
    """A never-reviewed substrate must surface stale, not fresh — the
    silent-fresh failure mode would defeat the whole gate."""
    from divineos.core import docs_review_tracker

    monkeypatch.setattr(docs_review_tracker, "last_review", lambda: None)

    status = docs_review_tracker.review_status()

    assert status["stale"] is True
    assert status["age_days"] == float("inf")
    assert "ever been recorded" in status["reason"].lower()


def test_review_status_age_axis_fires_independently(monkeypatch):
    """If review is older than threshold_days, stale=True even when
    churn is zero. Each axis is independently sufficient."""
    from divineos.core import docs_review_tracker

    monkeypatch.setattr(
        docs_review_tracker,
        "last_review",
        lambda: {
            "ts": time.time() - 30 * 86400,  # 30 days ago
            "head_sha": "abc123",
            "actor": "aether",
            "notes": "",
            "files": [],
        },
    )
    monkeypatch.setattr(docs_review_tracker, "architecture_churn_since", lambda *a, **kw: [])

    status = docs_review_tracker.review_status(threshold_days=7.0, threshold_files=100)

    assert status["stale"] is True
    assert status["age_days"] > 7.0
    assert status["churn_count"] == 0
    assert "since last review" in status["reason"]


def test_review_status_churn_axis_fires_independently(monkeypatch):
    """If too many arch files have changed since the review, stale=True
    even when the review is recent. Each axis is independently
    sufficient (the Andrew 2026-06-10 reframe — content currency is
    what matters, not just elapsed time)."""
    from divineos.core import docs_review_tracker

    monkeypatch.setattr(
        docs_review_tracker,
        "last_review",
        lambda: {
            "ts": time.time() - 60,  # 1 minute ago
            "head_sha": "abc123",
            "actor": "aether",
            "notes": "",
            "files": [],
        },
    )
    monkeypatch.setattr(
        docs_review_tracker,
        "architecture_churn_since",
        lambda *a, **kw: [f"src/divineos/x{i}.py" for i in range(30)],
    )

    status = docs_review_tracker.review_status(threshold_days=7.0, threshold_files=20)

    assert status["stale"] is True
    assert status["age_days"] < 0.01
    assert status["churn_count"] == 30
    assert "arch files changed" in status["reason"]
    assert len(status["churn_files"]) == 20  # capped


def test_review_status_returns_current_when_both_axes_pass(monkeypatch):
    """Recent review AND low churn → stale=False, reason='current'."""
    from divineos.core import docs_review_tracker

    monkeypatch.setattr(
        docs_review_tracker,
        "last_review",
        lambda: {
            "ts": time.time() - 60,
            "head_sha": "abc123",
            "actor": "aether",
            "notes": "",
            "files": [],
        },
    )
    monkeypatch.setattr(
        docs_review_tracker, "architecture_churn_since", lambda *a, **kw: ["src/divineos/x.py"]
    )

    status = docs_review_tracker.review_status(threshold_days=7.0, threshold_files=20)

    assert status["stale"] is False
    assert status["reason"] == "current"


def test_architecture_churn_calls_git_diff_with_arch_paths():
    """The churn helper must scope its git diff to ``src/divineos/``
    and ``.claude/hooks/`` — broader scope would mark every cosmetic
    change as architectural churn and false-fire the gate constantly."""
    from divineos.core import docs_review_tracker

    captured: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, **_):
        captured.append(cmd)
        return _Result()

    with patch("divineos.core.docs_review_tracker.subprocess.run", fake_run):
        docs_review_tracker.architecture_churn_since("abc123")

    assert captured, "git diff must be invoked"
    cmd = captured[0]
    assert cmd[0] == "git"
    assert "diff" in cmd
    assert "--name-only" in cmd
    assert "abc123..HEAD" in cmd
    assert "src/divineos/" in cmd
    assert ".claude/hooks/" in cmd


def test_architecture_churn_fail_soft_on_git_error():
    """Git failure must return [] rather than crashing — fail-soft
    keeps the briefing row legible when the repo state is unreadable."""
    from divineos.core import docs_review_tracker

    class _Result:
        returncode = 128
        stdout = ""
        stderr = "fatal: not a git repo"

    with patch(
        "divineos.core.docs_review_tracker.subprocess.run",
        lambda *a, **kw: _Result(),
    ):
        result = docs_review_tracker.architecture_churn_since("abc123")

    assert result == []


def test_architecture_churn_returns_empty_on_empty_commit_sha():
    """No anchor SHA → no comparison possible → empty list. Avoids
    calling git diff with a malformed range that could compare HEAD
    against the empty string."""
    from divineos.core import docs_review_tracker

    assert docs_review_tracker.architecture_churn_since("") == []
