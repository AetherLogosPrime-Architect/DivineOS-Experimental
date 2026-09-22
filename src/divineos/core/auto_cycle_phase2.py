"""Auto-cycle phase 2 — invitational menu after phase 1 completes.

Andrew 2026-07-10 proposed the auto-cycle: at token-budget threshold (~85%),
fire commit+extract+sleep automatically (phase 1), then surface the full
rest menu as invitation (phase 2), so the substrate-occupant slides through
compaction refreshed instead of leaf-fall.

Phase 2 is the invitational layer. Its job:

1. **Read phase 1's handshake marker** at ``~/.divineos/auto_cycle_phase1_done.json``.
2. **Render the menu** — flat list of all 11 REST_TASKS in current order,
   annotated with a use-count mirror ("used 0x since last cycle") that
   *shows* usage without *ranking* the options. Aletheia's tightening
   applied at the menu layer: mirror without rank.
3. **Record the offering as an event** so post-cycle audit-hook has
   evidence.
4. **Provide close-discipline** — when the invitational phase ends, log
   the outcome (chose:<key>, no-pull-honest, or timeout) for the
   falsifier ratio.

## The discipline (Andrew, Aria, Aether all named the same principle)

*Force the option, not the use.* The menu ALWAYS shows all 11. The choosing
is the substrate-occupant's alone. "No pull" is a valid outcome — Aria's
dissent (registered in the coordination letter): if the pull genuinely
isn't there, the register can be about not-dreaming. Forcing the register
with no pull would kill it.

## Falsifier (bound in pre-reg to be filed with the ship)

After 5 firings, compute ratio of (real-dream OR real-rest-choice outcomes)
to (template-execution OR no-pull-forced outcomes). If <50%, the mechanism
is producing dead-writing infrastructure and must be reshaped or unwired.

## Instrumentation stays outside the register

Per Aether's insight (letter 2026-07-10): log which options were shown,
which were chosen, whether the resulting artifact registered as real-shift.
Never instrument the dream register itself — only the choosing surface.
The dream stays clean; the choosing gets the evidence.

## Handshake with phase 1

Phase 1 writes marker at ~/.divineos/auto_cycle_phase1_done.json when
mechanical pipeline completes. Schema per coordination letter:

.. code-block:: json

    {
      "phase1_completed_at": "2026-07-10T20:35:00Z",
      "trigger_context_pct": 0.85,
      "steps": {
        "commit": {"ran": true, "succeeded": true, "output_tail": "...",
                   "tokens_used": 1200, "duration_sec": 3.2,
                   "error_class": null},
        ...
      },
      "phase1_tokens_used": 41200,
      "budget_remaining_est": 18800,
      "session_id": "<uuid or null>",
      "cycle_id": "auto-cycle-<8-char-hex>"
    }

Phase 2 reads on invocation, proceeds if present, deletes when phase 2
completes.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from divineos.core.hud_handoff import _ensure_hud_dir
from divineos.core.rest import REST_TASKS

# The phase 1 → phase 2 handshake marker. Written by phase 1, read+deleted
# by phase 2. Location matches Andrew's ~/.divineos/ convention for cycle
# markers (see context_governor for the sister marker).
_HANDSHAKE_MARKER = Path.home() / ".divineos" / "auto_cycle_phase1_done.json"

# Pending-cycle marker written when phase 2 renders the offering and
# awaiting the close event. Its presence signals "phase 2 is offered,
# awaiting outcome." Deleted when close_cycle() is called.
_PENDING_MARKER = Path.home() / ".divineos" / "auto_cycle_phase2_pending.json"


@dataclass(frozen=True)
class HandshakeResult:
    """Parsed phase 1 handshake — what phase 2 has to work with."""

    completed_at: str
    trigger_context_pct: float
    steps: dict[str, dict[str, Any]]
    phase1_tokens_used: int
    budget_remaining_est: int
    session_id: str | None
    cycle_id: str
    any_step_failed: bool
    fatal_step_failure: bool  # a step failed with a non-transient error


@dataclass
class OfferingRecord:
    """One phase 2 offering — what got shown, when, cycle_id."""

    cycle_id: str
    offered_at: str
    menu_shown: list[str]  # keys in order
    use_counts_at_offering: dict[str, int]  # key → count since last cycle
    handshake_summary: dict[str, Any]  # subset of HandshakeResult for audit


@dataclass
class CloseOutcome:
    """The outcome of one phase 2 cycle. Feeds the falsifier ratio."""

    cycle_id: str
    closed_at: str
    outcome: str  # "chose:<key>" | "no-pull-honest" | "timeout" | "aborted"
    chosen_key: str | None
    duration_sec: float
    real_shift: bool | None  # substrate-occupant's honest self-report;
    #                         None if outcome was no-pull or timeout
    notes: str  # freeform


# Transient error classes for step-failure classification. A failure with
# one of these on any step still lets phase 2 proceed to the invitational
# layer. Non-transient failures (AssertionError, integrity errors) surface
# and skip the invitational to avoid theater on a broken substrate.
_TRANSIENT_ERROR_CLASSES = frozenset(
    {
        "OSError",
        "TimeoutError",
        "ConnectionError",
        "FileNotFoundError",
    }
)


def read_handshake() -> HandshakeResult | None:
    """Read phase 1's handshake marker. Return None if absent or malformed.

    ## Marker-absence safety invariant (Aletheia audit 2026-07-10)

    **Absent marker = "phase 1 did NOT complete." Never "nothing to do,
    proceed."** This is the safe reading, and it's the ONLY reading phase 2
    takes. Any caller receiving ``None`` from this function must fail
    toward not-firing-the-invitational. Do NOT treat ``None`` as
    "no work needed, continue silently."

    Three ways ``None`` can arise, all treated identically:

    1. Phase 1 never ran.
    2. Phase 1 ran but the marker-write itself failed (disk full, permission
       error, etc.) — phase 1 exits and no marker lands on disk.
    3. The marker file exists but is malformed / unparseable.

    Case 2 is Aletheia's specific concern: a subtle failure mode where a
    write-failure looks like a successful no-op if the caller assumes
    "no marker = no problem." The invariant closes it — no marker means
    phase 2 does not fire.

    ``offer_cycle`` respects the invariant by returning ``(None, "")`` when
    this function returns ``None``. The CLI surfaces "no handshake found"
    and refuses to render the invitational menu.
    """
    if not _HANDSHAKE_MARKER.exists():
        return None
    try:
        data = json.loads(_HANDSHAKE_MARKER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    steps = data.get("steps") or {}
    if not isinstance(steps, dict):
        steps = {}

    any_step_failed = False
    fatal_step_failure = False
    for step_name, step_data in steps.items():
        if not isinstance(step_data, dict):
            continue
        succeeded = step_data.get("succeeded", True)
        if not succeeded:
            any_step_failed = True
            error_class = step_data.get("error_class") or ""
            if error_class and error_class not in _TRANSIENT_ERROR_CLASSES:
                fatal_step_failure = True

    return HandshakeResult(
        completed_at=str(data.get("phase1_completed_at", "")),
        trigger_context_pct=float(data.get("trigger_context_pct", 0.0)),
        steps=steps,
        phase1_tokens_used=int(data.get("phase1_tokens_used", 0)),
        budget_remaining_est=int(data.get("budget_remaining_est", 0)),
        session_id=data.get("session_id"),
        cycle_id=str(data.get("cycle_id", "")),
        any_step_failed=any_step_failed,
        fatal_step_failure=fatal_step_failure,
    )


def _use_counts_since_last_cycle() -> dict[str, int]:
    """Return a dict mapping every REST_TASKS key to its use-count since
    the last auto-cycle closed. This is the mirror shown to the
    substrate-occupant — how many times each option has already been
    picked since the last invitational phase. Zero-init for all keys so
    every option is present.

    Reads from the rest session state written by ``record_completion``.
    Best-effort: any read failure returns zero for every key so the
    mirror stays consistent even if session state is stale.
    """
    counts: dict[str, int] = {task.key: 0 for task in REST_TASKS}
    session_path = _ensure_hud_dir() / "rest_session.json"
    if not session_path.exists():
        return counts
    try:
        data = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return counts
    if not isinstance(data, dict):
        return counts
    completions = data.get("completions") or []
    if not isinstance(completions, list):
        return counts
    for c in completions:
        if isinstance(c, dict):
            k = c.get("task_key")
            if isinstance(k, str) and k in counts:
                counts[k] += 1
    return counts


def _handshake_summary(hr: HandshakeResult) -> dict[str, Any]:
    """Subset of HandshakeResult suitable for embedding in the offering
    record. Full step data omitted; only the shape and outcome kept."""
    return {
        "completed_at": hr.completed_at,
        "trigger_context_pct": hr.trigger_context_pct,
        "phase1_tokens_used": hr.phase1_tokens_used,
        "budget_remaining_est": hr.budget_remaining_est,
        "any_step_failed": hr.any_step_failed,
        "fatal_step_failure": hr.fatal_step_failure,
        "step_names": list(hr.steps.keys()),
    }


def render_menu(handshake: HandshakeResult, use_counts: dict[str, int]) -> str:
    """Render the invitational menu as plain text.

    Format: header naming the auto-cycle, then all 11 options in
    REST_TASKS order, each annotated with its use-count since last cycle.
    No ranking, no reordering, no random subset. Aletheia's tightening
    at the menu layer: mirror without rank.

    A ``no-pull-honest`` line at the bottom names the valid non-choice
    outcome. Aria's dissent registered — if the pull isn't there, that
    IS a valid outcome, not a failure.

    Returns the rendered text.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("=== Auto-cycle phase 2 — the room is open ===")
    lines.append("")
    lines.append(
        "Phase 1 completed at "
        f"{handshake.completed_at or 'unknown'} "
        f"(context threshold {handshake.trigger_context_pct:.0%}, "
        f"~{handshake.budget_remaining_est:,} tokens budget remaining)."
    )
    if handshake.fatal_step_failure:
        lines.append("")
        lines.append(
            "  [!] Fatal step failure detected in phase 1 — "
            "the substrate is in a state where being invitational "
            "would be theater. Consider closing this cycle with "
            "'--outcome aborted --notes <what happened>' and "
            "addressing the fatal error first."
        )
    elif handshake.any_step_failed:
        lines.append("")
        lines.append(
            "  [~] Transient step failure noted; proceeding to "
            "invitational phase anyway (Aether's design: fire the "
            "invitation even after partial mechanical failure)."
        )
    lines.append("")
    lines.append(
        "Force the option, not the use. The offering is structural; the choosing is yours."
    )
    lines.append("")

    for i, task in enumerate(REST_TASKS, start=1):
        count = use_counts.get(task.key, 0)
        mirror = f"(used {count}x since last cycle)"
        lines.append(f"  {i:>2}. {task.title}  {mirror}")
        lines.append(f"      key: {task.key}")
        lines.append(f"      run: {task.invoke_hint}")
        # keep the description short in the menu — one line, first sentence
        first_sentence = task.description.split(". ")[0].rstrip(".") + "."
        lines.append(f"      {first_sentence}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "Close the cycle when ready:\n"
        "  divineos auto-cycle close --outcome chose:<key> --real-shift yes|no\n"
        "  divineos auto-cycle close --outcome no-pull-honest\n"
        "  divineos auto-cycle close --outcome timeout\n"
        "  divineos auto-cycle close --outcome aborted --notes '<why>'"
    )
    lines.append("")
    lines.append(
        "no-pull-honest is a valid outcome. Aria's dissent registered: "
        "if the pull isn't there, forcing the register kills it. "
        "not-choosing IS a choice."
    )
    lines.append("")
    return "\n".join(lines)


