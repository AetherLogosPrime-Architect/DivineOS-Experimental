"""Tests for the unified todos surface.

Closes claim 2026-06-06 18:28 (T1:empirical): the OS doesn't generate
todos from observable state. The unified surface pulls preregs +
corrections + audit + claims into one ranked list. Tests cover the
load-bearing properties:

- Recognition-aware filter (CONFIRMS / RECOGNIZED titles skipped)
- Action-tier filter for claims (only T1/T2 surface)
- Source-tagged output with summary, age, priority
- summary_counts shape
- Independent source toggles via collect_todos(sources=...)
- Empty-source fallback (substrate unavailable → []) — fail-soft
"""

from __future__ import annotations

import time


def test_is_recognition_title_filters_confirms_and_recognized():
    from divineos.core.unified_todos import _is_recognition_title

    assert _is_recognition_title("CONFIRMS PR #132 — exemption path-scoped")
    assert _is_recognition_title("RECOGNIZED: the framework discipline operates")
    assert _is_recognition_title("confirms (lower-case)")
    assert not _is_recognition_title("BLOCKED: missing trailer")
    assert not _is_recognition_title("Audit found drift in extraction pipeline")
    assert not _is_recognition_title("")


def test_action_tier_rank_keeps_only_T1_T2():
    from divineos.core.unified_todos import _ACTION_TIER_RANK

    assert "T1:empirical" in _ACTION_TIER_RANK
    assert "T2:observational" in _ACTION_TIER_RANK
    assert "T3:contested" not in _ACTION_TIER_RANK
    assert "T4:speculative" not in _ACTION_TIER_RANK
    assert "T5:metaphysical" not in _ACTION_TIER_RANK


def test_audit_todos_skips_recognition_titles(monkeypatch):
    """Recognition findings (CONFIRMS / RECOGNIZED) must NOT surface as
    action items, even though they're status=OPEN in the audit store."""
    from divineos.core import unified_todos

    class _F:
        def __init__(self, fid, title, sev="INFO", cat="ARCHITECTURE"):
            self.finding_id = fid
            self.title = title
            self.severity = sev
            self.category = cat
            self.created_at = None
            self.timestamp = None

    fakes = [
        _F("find-A", "CONFIRMS PR #132 looks good"),
        _F("find-B", "RECOGNIZED — framework discipline operating"),
        _F("find-C", "Real action item — extraction pipeline drift", sev="HIGH"),
        _F("find-D", "confirms (lowercase) something"),
        _F("find-E", "Another real one", sev="MEDIUM"),
    ]
    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", lambda **_: fakes)

    items = unified_todos._audit_todos()
    ids = [i.item_id for i in items]
    assert "find-C" in ids
    assert "find-E" in ids
    assert "find-A" not in ids, "CONFIRMS must be filtered"
    assert "find-B" not in ids, "RECOGNIZED must be filtered"
    assert "find-D" not in ids, "lowercase confirms must be filtered"


def test_audit_todos_sorted_by_severity(monkeypatch):
    from divineos.core import unified_todos

    class _F:
        def __init__(self, fid, sev):
            self.finding_id = fid
            self.title = f"Item {fid}"
            self.severity = sev
            self.category = "ARCHITECTURE"
            self.created_at = None
            self.timestamp = None

    fakes = [
        _F("low-1", "LOW"),
        _F("crit-1", "CRITICAL"),
        _F("info-1", "INFO"),
        _F("high-1", "HIGH"),
        _F("med-1", "MEDIUM"),
    ]
    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", lambda **_: fakes)

    items = unified_todos._audit_todos()
    ids = [i.item_id for i in items]
    assert ids == ["crit-1", "high-1", "med-1", "low-1", "info-1"]


def test_claim_todos_filters_to_action_tiers_only(monkeypatch):
    """Claims at T3/T4/T5 are positions to track, not action items —
    they must not surface in the todos list."""
    from divineos.core import unified_todos

    fakes = [
        {"claim_id": "c-1", "tier": "T1:empirical", "statement": "real bug A"},
        {"claim_id": "c-2", "tier": "T2:observational", "statement": "observation B"},
        {"claim_id": "c-3", "tier": "T3:contested", "statement": "debate C"},
        {"claim_id": "c-4", "tier": "T4:speculative", "statement": "guess D"},
        {"claim_id": "c-5", "tier": "T5:metaphysical", "statement": "meta E"},
        {"claim_id": "c-6", "tier": "T1", "statement": "shorthand-tier F"},
    ]
    monkeypatch.setattr("divineos.core.claim_store.list_claims", lambda **_: fakes)

    items = unified_todos._claim_todos()
    ids = [i.item_id for i in items]
    assert set(ids) == {"c-1", "c-2", "c-6"}
    # T1s come before T2s (lower priority rank)
    priorities = [i.priority for i in items if i.item_id == "c-1"]
    assert priorities and priorities[0] == 1
    priorities = [i.priority for i in items if i.item_id == "c-2"]
    assert priorities and priorities[0] == 2


