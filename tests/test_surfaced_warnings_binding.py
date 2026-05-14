"""Regression-pin tests for the surfaced-warnings binding.

Andrew named the load-bearing failure 2026-05-14 ~06:15: recall
surfaces [!] watch-out warnings, I read them, then act as if they
didn't appear. The system worked; its outputs were not binding.

Fix: log every surfaced warning to the ledger; check for
acknowledging learn entries at dream-report render time; surface any
unacknowledged ones as the FIRST line of the report.

These tests pin the binding loop end-to-end.
"""

from __future__ import annotations

import time

from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db, log_event
from divineos.core.surfaced_warnings import (
    format_unacknowledged,
    log_surfaced_warnings,
    unacknowledged_warnings,
)


def _seed_session(monkeypatch, sid: str = "test-session-binding") -> str:
    """Force surfaced_warnings._current_session_id to return a known id."""
    import divineos.core.surfaced_warnings as sw

    monkeypatch.setattr(sw, "_current_session_id", lambda: sid)
    init_db()
    init_knowledge_table()
    return sid


def test_log_surfaced_warnings_writes_ledger_event(monkeypatch) -> None:
    """LOAD-BEARING: log_surfaced_warnings must emit SURFACED_WARNING
    events to the ledger. Without this the binding is broken."""
    sid = _seed_session(monkeypatch, "test-session-log")

    warnings = [
        {
            "id": "k-abc",
            "text": "Andrew does NOT read code at all",
            "relevance": 0.9,
            "occurrences": 4,
            "source": "lesson",
        }
    ]
    log_surfaced_warnings(warnings)

    from divineos.core.ledger import get_events

    events = [e for e in get_events(limit=200) if e.get("event_type") == "SURFACED_WARNING"]
    matching = [
        e for e in events
        if "Andrew does NOT read code" in ((e.get("payload") or {}).get("text") or "")
    ]
    assert matching, (
        "log_surfaced_warnings did not write a SURFACED_WARNING ledger event. "
        "Binding regressed."
    )


def test_unacknowledged_when_no_learn_filed(monkeypatch) -> None:
    """LOAD-BEARING: a warning surfaced with no follow-up learn entry
    must be returned by unacknowledged_warnings()."""
    sid = _seed_session(monkeypatch, "test-session-unack")

    warnings = [
        {
            "id": "k-xyz",
            "text": "specific-unique-token-for-regression-pin",
            "relevance": 0.8,
            "occurrences": 2,
            "source": "lesson",
        }
    ]
    log_surfaced_warnings(warnings)

    unack = unacknowledged_warnings(session_id=sid)
    assert unack, "Warning with no acknowledging learn entry was not flagged."
    assert any(
        "specific-unique-token-for-regression-pin"
        in ((u.get("_payload") or {}).get("text") or "")
        for u in unack
    )


def test_acknowledged_when_learn_filed_with_overlap(monkeypatch) -> None:
    """When a learn entry contains 3+ tokens overlapping the warning
    text, the warning counts as acknowledged."""
    sid = _seed_session(monkeypatch, "test-session-ack")

    warnings = [
        {
            "id": "k-overlap",
            "text": "remember regression-pin overlap acknowledgment binding token",
            "relevance": 0.8,
            "occurrences": 2,
            "source": "lesson",
        }
    ]
    log_surfaced_warnings(warnings)

    # Tiny delay so timestamp ordering is unambiguous
    time.sleep(0.01)

    log_event(
        event_type="LEARN",
        actor="aether",
        payload={
            "session_id": sid,
            "content": "filed lesson about regression-pin overlap acknowledgment token discipline",
        },
    )

    unack = unacknowledged_warnings(session_id=sid)
    matching = [
        u for u in unack
        if "regression-pin overlap acknowledgment"
        in ((u.get("_payload") or {}).get("text") or "")
    ]
    assert not matching, (
        f"Warning with overlapping learn entry was still flagged unack: {matching}"
    )