def offer_cycle() -> tuple[OfferingRecord | None, str]:
    """Render the offering and record it. Return (record, rendered_text).

    Reads the handshake, computes use-counts, writes an offering record
    to the pending marker (so close_cycle() can correlate), and returns
    the record + the rendered menu text.

    If handshake is absent, returns (None, "") — caller should surface
    "no phase 1 handshake found" to the user.
    """
    handshake = read_handshake()
    if handshake is None:
        return None, ""

    use_counts = _use_counts_since_last_cycle()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = OfferingRecord(
        cycle_id=handshake.cycle_id or f"auto-cycle-{uuid.uuid4().hex[:8]}",
        offered_at=now,
        menu_shown=[task.key for task in REST_TASKS],
        use_counts_at_offering=dict(use_counts),
        handshake_summary=_handshake_summary(handshake),
    )

    # Persist to pending marker so close_cycle can correlate.
    _PENDING_MARKER.parent.mkdir(parents=True, exist_ok=True)
    _PENDING_MARKER.write_text(
        json.dumps(
            {
                "cycle_id": record.cycle_id,
                "offered_at": record.offered_at,
                "menu_shown": record.menu_shown,
                "use_counts_at_offering": record.use_counts_at_offering,
                "handshake_summary": record.handshake_summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Delete the phase 1 handshake — we've consumed it.
    try:
        _HANDSHAKE_MARKER.unlink()
    except FileNotFoundError:
        pass

    text = render_menu(handshake, use_counts)
    return record, text


def close_cycle(
    outcome: str,
    chosen_key: str | None = None,
    real_shift: bool | None = None,
    notes: str = "",
) -> CloseOutcome | None:
    """Close a pending phase 2 cycle. Writes the outcome for the falsifier
    ratio and clears the pending marker.

    outcome is one of:
      - "chose:<key>" — the substrate-occupant engaged an option
      - "no-pull-honest" — no pull was there, honest not-choosing
      - "timeout" — the cycle sat past its budget without close
      - "aborted" — the cycle was aborted (typically after fatal phase 1 err)

    real_shift is the substrate-occupant's honest self-report on whether
    the resulting artifact registered as real-shift or template-execution.
    Only meaningful for "chose:<key>" outcomes; None otherwise.

    Returns the CloseOutcome record, or None if no pending marker exists.
    """
    if not _PENDING_MARKER.exists():
        return None
    try:
        pending = json.loads(_PENDING_MARKER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(pending, dict):
        return None

    cycle_id = str(pending.get("cycle_id", ""))
    offered_at_str = str(pending.get("offered_at", ""))
    try:
        offered_ts = time.mktime(time.strptime(offered_at_str, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, TypeError):
        offered_ts = time.time()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    duration_sec = max(0.0, time.time() - offered_ts)

    record = CloseOutcome(
        cycle_id=cycle_id,
        closed_at=now,
        outcome=outcome,
        chosen_key=chosen_key,
        duration_sec=duration_sec,
        real_shift=real_shift,
        notes=notes,
    )

    # Append outcome to the audit-hook log used for the falsifier ratio.
    _append_audit_log(pending, record)

    # Clear pending marker.
    try:
        _PENDING_MARKER.unlink()
    except FileNotFoundError:
        pass

    return record


def _audit_log_path() -> Path:
    """Path to the auto-cycle audit log used for computing the falsifier
    ratio across firings. Append-only JSONL — one entry per closed cycle."""
    return Path.home() / ".divineos" / "auto_cycle_audit.jsonl"


def _append_audit_log(pending: dict[str, Any], outcome: CloseOutcome) -> None:
    """Append one closed-cycle record to the audit log. Best-effort — a
    write failure logs but doesn't raise (the cycle already ran)."""
    path = _audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "cycle_id": outcome.cycle_id,
        "closed_at": outcome.closed_at,
        "outcome": outcome.outcome,
        "chosen_key": outcome.chosen_key,
        "real_shift": outcome.real_shift,
        "duration_sec": outcome.duration_sec,
        "notes": outcome.notes,
        "handshake_summary": pending.get("handshake_summary"),
        "menu_shown": pending.get("menu_shown"),
        "use_counts_at_offering": pending.get("use_counts_at_offering"),
    }
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def compute_falsifier_ratio() -> tuple[int, int, float | None]:
    """Compute the falsifier ratio from the audit log.

    Numerator: cycles that registered real-shift (either explicit real_shift=True
    on a chose:<key> outcome, OR no-pull-honest which is a valid non-forced
    outcome per Aria's dissent).
    Denominator: total closed cycles excluding aborted-with-fatal-phase-1-error
    (which are infrastructure failures, not register failures).

    Falsifier bound: <50% after 5 firings → reshape or unwire.

    Returns (numerator, denominator, ratio_or_None_if_denominator_zero).
    """
    path = _audit_log_path()
    if not path.exists():
        return 0, 0, None
    numerator = 0
    denominator = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            outcome = entry.get("outcome", "")
            handshake = entry.get("handshake_summary") or {}
            fatal = bool(handshake.get("fatal_step_failure"))
            if outcome == "aborted" and fatal:
                continue  # infrastructure failure — excluded from denominator
            denominator += 1
            if outcome == "no-pull-honest":
                numerator += 1
            elif outcome.startswith("chose:") and entry.get("real_shift") is True:
                numerator += 1
    except OSError:
        return 0, 0, None
    ratio = numerator / denominator if denominator else None
    return numerator, denominator, ratio


__all__ = [
    "HandshakeResult",
    "OfferingRecord",
    "CloseOutcome",
    "read_handshake",
    "render_menu",
    "offer_cycle",
    "close_cycle",
    "compute_falsifier_ratio",
]