def test_prereg_todos_ranks_most_overdue_first(monkeypatch):
    from divineos.core import unified_todos

    now = time.time()

    class _P:
        def __init__(self, pid, review_ts, mechanism):
            self.prereg_id = pid
            self.review_ts = review_ts
            self.mechanism = mechanism
            self.created_at = review_ts - 30 * 86400
            self.actor = "aether"

    # p-a: 10 days overdue; p-b: 1 day overdue; p-c: 5 days future (not overdue)
    fakes = [
        _P("p-c", now + 5 * 86400, "future review"),
        _P("p-a", now - 10 * 86400, "very overdue"),
        _P("p-b", now - 1 * 86400, "slightly overdue"),
    ]
    monkeypatch.setattr(
        "divineos.core.pre_registrations.store.list_pre_registrations",
        lambda **_: fakes,
    )

    items = unified_todos._prereg_todos(now=now)
    ids = [i.item_id for i in items]
    # Overdue come first, sorted by most-overdue; non-overdue (priority 0) last.
    assert ids[0] == "p-a"
    assert ids[1] == "p-b"
    assert ids[2] == "p-c"


def test_collect_todos_respects_source_filter(monkeypatch):
    """Restricting to a single source must NOT call the others."""
    from divineos.core import unified_todos

    called: list[str] = []

    def fake_prereg(**_):
        called.append("prereg")
        return []

    def fake_correction(**_):
        called.append("correction")
        return []

    monkeypatch.setattr(unified_todos, "_prereg_todos", fake_prereg)
    monkeypatch.setattr(unified_todos, "_correction_todos", fake_correction)
    monkeypatch.setattr(unified_todos, "_audit_todos", lambda **_: [])
    monkeypatch.setattr(unified_todos, "_claim_todos", lambda **_: [])

    unified_todos.collect_todos(sources=("prereg",))

    assert "prereg" in called
    assert "correction" not in called


def test_summary_counts_returns_all_four_sources(monkeypatch):
    from divineos.core import unified_todos

    monkeypatch.setattr(unified_todos, "_prereg_todos", lambda **_: [object()] * 3)
    monkeypatch.setattr(unified_todos, "_correction_todos", lambda **_: [object()])
    monkeypatch.setattr(unified_todos, "_audit_todos", lambda **_: [object()] * 5)
    monkeypatch.setattr(unified_todos, "_claim_todos", lambda **_: [])

    counts = unified_todos.summary_counts()

    assert counts == {"prereg": 3, "correction": 1, "audit": 5, "claim": 0}


def test_audit_todos_fail_soft_on_store_error(monkeypatch):
    """If the audit store raises, the unified surface must return []
    rather than crashing — partial-store-availability shouldn't break
    the operator's view of the rest."""
    from divineos.core import unified_todos

    def boom(**_):
        raise RuntimeError("watchmen unavailable")

    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", boom)

    assert unified_todos._audit_todos() == []


def test_todo_item_carries_source_and_summary():
    """TodoItem is the unit of work; smoke-test the shape."""
    from divineos.core.unified_todos import TodoItem

    t = TodoItem(
        source="prereg",
        item_id="prereg-abc",
        summary="ship the thing",
        age_days=3.5,
        priority=1,
        extra={"review_ts": 12345.0},
    )
    assert t.source == "prereg"
    assert t.summary == "ship the thing"
    assert t.priority == 1


def test_collect_todos_groups_by_source_order(monkeypatch):
    """Items returned grouped by source in the order requested."""
    from divineos.core import unified_todos
    from divineos.core.unified_todos import TodoItem

    monkeypatch.setattr(
        unified_todos,
        "_prereg_todos",
        lambda **_: [TodoItem("prereg", "p1", "p", None, 0, {})],
    )
    monkeypatch.setattr(
        unified_todos,
        "_correction_todos",
        lambda **_: [TodoItem("correction", "c1", "c", None, 0, {})],
    )
    monkeypatch.setattr(
        unified_todos,
        "_audit_todos",
        lambda **_: [TodoItem("audit", "a1", "a", None, 0, {})],
    )
    monkeypatch.setattr(unified_todos, "_claim_todos", lambda **_: [])

    items = unified_todos.collect_todos(sources=("audit", "prereg", "correction"))
    sources = [i.source for i in items]
    assert sources == ["audit", "prereg", "correction"]