def test_acknowledged_when_learn_references_warning_id(monkeypatch) -> None:
    """An explicit ID reference in the learn content also acknowledges."""
    sid = _seed_session(monkeypatch, "test-session-id-ack")

    warnings = [
        {
            "id": "k-unique-warning-id-9876",
            "text": "totally distinct phrase here",
            "relevance": 0.7,
            "occurrences": 1,
            "source": "lesson",
        }
    ]
    log_surfaced_warnings(warnings)
    time.sleep(0.01)

    log_event(
        event_type="LEARN",
        actor="aether",
        payload={
            "session_id": sid,
            "content": "acknowledging k-unique-warning-id-9876 via direct id reference",
        },
    )

    unack = unacknowledged_warnings(session_id=sid)
    matching = [
        u for u in unack
        if "totally distinct phrase here"
        in ((u.get("_payload") or {}).get("text") or "")
    ]
    assert not matching, "ID-based acknowledgment did not register."


def test_format_unacknowledged_returns_empty_for_empty_list() -> None:
    assert format_unacknowledged([]) == ""


def test_format_unacknowledged_surfaces_count_and_text() -> None:
    fake = [
        {"_payload": {"warning_id": "id-1", "text": "warning-text-one"}},
        {"_payload": {"warning_id": "id-2", "text": "warning-text-two"}},
    ]
    rendered = format_unacknowledged(fake)
    assert "2 surfaced warning(s)" in rendered
    assert "warning-text-one" in rendered
    assert "warning-text-two" in rendered
    assert "divineos learn" in rendered, (
        "Format must point operator at the acknowledgment action."
    )


def test_paraphrase_ack_with_stemming_registers(monkeypatch) -> None:
    """LOAD-BEARING: Aletheia round-5cdc2f48c642 Finding 38 — v1
    over-flagged paraphrase acks because tokens were matched raw
    ('ignored' did not match 'ignore'; 'patterns' did not match
    'pattern'). v2 stems tokens; this test pins that paraphrase
    with stem-overlap of 2+ counts as acknowledged."""
    sid = _seed_session(monkeypatch, "test-session-paraphrase")

    warnings = [
        {
            "id": "k-paraphrase",
            "text": "I have ignored these patterns about file paths",
            "relevance": 0.8,
            "occurrences": 2,
            "source": "lesson",
        }
    ]
    log_surfaced_warnings(warnings)
    time.sleep(0.01)

    # Learn entry uses PARAPHRASE — different tense / different
    # pluralization. v1 missed this; v2 stems and catches it.
    log_event(
        event_type="LEARN",
        actor="aether",
        payload={
            "session_id": sid,
            "content": "noting the pattern I keep ignoring about file paths in my work",
        },
    )

    unack = unacknowledged_warnings(session_id=sid)
    matching = [
        u for u in unack
        if "ignored these patterns" in ((u.get("_payload") or {}).get("text") or "")
    ]
    assert not matching, (
        f"Paraphrase ack should have been recognized; v2 stemming "
        f"failed: {matching}"
    )


def test_dream_report_surfaces_unack_first(monkeypatch) -> None:
    """LOAD-BEARING: when there are unacknowledged warnings, the dream
    report's summary must include them BEFORE the consolidation phase."""
    import divineos.core.sleep as sleep_mod
    import divineos.core.surfaced_warnings as sw

    fake_unack = [
        {"_payload": {"warning_id": "id-X", "text": "load-bearing-warning-marker-text"}}
    ]
    monkeypatch.setattr(sw, "unacknowledged_warnings", lambda *a, **kw: fake_unack)

    report = sleep_mod.DreamReport(duration_seconds=1.0)
    rendered = report.summary()

    assert "load-bearing-warning-marker-text" in rendered, (
        "Unacknowledged warning did not appear in dream report."
    )
    # Order check: the warning must appear BEFORE 'Phase 1' header
    warning_pos = rendered.index("load-bearing-warning-marker-text")
    phase1_pos = rendered.index("Phase 1")
    assert warning_pos < phase1_pos, (
        "Unacknowledged warning appeared AFTER Phase 1 consolidation header. "
        "It must be the FIRST surfaced content — the load-bearing failure-mode "
        "needs a loud unmissable post-session flag, not a buried footnote."
    )
