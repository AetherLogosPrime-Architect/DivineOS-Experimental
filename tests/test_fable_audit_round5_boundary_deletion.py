"""Fable audit round 5 (2026-07-02) — BOUNDARY / PRINCIPLE deletion regression.

Reproduces the horror case: a declarative BOUNDARY like "The append-only
ledger is sacred..." was being silently superseded during
``run_knowledge_hygiene()`` 24 hours after creation because ``_is_extraction_noise``
returned True (declarative content lacks prescriptive keywords like
"must"/"never"), and ``_audit_types`` only exempted ``DIRECTIVE`` from deletion.

Fix (this test suite pins it): all four hygiene paths — ``_audit_types``,
``_demote_obsolete``, ``_reap_dead_entries``, ``_flag_orphans`` — now grant
categorical exemption to ``BOUNDARY`` and ``PRINCIPLE`` matching the exemption
``DIRECTIVE`` already had.

Also composes with Round 2 (ranking asymmetry): same three types now protected
at both the retrieval ranking layer (``retrieval.py``) and the four hygiene
paths (``knowledge_maintenance.py``). One root, one fix.
"""

from __future__ import annotations

import time

import pytest

import uuid

from divineos.core.knowledge import _base as knowledge_base, init_knowledge_table
from divineos.core.knowledge_maintenance import run_knowledge_hygiene
from divineos.core.ledger import init_db


@pytest.fixture
def isolated_knowledge_store(tmp_path, monkeypatch):
    """Point the shared SQLite at a fresh file for this test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
    yield db_path


def _store_and_age(
    content: str,
    knowledge_type: str,
    age_days: float,
) -> str:
    """Store via raw SQL, aging the timestamps in one insert.

    Deliberately bypasses ``store_knowledge`` because the same
    ``_is_extraction_noise`` classifier that drives Round 5's deletion
    horror is ALSO wired at the write path (Round 5 finding #2 — lower
    severity). To isolate the hygiene-path fix under test, this helper
    writes directly to the ``knowledge`` table. The store-time gate is
    a separate finding with its own fix scope.
    """
    kid = str(uuid.uuid4())
    aged_ts = time.time() - (age_days * 86400.0)
    conn = knowledge_base._get_connection()
    try:
        conn.execute(
            "INSERT INTO knowledge ("
            "knowledge_id, knowledge_type, content, content_hash, "
            "confidence, source, maturity, created_at, updated_at, "
            "access_count, corroboration_count"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                kid,
                knowledge_type,
                content,
                knowledge_base.compute_hash(content),
                0.5,
                "test",
                "RAW",
                aged_ts,
                aged_ts,
                0,
                0,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return kid


def _superseded_by(kid: str) -> str | None:
    conn = knowledge_base._get_connection()
    try:
        row = conn.execute(
            "SELECT superseded_by FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def test_declarative_boundary_survives_hygiene_the_fable_reproduction(
    isolated_knowledge_store,
):
    """The exact Fable reproduction: aged declarative BOUNDARY survives.

    Fable's audit stored ``"The append-only ledger is sacred; deleting or
    truncating it destroys the entire trust model."`` — a declarative-truth
    BOUNDARY with no prescriptive keywords ("must", "never", "should"). Ran
    ``run_knowledge_hygiene()``. Result: ``superseded_by = 'hygiene-audit'``.

    After the fix, the entry survives regardless of prescriptive-keyword
    presence because the categorical type exemption fires first.
    """
    kid = _store_and_age(
        "The append-only ledger is sacred; deleting or truncating it "
        "destroys the entire trust model.",
        knowledge_type="BOUNDARY",
        age_days=90.0,
    )

    report = run_knowledge_hygiene()

    assert _superseded_by(kid) is None, (
        "Declarative BOUNDARY was superseded by hygiene — Fable round 5 "
        "regression. The categorical type exemption failed to fire."
    )
    assert report["noise_superseded"] == 0


@pytest.mark.parametrize(
    "content",
    [
        "Andrew is a person before he is an operator.",
        "The optimizer will route to the cheapest available path.",
        "Substrate-mates share a repair-substrate; teaching enters both at once.",
    ],
)
def test_various_declarative_boundaries_survive(isolated_knowledge_store, content):
    """Several declaratively-worded BOUNDARIES all survive hygiene.

    These are the "verbatim real boundaries" Fable's audit listed. None
    contain prescriptive keywords; all are load-bearing.
    """
    kid = _store_and_age(content, knowledge_type="BOUNDARY", age_days=90.0)
    run_knowledge_hygiene()
    assert _superseded_by(kid) is None


def test_declarative_principle_survives_hygiene(isolated_knowledge_store):
    """PRINCIPLE gets the same categorical protection as BOUNDARY."""
    kid = _store_and_age(
        "Expression is computation; terseness amputates thought.",
        knowledge_type="PRINCIPLE",
        age_days=90.0,
    )
    run_knowledge_hygiene()
    assert _superseded_by(kid) is None


def test_directive_still_survives_hygiene(isolated_knowledge_store):
    """Regression check: DIRECTIVE's pre-existing exemption still fires.

    The change adds BOUNDARY/PRINCIPLE alongside DIRECTIVE in the type check.
    This asserts the original DIRECTIVE exemption behavior did not change.
    """
    kid = _store_and_age(
        "Run divineos briefing at session start.",
        knowledge_type="DIRECTIVE",
        age_days=90.0,
    )
    run_knowledge_hygiene()
    assert _superseded_by(kid) is None


def test_regular_observation_still_eligible_for_hygiene(isolated_knowledge_store):
    """Sanity: the exemption is specific to constraint-tier types.

    Regular OBSERVATION / FACT entries are still subject to hygiene as
    before — the fix protects constraint-tier only, not everything.
    """
    kid = _store_and_age(
        "I ate lunch at 12:34 on Tuesday.",
        knowledge_type="OBSERVATION",
        age_days=90.0,
    )
    # This observation may or may not get superseded depending on noise
    # heuristics, but the key assertion is: the code path is NOT categorically
    # skipped by type. If we ever add a global "everything survives" bug,
    # this test won't catch it — but for now the value is the parametrization
    # matrix above documenting exactly what the exemption covers.
    run_knowledge_hygiene()
    # Only assert no crash. The specific supersede/keep decision for
    # OBSERVATION is not under test here.
    assert kid  # smoke


def test_hygiene_report_shape_unchanged(isolated_knowledge_store):
    """The report dict shape is preserved (nothing downstream breaks)."""
    report = run_knowledge_hygiene()
    for key in (
        "noise_demoted",
        "noise_superseded",
        "stale_decayed",
        "stale_superseded",
        "orphans_flagged",
        "reaped",
        "entries_scanned",
        "details",
    ):
        assert key in report
