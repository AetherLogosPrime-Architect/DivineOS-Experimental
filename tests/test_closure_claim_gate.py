"""Regression tests for the closure-claim precommit gate.

Audit r9-21 round-3+ — prereg-e30878ce3f09. Defends the round-1 +
round-3 closure-claim-ahead-of-verification recurrence.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import check_closure_claim as ccc  # noqa: E402


@pytest.fixture
def tmp_log(tmp_path, monkeypatch):
    """Point the verifier log at a tmp path for isolation."""
    log = tmp_path / "verifier_runs.jsonl"
    monkeypatch.setattr(ccc, "_VERIFIER_LOG_PATH", log)
    yield log


def test_neutral_message_passes_with_or_without_log(tmp_log):
    ok, _ = ccc.check_commit("Just adding a typo fix.")
    assert ok


def test_closure_claim_blocks_when_no_log(tmp_log):
    ok, msg = ccc.check_commit("Audit Tier 1 #5: fully closed.")
    assert not ok
    assert "closure claim" in msg.lower()


def test_closure_claim_blocks_when_log_is_stale(tmp_log):
    tmp_log.write_text(
        json.dumps({"ts": time.time() - 4 * 3600, "cmd": "pytest"}) + "\n",
        encoding="utf-8",
    )
    ok, _ = ccc.check_commit("Round-3 closure: zero remaining orphans.")
    assert not ok


def test_closure_claim_passes_when_log_is_fresh(tmp_log):
    tmp_log.write_text(
        json.dumps({"ts": time.time(), "cmd": "pytest tests/"}) + "\n",
        encoding="utf-8",
    )
    ok, msg = ccc.check_commit("All findings fully closed.")
    assert ok, msg


def test_record_verifier_run_creates_entry(tmp_log):
    ccc._record_verifier_run("pytest tests/test_x.py")
    assert tmp_log.exists()
    line = tmp_log.read_text(encoding="utf-8").strip()
    entry = json.loads(line)
    assert entry["cmd"] == "pytest tests/test_x.py"
    assert entry["ts"] > 0


def test_find_closure_claims_extracts_phrases():
    msg = "This commit definitively closed the issue and verified clean state."
    claims = ccc.find_closure_claims(msg)
    assert any("definitively closed" in c.lower() for c in claims)
    assert any("verified clean" in c.lower() for c in claims)


def test_partial_closure_does_not_trigger(tmp_log):
    """A scoped partial-closure phrasing should NOT fire the gate."""
    msg = "Closes #45's primary site; 3 follow-ups tracked at issue 47. Test count up to 5444."
    ok, _ = ccc.check_commit(msg)
    assert ok, "scoped partial-closure language should pass without verifier log"


# V2 calibration patterns (recovered from old 50d5fa2 via auditor 5th-pass
# finding 2026-05-04). The V1 gate caught round-1 / round-3 audit-cleanup
# phrasings but missed body-building commit-summary phrasings. These tests
# pin the V2 patterns so they can't drift back.


def test_v2_all_count_noun_addressed_blocks(tmp_log):
    """V2 calibration: 'all seven friction points addressed' should fire."""
    msg = "Body-building #1-#7: all seven friction points addressed and shipped."
    ok, _ = ccc.check_commit(msg)
    assert not ok, "all-N <noun> addressed/shipped must fire the gate"


def test_v2_all_n_defenses_landed_blocks(tmp_log):
    msg = "All five structural defenses landed cleanly."
    ok, _ = ccc.check_commit(msg)
    assert not ok, "all-N defenses landed must fire the gate"


def test_v2_all_n_pre_regs_filed_blocks(tmp_log):
    msg = "all 7 pre-regs filed for body-building work."
    ok, _ = ccc.check_commit(msg)
    assert not ok, "all-N pre-regs filed (hyphenated noun) must fire the gate"


def test_v2_body_building_done_blocks(tmp_log):
    msg = "Body-building done. Ready for next session."
    ok, _ = ccc.check_commit(msg)
    assert not ok, "body-building done must fire the gate"


def test_v2_everything_landed_blocks(tmp_log):
    msg = "Everything landed; the substrate is whole."
    ok, _ = ccc.check_commit(msg)
    assert not ok, "everything landed must fire the gate"


def test_v2_passes_with_fresh_verifier_log(tmp_log):
    """V2 patterns also unblock when the verifier log is fresh —
    same gate-shape as V1, just with broader pattern coverage."""
    ccc._record_verifier_run("test:fresh-run")
    msg = "All five structural defenses landed cleanly."
    ok, _ = ccc.check_commit(msg)
    assert ok, "V2 patterns must pass with fresh verifier evidence"
