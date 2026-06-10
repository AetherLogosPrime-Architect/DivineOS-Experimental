"""Regression-pin for the get_events ASC/DESC recency bug.

Fable 5 cross-vantage audit 2026-06-09: ``get_events`` defaulted to
``ORDER BY timestamp ASC LIMIT ?``. Four call sites
(_recent_user_corrections, _surfaced_this_session, _learns_since,
stale_engagement) treated the return as recent rows. Once the ledger
exceeded the LIMIT, those callers silently froze on the OLDEST
history:

  - duplicate-warning suppression died (current session never in window)
  - learn-since-N detection died (recent timestamps never matched)
  - correction-recency reads oldest corrections instead of most recent

The bug was invisible to every existing test because per-test DBs
never exceed the limit — with total rows < LIMIT, ASC and DESC return
identical row sets. The audit recommended this exact test shape: seed
limit+1 events, verify the newest is reachable.
"""

from __future__ import annotations

import time

import pytest

from divineos.core.ledger import get_events, init_db, log_event


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    init_db()


def _seed(n: int) -> tuple[str, str]:
    """Seed n+1 events; return (oldest_payload, newest_payload)."""
    oldest_id = ""
    newest_id = ""
    for i in range(n + 1):
        rid = f"event-{i:05d}"
        log_event("TEST_EVENT", actor="test", payload={"i": i, "tag": rid})
        if i == 0:
            oldest_id = rid
        newest_id = rid
        # Small delay to ensure distinct timestamps if storage is fast.
        time.sleep(0.001)
    return oldest_id, newest_id


def _tags(events: list[dict]) -> list[str]:
    out: list[str] = []
    for e in events:
        payload = e.get("payload") or {}
        if isinstance(payload, dict):
            t = payload.get("tag")
            if isinstance(t, str):
                out.append(t)
    return out


def test_desc_returns_newest_when_total_exceeds_limit():
    """The bug-shape the audit named: ledger > LIMIT, ask for recent
    events, expect to see them."""
    oldest, newest = _seed(10)
    rows = get_events(limit=5, order="desc")
    tags = _tags(rows)
    assert newest in tags, (
        f"order='desc' must return the newest event when total > limit. Got tags: {tags}"
    )
    assert oldest not in tags, (
        f"order='desc' with limit=5 must NOT return the oldest of 11 events. Got tags: {tags}"
    )


def test_asc_default_preserved_for_back_compat():
    """The default stays ASC — back-compat with callers that genuinely
    want oldest-first iteration."""
    oldest, newest = _seed(10)
    rows = get_events(limit=5)  # no order arg
    tags = _tags(rows)
    assert oldest in tags
    assert newest not in tags


def test_desc_with_event_type_filter():
    """The DESC path must compose with event_type filtering — that's
    the shape _surfaced_this_session and _stale_surfaced_events use."""
    for i in range(20):
        log_event("KEEP", actor="test", payload={"i": i, "tag": f"keep-{i}"})
        log_event("SKIP", actor="test", payload={"i": i, "tag": f"skip-{i}"})
        time.sleep(0.001)
    rows = get_events(limit=3, event_type="KEEP", order="desc")
    tags = _tags(rows)
    assert all(t.startswith("keep-") for t in tags)
    # Newest KEEP is keep-19; must be in the returned 3.
    assert "keep-19" in tags


def test_invalid_order_falls_back_to_asc():
    """Garbage order strings shouldn't break the query — fall through
    to ASC (safe default)."""
    oldest, _ = _seed(10)
    rows = get_events(limit=5, order="banana")
    tags = _tags(rows)
    assert oldest in tags


def test_recency_at_exact_limit_boundary():
    """At total == limit, ASC and DESC return the same row set; this
    pins that both paths still work without raising."""
    _, newest = _seed(4)  # 5 total
    desc = get_events(limit=5, order="desc")
    asc = get_events(limit=5, order="asc")
    assert len(desc) == 5
    assert len(asc) == 5
    # Newest still visible in DESC ordering.
    assert newest in _tags(desc)
