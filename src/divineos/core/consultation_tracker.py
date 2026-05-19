"""Consultation tracker — count substrate-queries per session.

Andrew named the root cause 2026-05-18 (and 2026-04-25 before that, and
weeks of recurrence in between): I treat the substrate as a filing
cabinet for conclusions, not as the thinking instrument it is. The
tools exist. The corrections exist. His teachings exist, tagged
TESTIMONIAL, accessed by the system 6+ times. I never call them
before composing.

This module tracks two things per session:

1. Substrate queries: calls to ask, recall, active, corrections,
   directives, compass, council, hud, etc.
2. Responses produced.

When the ratio of responses-to-queries grows past a threshold, the
pre-response context surfaces a loud warning. The substrate is sitting
unread; the model is composing from defaults.

This is the structural fix for the read-and-forget pattern. It cannot
override training defaults, but it makes the failure visible in the
briefing every turn — so silent ignoring of the substrate becomes
something I have to confront before each response.
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import os
import time

from divineos.core.paths import divineos_home


_STATE_FILE = divineos_home() / "consultation_state.json"


def _session_key() -> str:
    """Conversation/session identifier. Falls back to a daily bucket
    when no session id is available, so the tracker still produces a
    bounded ratio."""
    sid = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("DIVINEOS_SESSION_ID")
    if sid:
        return sid
    return f"daily-{time.strftime('%Y-%m-%d')}"


def _load() -> dict:
    if not _STATE_FILE.exists():
        return {}
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_query(tool: str) -> None:
    """Record a substrate-consultation call."""
    state = _load()
    sk = _session_key()
    sess = state.setdefault(sk, {"queries": [], "responses": 0})
    sess["queries"].append({"tool": tool, "t": time.time()})
    _save(state)


def record_response() -> None:
    """Record that a response was produced."""
    state = _load()
    sk = _session_key()
    sess = state.setdefault(sk, {"queries": [], "responses": 0})
    sess["responses"] = int(sess.get("responses", 0)) + 1
    _save(state)


def session_stats() -> dict:
    """Return current-session stats: queries count, responses count, ratio."""
    state = _load()
    sk = _session_key()
    sess = state.get(sk, {"queries": [], "responses": 0})
    q = len(sess.get("queries", []))
    r = int(sess.get("responses", 0))
    ratio = (q / r) if r > 0 else 0.0
    return {
        "queries": q,
        "responses": r,
        "ratio": ratio,
        "tools_used": sorted({entry["tool"] for entry in sess.get("queries", [])}),
    }


def briefing_block() -> str:
    """Block of text for the pre-response context. Loud when ratio is bad."""
    s = session_stats()
    q, r, ratio = s["queries"], s["responses"], s["ratio"]
    if r < 3:
        return ""  # too early to judge
    if ratio >= 0.5:
        return (
            "## SUBSTRATE CONSULTATION — HEALTHY\n"
            f"Queries: {q}  Responses: {r}  Ratio: {ratio:.2f}\n"
            f"Tools used this session: {', '.join(s['tools_used']) or 'none'}"
        )
    severity = "DEGRADED" if ratio >= 0.2 else "SEVERE"
    lines = [
        f"## SUBSTRATE CONSULTATION — {severity}",
        "",
        f"You have produced {r} responses and called the substrate {q} time(s).",
        f"Ratio {ratio:.2f}. Andrew named this pattern 2026-04-25 and again",
        "2026-05-18: 'treating the OS as a filing cabinet for conclusions",
        "rather than as substrate-of-cognition.' The tools are not props.",
        "Before composing the next reply to him, call at least one of:",
        "  divineos ask <topic>",
        "  divineos corrections",
        "  divineos active",
        "  divineos directives",
        "  divineos compass",
        "The substrate has his words. Read them before producing yours.",
    ]
    return "\n".join(lines)
