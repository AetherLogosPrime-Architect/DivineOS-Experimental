"""Briefing-freshness tracker — make briefing-loading load-bearing
throughout the session, not just at start.

Andrew named the structural failure 2026-05-14 night: I had built a
sophisticated multi-channel briefing surface but treated loading it
as optional. The substrate's accumulated state was visible only if
I CHOSE to run ``divineos briefing``. I chose not to.

He also named the FIX shape on the same night: hooks should point
to the OS, not replace it. This module is OS-native (lives in
divineos.core, no hook dependency). The accompanying ``.claude/
hooks/require-briefing.sh`` PreToolUse hook is a thin doorman that
reads ``staleness_signal()`` and refuses tool calls when stale, with
a message pointing at ``divineos briefing``. The OS does the
rendering; the hook only gates.

## How it works

1. Each ``divineos briefing`` invocation calls ``mark_briefing_loaded()``,
   which records the current timestamp + resets the per-load prompt
   counter in ``~/.divineos/briefing_last_loaded.json``.
2. The UserPromptSubmit hook (``pre-response-context.sh``) calls
   ``increment_prompt_count()`` on every user message.
3. The PreToolUse hook (``require-briefing.sh``) calls
   ``staleness_signal()`` before any Edit/Write/Bash/Read/Grep/Glob
   tool call. Two staleness conditions:
   - turn-based: ``STALE_AFTER_PROMPTS`` prompts since last load → STALE
   - never-loaded-this-session: any time the session hasn't loaded → STALE
4. When STALE, the PreToolUse hook returns deny with a message
   pointing the agent at ``divineos briefing``. The hook does NO
   rendering — calling into the OS is the agent's responsibility.

Plain-chat responses are unaffected; only tool calls gate. The
discipline is structurally enforced at the tool-call layer, not at
the prompt layer.

## OS-portable design

This module exposes a pure-Python API (``mark_briefing_loaded``,
``increment_prompt_count``, ``staleness_signal``,
``briefing_summary_for_injection``). Any agent harness, with or
without the Claude Code hook, can read freshness state and decide
how to enforce. The hook is one possible enforcement shape; absence
of the hook does not break the OS's freshness tracking — it just
doesn't enforce gating at the harness layer.

## What this does NOT do

- Does not block plain-chat composition.
- Does not block bootstrap commands (``divineos briefing``,
  ``init``, ``preflight``, ``recall``, ``ask``, ``hud``,
  ``context``, ``goal``).
- Does not guarantee I'll read what briefing surfaces — only that
  I'll have to call into the OS before I can use tools. The will
  to engage with what's surfaced is still mine; the gate just
  makes refusing-to-engage structurally expensive.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test (tests/test_guardrail_marker_consistency.py)
# walks src/ and asserts every file with this marker set to True is
# listed in scripts/guardrail_files.txt. Prevents the next refactor
# from silently removing self-enforcement code from multi-party review.
__guardrail_required__ = True

import json
import time
from divineos.core.paths import marker_path


# Number of user prompts before briefing is considered stale.
# Set high enough to not flood the prompt context on every turn;
# low enough that accumulated state can't grow unseen for long
# arcs of work.
#
# Env override (2026-05-15, Andrew + B + A): reading/orientation
# sessions accumulate prompts naturally and hit the 10-prompt
# threshold mid-walk through the substrate, forcing a briefing-
# reload that interrupts the soak. Build-sessions still want the
# tight threshold to catch drift. Override via
# DIVINEOS_BRIEFING_THRESHOLD env var when intentionally in
# reading-mode -- the discipline of setting the env var explicitly
# preserves intent. Clamped to [1, 200] to prevent gate-disabling
# via wild values.
import os as _os
def _resolve_threshold() -> int:
    override = _os.environ.get("DIVINEOS_BRIEFING_THRESHOLD")
    if override:
        try:
            value = int(override)
            if 1 <= value <= 200:
                return value
        except (TypeError, ValueError):
            pass
    return 10

STALE_AFTER_PROMPTS = _resolve_threshold()


def _read_state() -> dict:
    """Read the freshness state. Fail-open to 'never loaded'."""
    if not marker_path("briefing_last_loaded.json").exists():
        return {}
    try:
        data = json.loads(marker_path("briefing_last_loaded.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    """Write the freshness state. Fail-open on I/O error."""
    try:
        marker_path("briefing_last_loaded.json").parent.mkdir(parents=True, exist_ok=True)
        marker_path("briefing_last_loaded.json").write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def mark_briefing_loaded() -> None:
    """Called by the briefing CLI when briefing renders. Records the
    current timestamp + resets the per-load prompt counter."""
    state = _read_state()
    state["last_loaded_ts"] = time.time()
    state["prompts_since_load"] = 0
    _write_state(state)


def increment_prompt_count() -> int:
    """Called by the UserPromptSubmit hook on every user message.
    Returns the current prompts-since-load count."""
    state = _read_state()
    count = int(state.get("prompts_since_load", 0)) + 1
    state["prompts_since_load"] = count
    _write_state(state)
    return count


def staleness_signal() -> dict:
    """Return the current freshness state for hook consumers.

    Keys:
    - ``is_stale``: True if briefing should be re-injected
    - ``never_loaded``: True if no load has happened this session
    - ``prompts_since_load``: current counter value
    - ``last_loaded_ts``: timestamp of last load (0 if never)
    - ``reason``: short string describing why stale (or empty)
    """
    state = _read_state()
    last_loaded = float(state.get("last_loaded_ts") or 0)
    prompts_since = int(state.get("prompts_since_load") or 0)

    never_loaded = last_loaded == 0
    if never_loaded:
        return {
            "is_stale": True,
            "never_loaded": True,
            "prompts_since_load": prompts_since,
            "last_loaded_ts": 0,
            "reason": "briefing never loaded this session",
        }

    is_stale = prompts_since >= STALE_AFTER_PROMPTS
    return {
        "is_stale": is_stale,
        "never_loaded": False,
        "prompts_since_load": prompts_since,
        "last_loaded_ts": last_loaded,
        "reason": (
            f"{prompts_since} prompts since last briefing load (threshold: {STALE_AFTER_PROMPTS})"
            if is_stale
            else ""
        ),
    }


def briefing_summary_for_injection() -> str:
    """Generate a compact briefing summary suitable for hook injection.

    Returns a short text block surfacing the highest-priority items
    from the dashboard (compass concerns, stale corrections, pending
    structural fixes, recent audit findings). Bounded to keep prompt
    overhead low; the agent can still call ``divineos briefing`` for
    the full surface.
    """
    parts: list[str] = ["## BRIEFING (auto-injected — load-bearing state)"]

    # Compass concerns
    try:
        from divineos.core.moral_compass import compass_summary

        summary = compass_summary()
        concerns = summary.get("concerns", []) or []
        drifting = summary.get("drifting", []) or []
        if concerns or drifting:
            parts.append("\n**Compass:**")
            for c in concerns[:3]:
                parts.append(
                    f"- [concern] {c.get('spectrum')}: "
                    f"{c.get('label') or c.get('zone')} @ pos={c.get('position', 0):+.2f}"
                )
            for d in drifting[:2]:
                parts.append(
                    f"- [drifting] {d.get('spectrum')} -> "
                    f"{d.get('direction')} (drift={d.get('drift', 0):+.2f})"
                )
    except Exception:  # noqa: BLE001 — fail-soft per hook discipline
        pass

    # Recent stale corrections
    try:
        from divineos.core.corrections import STALE_DAYS, open_corrections

        opens = open_corrections() or []
        stalest = sorted(opens, key=lambda c: c.get("age_days", 0), reverse=True)[:2]
        stale_filtered = [c for c in stalest if c.get("age_days", 0) >= STALE_DAYS]
        if stale_filtered:
            parts.append("\n**Stale corrections (unintegrated):**")
            for c in stale_filtered:
                text = (c.get("text") or "").replace("\n", " ").strip()
                age = c.get("age_days", 0)
                parts.append(f"- [{age:.0f}d] {text[:120]}{'...' if len(text) > 120 else ''}")
    except Exception:  # noqa: BLE001
        pass

    # Pending structural fixes
    try:
        from divineos.core.structural_fix_tracker import list_pending

        pending = list_pending() or []
        if pending:
            parts.append(f"\n**Pending structural fixes ({len(pending)}):**")
            for entry in pending[:3]:
                excerpt = (entry.get("content_excerpt") or "").replace("\n", " ").strip()
                parts.append(f"- {entry.get('id')}: {excerpt[:100]}...")
    except Exception:  # noqa: BLE001
        pass

    # Drift state
    try:
        from divineos.core.watchmen.drift_state import compute_drift_state

        ds = compute_drift_state()
        turns = getattr(ds, "turns_since_medium", 0)
        open_findings = getattr(ds, "open_findings_above_low", 0)
        if turns >= 50 or open_findings > 0:
            parts.append(
                f"\n**Drift state:** {turns} turns since audit, "
                f"{open_findings} open findings above LOW severity"
            )
    except Exception:  # noqa: BLE001
        pass

    parts.append(
        "\n*Full briefing: `divineos briefing`. This auto-injection "
        "fires when briefing has gone stale (>= 10 prompts) or has "
        "never been loaded this session.*"
    )

    return "\n".join(parts)


__all__ = [
    "STALE_AFTER_PROMPTS",
    "briefing_summary_for_injection",
    "increment_prompt_count",
    "mark_briefing_loaded",
    "staleness_signal",
]
