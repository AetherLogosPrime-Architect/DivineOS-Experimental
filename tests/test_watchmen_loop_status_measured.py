"""The loop-status line must be measured, never asserted.

THE DEFECT (2026-08-01). `watchmen_loop_status()` returned a hardcoded
sentence claiming "external-actor filing works; routing to
knowledge/claims/lessons works", printed unconditionally at the top of
`divineos audit summary`. Its own docstring named the mechanism:
"Updated manually as loop-closing features ship."

Measured against the real store before the rewrite:

    external-actor findings : 542/637 (85%)  -> filing genuinely works
    unrouted findings       : 536/637 (84%)  -> routing does NOT
    open findings           : 212

Half true. It vouched for a routing loop that had never processed 84% of
what it received, printed directly above the findings proving otherwise.

The sweep recommended deleting the line. Deletion would have thrown away
the accurate half with the false one — which is why these tests pin BOTH
verdicts independently, and pin that a blind store reports blindness
instead of reverting to reassurance.
"""

from __future__ import annotations

import sqlite3

import pytest

from divineos.core.watchmen import summary as sm


@pytest.fixture
def findings_db(tmp_path, monkeypatch):
    """Isolated audit_findings the tests can shape."""
    db = tmp_path / "findings.db"

    def _conn():
        c = sqlite3.connect(str(db))
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_findings (
                finding_id TEXT PRIMARY KEY,
                actor      TEXT,
                routed_to  TEXT,
                status     TEXT
            )
        """)
        c.commit()
        return c

    monkeypatch.setattr("divineos.core.ledger.get_connection", _conn)
    return _conn


def _add(conn_factory, fid: str, actor: str, routed_to: str = "", status: str = "OPEN"):
    c = conn_factory()
    c.execute(
        "INSERT INTO audit_findings (finding_id, actor, routed_to, status) VALUES (?,?,?,?)",
        (fid, actor, routed_to, status),
    )
    c.commit()
    c.close()


def test_reports_routing_not_closed_when_most_findings_unrouted(findings_db):
    """The half that was false. 90% unrouted must not read as 'works'."""
    for i in range(90):
        _add(findings_db, f"u{i}", "aletheia", routed_to="")
    for i in range(10):
        _add(findings_db, f"r{i}", "aletheia", routed_to="knowledge-123", status="ROUTED")

    out = sm.watchmen_loop_status()
    assert "NOT CLOSED" in out
    assert "90/100" in out


def test_reports_filing_works_when_externals_dominate(findings_db):
    """The half that was TRUE. Deleting the line wholesale would have lost
    this, which is why the fix measures rather than removes."""
    for i in range(85):
        _add(findings_db, f"e{i}", "aletheia", routed_to="k", status="ROUTED")
    for i in range(15):
        _add(findings_db, f"s{i}", "aether", routed_to="k", status="ROUTED")

    out = sm.watchmen_loop_status()
    assert "filing works" in out
    assert "85/100" in out


def test_reports_filing_thin_when_agent_files_its_own_audits(findings_db):
    """The direction the old sentence could never express. If the running
    agent files most of its own findings, external review is not happening
    and the surface has to say so."""
    for i in range(80):
        _add(findings_db, f"s{i}", "aether", routed_to="k", status="ROUTED")
    for i in range(20):
        _add(findings_db, f"e{i}", "grok", routed_to="k", status="ROUTED")

    out = sm.watchmen_loop_status()
    assert "THIN" in out
    assert "20/100" in out


def test_blind_store_reports_blindness_not_health(monkeypatch):
    """The load-bearing one. A health surface that reverts to optimism when
    it cannot see is the exact defect class this audit keeps finding. The
    old function returned its cheerful sentence regardless."""

    def _boom():
        raise sqlite3.OperationalError("store unreachable")

    monkeypatch.setattr("divineos.core.ledger.get_connection", _boom)
    out = sm.watchmen_loop_status()
    assert "UNAVAILABLE" in out
    assert "not a clean result" in out
    assert "works" not in out, "must not claim anything works while blind"


def test_unreadable_table_reports_blindness(tmp_path, monkeypatch):
    """Store opens but the table is missing — still blindness, not health."""
    db = tmp_path / "empty.db"

    def _conn():
        return sqlite3.connect(str(db))

    monkeypatch.setattr("divineos.core.ledger.get_connection", _conn)
    out = sm.watchmen_loop_status()
    assert "UNAVAILABLE" in out
    assert "works" not in out


def test_empty_store_makes_no_claim_either_way(findings_db):
    """A fresh install has filed nothing. That is neither health nor defect
    and must not be dressed as either."""
    out = sm.watchmen_loop_status()
    assert "nothing to report" in out
    assert "works" not in out
    assert "NOT CLOSED" not in out


def test_counts_print_even_when_labels_are_arguable(findings_db):
    """The thresholds behind 'works' / 'NOT CLOSED' are judgements. Raw
    counts must always print so the numbers outlive a bad label."""
    for i in range(50):
        _add(findings_db, f"x{i}", "user", routed_to="", status="OPEN")

    out = sm.watchmen_loop_status()
    assert "50/50" in out
    assert "50 findings still OPEN" in out
    assert "measured across 50 findings" in out
    # The "Loop status:" prefix is an interface other callers and tests grep
    # for. An earlier draft moved the colon into a parenthetical and broke
    # test_loop_status_labels; pinned here so it cannot drift again.
    assert out.startswith("Loop status:")
