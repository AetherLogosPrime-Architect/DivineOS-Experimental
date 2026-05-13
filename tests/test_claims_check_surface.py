"""Test that `divineos claims check` is a pure review surface — no auto-mutation.

Bullet-wound-clause + code-does-not-think directives (2026-05-12). Pattern
matches `goal check` and `hold check`. The check surface sorts no-evidence
claims first because those are the most likely candidates for assessment,
but the surface does NOT filter, classify, or close anything for me. The
investigation (via `claims evidence`) and assessment (via `claims assess`)
are separate commands that record decisions I make.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.claim_store import file_claim, add_evidence


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    from divineos.core.ledger import init_db

    init_db()
    yield db


def test_claims_check_lists_open_claims(isolated_db):
    """All OPEN/INVESTIGATING/CONTESTED claims appear by default."""
    file_claim("first open claim")
    file_claim("second open claim")

    runner = CliRunner()
    result = runner.invoke(cli, ["claims", "check"])
    assert result.exit_code == 0
    assert "first open claim" in result.output
    assert "second open claim" in result.output


def test_claims_check_no_evidence_first(isolated_db):
    """Claims without evidence sort first — they're the most likely candidates
    for assessment. The surface does NOT filter; it just orders by data."""
    has_ev = file_claim("claim with evidence")
    file_claim("claim without evidence")
    add_evidence(has_ev, "supporting finding", direction="SUPPORTS", strength=0.7)

    runner = CliRunner()
    result = runner.invoke(cli, ["claims", "check"])
    assert result.exit_code == 0
    # The zero-evidence claim should appear before the one-evidence claim
    no_ev_pos = result.output.find("claim without evidence")
    has_ev_pos = result.output.find("claim with evidence")
    assert no_ev_pos != -1 and has_ev_pos != -1
    assert no_ev_pos < has_ev_pos


def test_claims_check_shows_evidence_marker(isolated_db):
    """no-evidence claims are visually marked; with-evidence shows the count."""
    file_claim("zero ev")
    cid_one = file_claim("one ev")
    add_evidence(cid_one, "ev1", direction="SUPPORTS")

    runner = CliRunner()
    result = runner.invoke(cli, ["claims", "check"])
    assert "no-evidence" in result.output
    assert "1 evidence" in result.output


def test_claims_check_does_not_mutate(isolated_db):
    """Pure-read surface — running check does not change any claim's state."""
    cid = file_claim("test claim")

    from divineos.core.claim_store import get_claim

    before = get_claim(cid)
    assert before["confidence"] == 0.5
    assert before["status"] == "OPEN"

    runner = CliRunner()
    runner.invoke(cli, ["claims", "check"])

    after = get_claim(cid)
    assert after["confidence"] == 0.5
    assert after["status"] == "OPEN"


def test_claims_check_shows_decide_affordances(isolated_db):
    """The surface names how to investigate, assess, or let-stand."""
    file_claim("anything")

    runner = CliRunner()
    result = runner.invoke(cli, ["claims", "check"])
    assert "Decide each" in result.output
    assert "claims evidence" in result.output
    assert "claims assess" in result.output


def test_claims_check_empty_state(isolated_db):
    """No active claims → friendly message, no crash."""
    runner = CliRunner()
    result = runner.invoke(cli, ["claims", "check"])
    assert result.exit_code == 0
    assert "No claims" in result.output


def test_claims_check_excludes_settled_by_default(isolated_db):
    """SUPPORTED and REFUTED claims don't appear by default — they're settled."""
    from divineos.core.claim_store import update_claim

    file_claim("still open")
    closed_cid = file_claim("already supported")
    update_claim(closed_cid, status="SUPPORTED")

    runner = CliRunner()
    result = runner.invoke(cli, ["claims", "check"])
    assert "still open" in result.output
    assert "already supported" not in result.output


def test_claims_check_all_flag_includes_settled(isolated_db):
    """--all flag opts in to seeing settled claims too."""
    from divineos.core.claim_store import update_claim

    file_claim("still open")
    closed_cid = file_claim("already supported")
    update_claim(closed_cid, status="SUPPORTED")

    runner = CliRunner()
    result = runner.invoke(cli, ["claims", "check", "--all"])
    assert "still open" in result.output
    assert "already supported" in result.output
