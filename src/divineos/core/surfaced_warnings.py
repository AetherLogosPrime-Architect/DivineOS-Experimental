"""Surfaced-warnings binding — load-bearing.

Andrew named the load-bearing failure 2026-05-14 ~06:15: recall
surfaces ``[!]`` watch-out warnings, I read them, then act as if
they didn't appear. The substrate works; its outputs aren't binding.
Building more retrieval doesn't help if engaging with what it returns
remains optional.

This module makes the surfacing→acknowledgment loop structural:

  1. When recall/ask/briefing render anticipation warnings, this
     module logs each warning as a SURFACED_WARNING ledger event with
     the warning_id and session id.
  2. Acknowledgment matching is done at read-time via token-overlap
     between learn-event content and surfaced warning content within
     the same session.
  3. Dream report surfaces any still-unacknowledged warnings from the
     session as the FIRST line of the report — not buried.

The architecture enforces that I LOOK at and RESPOND to surfaced
warnings (HOW); the content of the response — what the warning means
for the work, what to learn, what to do — stays mine (WHAT). Same
shape as the council walk: forced engagement, my own walking.

Session-scoped: warnings surfaced this session are tracked against
this session id only. A new session is a clean slate; an
unacknowledged warning from this session does not chase indefinitely,
but the dream report flags it loudly so the next session inherits
the open thread.
"""

from __future__ import annotations

from pathlib import Path


def _current_session_id() -> str:
    """Read the current session id from the conventional file.

    Tests monkeypatch this function; do not inline. Returns "" if no
    session file exists (e.g. fresh install) rather than raising.
    """
    try:
        p = Path.home() / ".divineos" / "current_session.txt"
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def log_surfaced_warnings(warnings: list[dict]) -> None:
    """Record that these warnings were shown to the operator this turn.

    Called by recall/ask/briefing immediately after format_anticipation
    renders the warnings. Each warning becomes one SURFACED_WARNING
    ledger event tagged with the session id and warning_id.
    Fail-soft: any error swallowed.
    """
    if not warnings:
        return
    try:
        from divineos.core.ledger import log_event
    except Exception:  # noqa: BLE001
        return

    sid = _current_session_id() or "unknown"

    for w in warnings:
        wid = w.get("id") or "unknown"
        text_preview = (w.get("text") or "")[:200]
        try:
            log_event(
                event_type="SURFACED_WARNING",
                actor="aether",
                payload={
                    "session_id": sid,
                    "warning_id": wid,
                    "text": text_preview,
                    "relevance": w.get("relevance", 0.0),
                    "occurrences": w.get("occurrences", 0),
                    "source": w.get("source", ""),
                },
            )
        except Exception:  # noqa: BLE001
            continue


def _coerce_payload(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json

            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:  # noqa: BLE001
            pass
    return {}


def _surfaced_this_session(session_id: str) -> list[dict]:
    """All SURFACED_WARNING events tagged with this session id."""
    from divineos.core.ledger import get_events

    out: list[dict] = []
    for e in get_events(limit=500):
        if e.get("event_type") != "SURFACED_WARNING":
            continue
        payload = _coerce_payload(e.get("payload"))
        if payload.get("session_id") == session_id:
            out.append({**e, "_payload": payload})
    return out


def _learns_since(since_ts: float) -> list[dict]:
    """KNOWLEDGE_STORED / LESSON_RECORDED / LEARN events filed at or
    after the given timestamp."""
    from divineos.core.ledger import get_events

    out: list[dict] = []
    for e in get_events(limit=500):
        et = e.get("event_type") or ""
        if et not in ("KNOWLEDGE_STORED", "LESSON_RECORDED", "LEARN"):
            continue
        ts = float(e.get("timestamp") or 0)
        if ts >= since_ts:
            out.append(e)
    return out


def unacknowledged_warnings(session_id: str | None = None) -> list[dict]:
    """Return warnings surfaced this session with no acknowledging
    learn entry filed afterward.

    Acknowledgment heuristic — minimal but real:
      * Warning is acknowledged if any LEARN event filed AFTER the
        SURFACED_WARNING contains the warning_id in its content, OR
        contains 3+ tokens (length >= 4) overlapping the warning text.

    Errs toward FLAGGING unacknowledged. Over-surfacing the load-
    bearing failure-mode is the right side of the trade.
    """
    sid = session_id or _current_session_id() or "unknown"

    surfaced = _surfaced_this_session(sid)
    if not surfaced:
        return []

    earliest = min(float(s.get("timestamp") or 0) for s in surfaced)
    learns = _learns_since(earliest)
    # Learn events store their content inside the payload (no top-level
    # content field on get_events rows). Concatenate payload['content']
    # across all learns this session into a single search blob.
    learn_blob = " ".join(
        ((_coerce_payload(l.get("payload")).get("content") or "")[:500]).lower()
        for l in learns
    )

    unack: list[dict] = []
    for s in surfaced:
        payload = s["_payload"]
        wid = (payload.get("warning_id") or "").lower()
        wtext = (payload.get("text") or "").lower()

        if wid and wid != "unknown" and wid in learn_blob:
            continue

        tokens = [t for t in wtext.split() if len(t) >= 4]
        overlap = sum(1 for t in tokens if t in learn_blob)
        if overlap >= 3:
            continue

        unack.append(s)
    return unack


def format_unacknowledged(unack: list[dict]) -> str:
    """Render unacknowledged warnings for the dream report's first line."""
    if not unack:
        return ""
    lines = [
        f"!! {len(unack)} surfaced warning(s) from this session "
        "with NO acknowledging learn entry:"
    ]
    for s in unack:
        payload = s.get("_payload") or {}
        wtext = (payload.get("text") or s.get("content") or "")[:140]
        lines.append(f"   - {wtext}")
    lines.append(
        "   These are warnings the substrate flagged; ignoring them "
        "is the load-bearing failure-mode. File a `divineos learn` "
        "entry referencing the warning content to acknowledge."
    )
    return "\n".join(lines)


__all__ = [
    "format_unacknowledged",
    "log_surfaced_warnings",
    "unacknowledged_warnings",
]
