"""Tests for the open-claims briefing surface.

Pure-function tests against the real claim store. Each test sets up
its own DB via tmp_path → DIVINEOS_DB so no cross-test contamination.
"""

from __future__ import annotations

import os
import time

import pytest

from divineos.core.open_claims_surface import (
    MAX_LISTED_CLAIMS,
    MIN_OPEN_CLAIMS_TO_SURFACE,
    STALENESS_THRESHOLD_DAYS,
    _coerce_age_days,
    _to_open_claim,
    format_for_briefing,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        from divineos.core.ledger import init_db

        init_db()
        # claim_store init_claim_tables() is auto-called on first
        # file_claim/list_claims; no manual init needed.
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _file_claim(statement: str, tier: int = 2) -> str:
    from divineos.core.claim_store import file_claim

    return file_claim(statement=statement, tier=tier)


def _backdate_claim(claim_id: str, days: int) -> None:
    """Set created_at on a claim to N days ago, simulating age."""
    import sqlite3

    conn = sqlite3.connect(os.environ["DIVINEOS_DB"])
    try:
        target = time.time() - days * 86400
        conn.execute(
            "UPDATE claims SET created_at = ? WHERE claim_id = ?",
            (target, claim_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- empty / under-threshold ----------


def test_empty_store_returns_empty():
    assert format_for_briefing() == ""


def test_below_min_threshold_returns_empty():
    """Fewer than MIN_OPEN_CLAIMS_TO_SURFACE open claims → silent."""
    for i in range(MIN_OPEN_CLAIMS_TO_SURFACE - 1):
        _file_claim(f"under-threshold claim {i}")
    assert format_for_briefing() == ""


# ---------- headline behavior ----------


def test_at_min_threshold_surfaces_block():
    for i in range(MIN_OPEN_CLAIMS_TO_SURFACE):
        _file_claim(f"claim {i}: a statement long enough to be meaningful and visible")
    block = format_for_briefing()
    assert block != ""
    assert "[open claims]" in block
    assert f"{MIN_OPEN_CLAIMS_TO_SURFACE} open investigation" in block


def test_no_stale_claims_no_stale_clause():
    """When all open claims are fresh, headline doesn't mention staleness."""
    for i in range(MIN_OPEN_CLAIMS_TO_SURFACE):
        _file_claim(f"fresh claim {i} that is recent and meaningful")
    block = format_for_briefing()
    assert "older than" not in block
    assert "STALE" not in block


def test_stale_claims_surfaced_with_marker():
    cid = _file_claim("stale-investigation claim that needs resolution and attention")
    _backdate_claim(cid, days=STALENESS_THRESHOLD_DAYS + 2)
    for i in range(MIN_OPEN_CLAIMS_TO_SURFACE - 1):
        _file_claim(f"fresh claim {i} placeholder text content")
    block = format_for_briefing()
    assert "older than" in block
    assert "STALE" in block
    assert cid[:8] in block


def test_stale_count_pluralization():
    for i in range(2):
        cid = _file_claim(f"stale claim {i} text long enough to display")
        _backdate_claim(cid, days=STALENESS_THRESHOLD_DAYS + 1)
    _file_claim("fresh claim text long enough to display in the surface")
    block = format_for_briefing()
    assert "are older than" in block  # plural


# ---------- ordering and capping ----------


def test_oldest_claims_listed_first():
    youngest = _file_claim("youngest claim text content")
    middle = _file_claim("middle claim text content")
    oldest = _file_claim("oldest claim text content")
    _backdate_claim(youngest, days=1)
    _backdate_claim(middle, days=5)
    _backdate_claim(oldest, days=10)

    block = format_for_briefing()
    pos_oldest = block.find(oldest[:8])
    pos_middle = block.find(middle[:8])
    pos_youngest = block.find(youngest[:8])
    assert 0 <= pos_oldest < pos_middle < pos_youngest


def test_max_listed_cap_enforced():
    for i in range(MAX_LISTED_CLAIMS + 5):
        _file_claim(f"claim number {i:02d} distinct statement text here")
    block = format_for_briefing()
    listed = sum(1 for line in block.splitlines() if line.startswith("  - "))
    assert listed == MAX_LISTED_CLAIMS
    assert "+5 more" in block


def test_truncation_of_long_statements():
    long_text = "x" * 500
    _file_claim(long_text)
    for i in range(MIN_OPEN_CLAIMS_TO_SURFACE):
        _file_claim(f"placeholder {i} long enough to render on the surface")
    block = format_for_briefing()
    assert "..." in block
    assert "x" * 500 not in block


# ---------- contents ----------


def test_block_includes_assess_pointer():
    for i in range(MIN_OPEN_CLAIMS_TO_SURFACE):
        _file_claim(f"investigation {i} statement long enough to be meaningful")
    block = format_for_briefing()
    assert "divineos claims show" in block
    assert "assess" in block


def test_resolved_claims_excluded():
    """Closed claims must not appear in the open-investigations surface."""
    from divineos.core.claim_store import update_claim

    for i in range(MIN_OPEN_CLAIMS_TO_SURFACE + 2):
        cid = _file_claim(f"investigation {i} statement long enough to render")
        if i < 2:
            update_claim(claim_id=cid, status="RESOLVED")
    block = format_for_briefing()
    open_count = MIN_OPEN_CLAIMS_TO_SURFACE  # filed 5, resolved 2 → 3 open
    assert f"{open_count} open" in block


# ---------- helpers ----------


def test_coerce_age_days_with_none():
    assert _coerce_age_days(None, time.time()) == 0.0


def test_coerce_age_days_with_invalid():
    assert _coerce_age_days("not-a-number", time.time()) == 0.0


def test_coerce_age_days_with_future_clamps_to_zero():
    """A timestamp in the future shouldn't produce negative age."""
    assert _coerce_age_days(time.time() + 86400, time.time()) == 0.0


def test_to_open_claim_rejects_missing_statement():
    row = {"claim_id": "abc", "statement": "", "tier": 2, "created_at": time.time()}
    assert _to_open_claim(row, time.time()) is None


def test_to_open_claim_rejects_missing_id():
    row = {"claim_id": "", "statement": "valid", "tier": 2, "created_at": time.time()}
    assert _to_open_claim(row, time.time()) is None


def test_constants_sane():
    assert STALENESS_THRESHOLD_DAYS > 0
    assert MAX_LISTED_CLAIMS > 0
    assert MIN_OPEN_CLAIMS_TO_SURFACE > 0
