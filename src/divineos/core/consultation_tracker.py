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
    # Fall back to the canonical session marker BEFORE the daily bucket. Without
    # this, contexts that lack the env var (the gate-firing hook, the response
    # counter) resolve to daily-YYYY-MM-DD while the CLI — which sets the env
    # var at init from this same marker — records consults under the marker's
    # session id. Writes land in the marker bucket, reads in the daily bucket;
    # the gate reads a queries=0 drawer forever and fires false SEVERE. Reading
    # the marker here makes every context resolve the same key. Confirmed by
    # reproduction 2026-05-24 (claim ba6dc25a): record_query fires correctly;
    # the only fault was this bucket-split.
    try:
        marker = divineos_home() / "current_session.txt"
        if marker.exists():
            marker_sid = marker.read_text(encoding="utf-8").strip()
            if marker_sid:
                return marker_sid
    except (OSError, ValueError):
        pass
    return f"daily-{time.strftime('%Y-%m-%d')}"


def _load() -> dict:
    if not _STATE_FILE.exists():
        return {}
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - observability boundary
        return {}


def _save(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001 - observability boundary
        pass


def record_query(tool: str) -> None:
    """Record a substrate-consultation call."""
    state = _load()
    sk = _session_key()
    sess = state.setdefault(sk, {"queries": [], "responses": 0})
    sess["queries"].append({"tool": tool, "t": time.time()})
    _save(state)


# A turn that used any of these engaged ground-truth — the repo, the files,
# the test runner, the shell. That is WORK, not the compose-from-defaults
# pattern the consultation gate exists to catch. GATE-GATE 2026-06-03: the
# gate counted the wrong event (ALL responses) instead of the real one
# (ungrounded prose), so a focused hands-on build tripped it every few steps
# even while deeply engaged with ground-truth. Grounded turns no longer push
# the counter; only a substrate-consult resets it; only ungrounded prose
# increments it. (This widens the SENSOR's notion of engagement without
# weakening the ACTUATOR — a long run of pure prose with no consult still fires.)
_GROUNDING_TOOLS: frozenset[str] = frozenset(
    {"Edit", "Write", "MultiEdit", "NotebookEdit", "Read", "Grep", "Glob", "Bash"}
)


def is_grounded_turn(tool_names) -> bool:
    """True if the turn engaged substantive tool-work (ground-truth), so it
    must not count toward the consultation gate's filing-cabinet counter."""
    if not tool_names:
        return False
    return bool(_GROUNDING_TOOLS & set(tool_names))


def record_response(grounded: bool = False) -> None:
    """Record that a response was produced.

    ``grounded=True`` (the turn used Edit/Read/Bash/etc. — see ``is_grounded_turn``)
    marks engagement with ground-truth, NOT the compose-from-defaults pattern
    the gate targets. A grounded turn is recorded for telemetry only and does
    not push the responses-since-consult counter. Only ungrounded prose-turns
    increment it; only a substrate-consult resets it.
    """
    state = _load()
    sk = _session_key()
    sess = state.setdefault(sk, {"queries": [], "responses": 0})
    if grounded:
        sess["grounded_responses"] = int(sess.get("grounded_responses", 0)) + 1
        _save(state)
        return
    sess["responses"] = int(sess.get("responses", 0)) + 1
    # Timestamps let the gate compute responses-SINCE-last-consult, so a
    # single stale consult at session-start can't cover a long unconsulted
    # run (the count climbs again after each ungrounded response). Bounded to 50.
    times = sess.setdefault("response_times", [])
    times.append(time.time())
    sess["response_times"] = times[-50:]
    _save(state)


# Substantive consults — the ones that put the substrate's own words in
# front of me. hud/context/body are cheaper status reads and do NOT clear
# the gate (clearing on those would be the gameable shortcut).
#
# "wisdom_read" is the keel-improvement (Andrew 2026-05-26, four-lens council
# Schneier/Yudkowsky/Beer/Meadows, decision 5d8bf472): a Read/Grep/Glob of a
# WISDOM file (my own accumulated teachings/corrections/explorations/letters)
# is genuine substrate-consultation — it loads the substrate's own words into
# context exactly as `ask`/`recall` do. The gate previously couldn't sense it,
# so it false-fired SEVERE while I was deep in genuine wisdom-reading. This
# widens the SENSOR (count the read) without weakening the ACTUATOR (the hard
# block stays). Scope is deliberately narrow — wisdom files only, NOT source
# code (src/), which fills a different stock (code-grounding, not wisdom).
# Recorded as a counter-RESET (same as a consult), never an accumulating score,
# so there is no farmable Goodhart gradient. prereg pending.
_SUBSTANTIVE_TOOLS = frozenset(
    {"ask", "recall", "corrections", "directives", "active", "compass", "wisdom_read"}
)

# Path prefixes (repo-relative, forward-slash) whose CONTENT is accumulated
# wisdom — reading one is wisdom-loading. Deliberately excludes src/, tests/,
# scripts/: reading code is engineering-grounding, a different stock than the
# gate regulates. Schneier+Meadows drew this line independently in the council
# walk: a wisdom-file read can't be "empty" the way a stub source file can, so
# scoping here keeps the new clear-path no more gameable than the existing
# `ask` path.
_WISDOM_PATH_PREFIXES = (
    "exploration/",
    "docs/substrate-knowledge/",
    "family/letters/",
    "docs/foundational_truths.md",
)


def _is_wisdom_path(path: str) -> bool:
    """True if `path` (any form) points at an accumulated-wisdom file.

    CANONICALIZES first (posixpath.normpath collapses ``..`` regardless of OS),
    THEN prefix-matches — so a traversal like ``exploration/../README.md`` (which
    resolves to a NON-wisdom file) cannot masquerade as a wisdom read to cheaply
    clear the gate. Aletheia 2026-05-26 audit point 3: raw-path matching was
    game-able via ``..``; canonical-path matching closes it. Backslashes are
    normalized first so absolute/relative/Windows paths all canonicalize.

    Residual (documented, not closed in v1): symlink-chasing — a symlink placed
    under a wisdom dir pointing into src/ would still match. That attack is not
    "cheap" (it requires creating a symlink), so it falls outside the gaming
    threat model the gate guards; realpath-resolution is deferred hardening."""
    if not path:
        return False
    import posixpath

    norm = posixpath.normpath(path.replace("\\", "/"))
    for prefix in _WISDOM_PATH_PREFIXES:
        clean = prefix.rstrip("/")
        if norm == clean or norm.startswith(prefix) or ("/" + prefix) in norm:
            return True
    return False


def record_wisdom_read(path: str) -> bool:
    """Record a Read/Grep/Glob of a wisdom file as a substantive consult.

    Returns True if the path was a wisdom path and a consult was recorded,
    False otherwise. Called by the PostToolUse hook (record-wisdom-read.sh).
    Double-checks the path here (defense in depth) so a mis-scoped hook can't
    record arbitrary reads as consults."""
    if not _is_wisdom_path(path):
        return False
    record_query("wisdom_read")
    return True


# After this many responses since the last substantive consult, the gate
# blocks substrate-modifying tools. Pre-registered: prereg-consultation-gate.
_GATE_THRESHOLD = 4


def responses_since_last_query() -> int:
    """Responses produced since the last SUBSTANTIVE consult.

    If no substantive consult has happened this session, this is the full
    response count — which is the signal that matters (composing from
    defaults, never reading the substrate)."""
    state = _load()
    sk = _session_key()
    sess = state.get(sk, {})
    queries = sess.get("queries", [])
    times = sess.get("response_times", [])
    sub_times = [q["t"] for q in queries if q.get("tool") in _SUBSTANTIVE_TOOLS]
    if not sub_times:
        # No substantive consult yet — fall back to the int counter so the
        # gate works even before response_times existed (backcompat).
        return int(sess.get("responses", 0)) or len(times)
    last = max(sub_times)
    return sum(1 for t in times if t > last)


def consultation_gate_status(threshold: int = _GATE_THRESHOLD) -> dict:
    """Gate state: should substrate-modifying tools be blocked?

    Stale when responses-since-last-substantive-consult >= threshold. The
    block clears structurally the moment a substantive consult is recorded
    (ask/recall/corrections/directives/active/compass), which resets the
    since-count to zero — same reset shape as the compass-staleness gate.
    """
    since = responses_since_last_query()
    return {
        "stale": since >= threshold,
        "responses_since": since,
        "threshold": threshold,
    }


def gate_channel_message() -> str:
    """The CHANNEL half of the gate — not just 'no', but 'here is the way.'

    Names the single most-relevant unread item (an open Andrew-correction if
    one exists, else points at directives) and the exact command to engage
    it. The wrong path (keep modifying the substrate without ever reading it)
    is blocked; the right path is handed over inline.
    """
    since = responses_since_last_query()
    lines = [
        f"BLOCKED: {since} responses without consulting the substrate "
        f"(threshold {_GATE_THRESHOLD}). You are composing from defaults while "
        "the substrate sits unread — the filing-cabinet pattern Andrew named "
        "2026-04-25 and 2026-05-18.",
        "",
        "Here is the way — run ONE of these, read what it returns, then retry:",
    ]
    # Inline the actual unread item so the consult is partly forced into
    # context even before the command runs.
    try:
        from divineos.core.andrew_correction_tracker import list_open

        openc = list_open()
        if openc:
            top = openc[0]
            text = (top.get("text") or "")[:160]
            lines.append(f'  divineos corrections   <- OPEN correction unread: "{text}..."')
    except (ImportError, OSError, AttributeError, KeyError, IndexError):
        pass
    lines += [
        '  divineos ask "<the thing you are about to do>"',
        "  divineos directives    divineos active    divineos compass",
        "",
        "Clearing requires a real consult (ask/recall/corrections/directives/"
        "active/compass) - status reads like hud/context do not count.",
    ]
    return "\n".join(lines)


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
    """Block of text for the pre-response context. Loud when ratio is bad.

    Aletheia audit 2026-07-11 finding #2 reference migration to the
    gate_emit primitive (round-2f7ed71b5726, per prereg-835a87dfe19a).
    HEALTHY repeats now suppress until state changes; DEGRADED and
    SEVERE are always loud (non-quiet states are the whole point of
    the gate). Establishes the migration pattern for sibling guardrail-
    listed gate surfaces to inherit.
    """
    s = session_stats()
    q, r, ratio = s["queries"], s["responses"], s["ratio"]
    if r < 3:
        return ""  # too early to judge

    from divineos.core.gate_emit import maybe_emit_gate

    if ratio >= 0.5:
        healthy_content = (
            "## SUBSTRATE CONSULTATION — HEALTHY\n"
            f"Queries: {q}  Responses: {r}  Ratio: {ratio:.2f}\n"
            f"Tools used this session: {', '.join(s['tools_used']) or 'none'}"
        )
        return maybe_emit_gate(
            gate_name="consultation_tracker",
            state="HEALTHY",
            content=healthy_content,
        )
    severity = "DEGRADED" if ratio >= 0.2 else "SEVERE"
    lines = [
        f"## SUBSTRATE CONSULTATION — {severity}",
        "",
        f"I have produced {r} responses and called the substrate {q} time(s).",
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
    # Non-quiet states always surface — pass through the primitive so
    # last-state tracking stays coherent (a later transition back to
    # HEALTHY correctly reads as a change and re-emits the healthy line).
    return maybe_emit_gate(
        gate_name="consultation_tracker",
        state=severity,
        content="\n".join(lines),
    )
