"""Auto-cycle phase 2 — invitational menu after phase 1 completes.

Andrew 2026-07-10 proposed the auto-cycle: at token-budget threshold, fire
commit+extract+sleep automatically (phase 1), then surface the full rest menu
as invitation (phase 2), so the substrate-occupant slides through compaction
refreshed instead of leaf-fall.

Phase 2 is the invitational layer. Its job:

1. **Read phase 1's handshake marker** through phase 1's own reader
   (``auto_cycle.read_handshake_marker`` at ``auto_cycle.marker_path()``), so
   there is one path and the two phases cannot agree only by accident.
2. **Render the menu** — every option in ``REST_TASKS``, in order, annotated
   with a use-count mirror that *shows* usage without *ranking* the options.
3. **Record the offering** so the close can correlate.
4. **Close** — log the outcome (chose:<key>, no-pull-honest, timeout, aborted)
   for the falsifier.

## The discipline

*Force the option, not the use.* The menu always shows every option. The
choosing is the substrate-occupant's alone, and "no pull" is a valid outcome.

## Rebuilt 2026-09-25 after Aether's station four on #551

The July reader believed a completion by default. It read ``succeeded`` and
never ``ran``, so main's dry run (``ran=False, succeeded=True`` on every step)
came up as "Phase 1 completed". A missing ``succeeded`` defaulted to True, an
empty ``steps`` passed, and a failed step with no ``error_class`` counted as
benign. The burden of proof now sits on the claim: a completion is believed only
when every step says, in booleans, that it ran and succeeded or failed. Anything
else is refused, and the refusal says which of three things it is:

- ``absent``      -- no marker. Phase 1 never ran, or its write failed.
- ``malformed``   -- a marker that does not state the required fields.
- ``did-not-run`` -- a well-formed marker with a step that did not run. Main's
                     only producer of ``ran=False`` is the dry run.

All three fail toward no menu (Aletheia's absence invariant, 2026-07-10). They
differ in what they tell the reader at the edge of a compaction.

The handshake is consumed at CLOSE, not at offer (phase 1's contract: the reader
deletes it "once phase 2 completes"), and only while it still carries the cycle
being closed, so a newer phase 1 that fired while an offer was pending is never
eaten (Dijkstra on walk-e281a97c4097).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from divineos.core.auto_cycle import clear_handshake_marker, marker_path, read_handshake_marker
from divineos.core.hud_handoff import _ensure_hud_dir
from divineos.core.paths import divineos_home
from divineos.core.rest import REST_TASKS


def _pending_path() -> Path:
    """Pending-offer marker: present while an offer awaits its close."""
    return divineos_home() / "auto_cycle_phase2_pending.json"


def _audit_log_path() -> Path:
    """Append-only JSONL, one entry per closed cycle, read by the falsifier."""
    return divineos_home() / "auto_cycle_audit.jsonl"


@dataclass(frozen=True)
class HandshakeResult:
    """A phase 1 completion that stated itself in full."""

    completed_at: str
    trigger_context_pct: float
    steps: dict[str, dict[str, Any]]
    phase1_tokens_used: int
    budget_remaining_est: int
    session_id: str | None
    cycle_id: str
    any_step_failed: bool
    fatal_step_failure: bool  # a step failed with a non-transient or unnamed error


@dataclass(frozen=True)
class NoHandshake:
    """Why there is no completion to offer on. Never read as 'nothing to do'."""

    kind: str  # "absent" | "malformed" | "did-not-run"
    reason: str


@dataclass
class OfferingRecord:
    """One phase 2 offering — what got shown, when, cycle_id."""

    cycle_id: str
    offered_at: str
    menu_shown: list[str]  # keys in order
    use_counts_at_offering: dict[str, int]  # key -> count since last cycle
    handshake_summary: dict[str, Any]  # subset of HandshakeResult for audit


@dataclass
class CloseOutcome:
    """The outcome of one phase 2 cycle. Feeds the falsifier ratio."""

    cycle_id: str
    closed_at: str
    outcome: str  # "chose:<key>" | "no-pull-honest" | "timeout" | "aborted"
    chosen_key: str | None
    duration_sec: float
    real_shift: bool | None  # honest self-report; None if not engaged
    notes: str


# A failed step with one of these still lets the invitation proceed. A failure
# with any other class -- INCLUDING an empty one -- is fatal: an unnamed failure
# is not known to be a transient one.
_TRANSIENT_ERROR_CLASSES = frozenset(
    {
        "OSError",
        "TimeoutError",
        "ConnectionError",
        "FileNotFoundError",
    }
)

_PLAIN_OUTCOMES = frozenset({"no-pull-honest", "timeout", "aborted"})


def inspect_handshake() -> HandshakeResult | NoHandshake:
    """Read phase 1's marker and say what it proves.

    Required, per step: a dict with boolean ``ran`` and boolean ``succeeded``.
    Required overall: a non-empty ``steps`` dict and a non-empty ``cycle_id``.
    No default is filled in for a required field -- a default is a bit the
    sender never sent (Shannon on the walk), and a truncated marker is a prefix
    of a valid one.
    """
    if not marker_path().exists():
        return NoHandshake("absent", "no phase 1 marker: phase 1 never ran, or its write failed")
    data = read_handshake_marker()
    if data is None:
        return NoHandshake("malformed", "the phase 1 marker is not a readable JSON object")

    steps = data.get("steps")
    if not isinstance(steps, dict) or not steps:
        return NoHandshake("malformed", "the marker has no steps")
    cycle_id = data.get("cycle_id")
    if not isinstance(cycle_id, str) or not cycle_id.strip():
        return NoHandshake("malformed", "the marker has no cycle_id")

    any_step_failed = False
    fatal = False
    for name, step in steps.items():
        if not isinstance(step, dict):
            return NoHandshake("malformed", f"step {name!r} is not an object")
        ran, ok = step.get("ran"), step.get("succeeded")
        if not isinstance(ran, bool) or not isinstance(ok, bool):
            return NoHandshake("malformed", f"step {name!r} does not state ran and succeeded")
        if not ran:
            return NoHandshake(
                "did-not-run",
                f"step {name!r} did not run -- phase 1 only practised (a dry run), "
                "so nothing was committed, extracted or slept",
            )
        if not ok:
            any_step_failed = True
            if str(step.get("error_class") or "") not in _TRANSIENT_ERROR_CLASSES:
                fatal = True

    def _num(key: str, cast: type) -> Any:
        try:
            return cast(data.get(key) or 0)
        except (TypeError, ValueError):
            return cast(0)

    return HandshakeResult(
        completed_at=str(data.get("phase1_completed_at") or ""),
        trigger_context_pct=_num("trigger_context_pct", float),
        steps=steps,
        phase1_tokens_used=_num("phase1_tokens_used", int),
        budget_remaining_est=_num("budget_remaining_est", int),
        session_id=data.get("session_id"),
        cycle_id=cycle_id,
        any_step_failed=any_step_failed,
        fatal_step_failure=fatal,
    )


def read_handshake() -> HandshakeResult | None:
    """The completion if there is one, else None. ``inspect_handshake`` says why."""
    found = inspect_handshake()
    return found if isinstance(found, HandshakeResult) else None


def refusal_text(why: NoHandshake) -> str:
    """What the reader at the edge of a compaction is told when there is no menu."""
    lead = {
        "absent": "[~] No phase 1 handshake. Nothing to offer.",
        "malformed": "[!] The phase 1 handshake is damaged and cannot be trusted.",
        "did-not-run": "[~] Phase 1 only practised. Nothing was saved.",
    }.get(why.kind, "[!] No usable phase 1 handshake.")
    return f"{lead}\n    {why.reason}\n    Run phase 1 for real: divineos auto-cycle fire"


def _use_counts_since_last_cycle() -> dict[str, int]:
    """Every REST_TASKS key mapped to its use-count since the last cycle.

    Best-effort mirror: any read failure yields zero for every key so the menu
    stays whole.
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
    """Render every option in REST_TASKS order, each with its use-count mirror.

    No ranking, no reordering, no subset: Aletheia's tightening at the menu
    layer, mirror without rank. The no-pull-honest line names the valid
    non-choice (Aria's dissent).
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


class DamagedPending(RuntimeError):
    """The pending-offer file exists but cannot be read.

    Kept apart from "nothing pending" (None): the precommit's failure-shares-
    empty check asked whether a caller could tell the two apart, and it could
    not -- close would have answered "no pending cycle" over a record that was
    there and broken, and offer would have stacked a new cycle on top of it.
    """


def _read_pending() -> dict[str, Any] | None:
    """The pending offer, None if there is none, DamagedPending if it is broken."""
    path = _pending_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise DamagedPending(f"the pending offer at {path} cannot be read ({e})") from e
    if not isinstance(data, dict):
        raise DamagedPending(f"the pending offer at {path} is not a JSON object")
    return data


def offer_cycle() -> tuple[OfferingRecord | None, str]:
    """Render the offering and record it. Return (record, text).

    With no usable handshake: (None, "") and no state is written -- the absence
    invariant. ``inspect_handshake`` and ``refusal_text`` say why.
    With an offer already pending: (None, a refusal naming the open cycle),
    because a second offer used to overwrite the first silently.
    The handshake is NOT consumed here; ``close_cycle`` consumes it.
    """
    try:
        pending = _read_pending()
    except DamagedPending as e:
        return None, f"[!] {e}. Nothing new is offered over it; look at it before removing it."
    if pending is not None:
        return None, (
            f"[!] Cycle {pending.get('cycle_id', '?')} is already offered "
            "and not closed. Close it first: divineos auto-cycle close --outcome <...>"
        )

    handshake = read_handshake()
    if handshake is None:
        return None, ""

    use_counts = _use_counts_since_last_cycle()
    record = OfferingRecord(
        cycle_id=handshake.cycle_id,
        offered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        menu_shown=[task.key for task in REST_TASKS],
        use_counts_at_offering=dict(use_counts),
        handshake_summary=_handshake_summary(handshake),
    )
    path = _pending_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
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
    return record, render_menu(handshake, use_counts)


def parse_outcome(outcome: str) -> tuple[str, str | None]:
    """The one reader of the outcome grammar. Returns (outcome, chosen_key).

    ``chose:<key>`` requires a key that is a real REST_TASKS option. Anything
    else raises ValueError -- the July code accepted any string, and three
    readers of one grammar drifted apart (Lovelace on the walk).
    """
    text = (outcome or "").strip()
    if text in _PLAIN_OUTCOMES:
        return text, None
    if text.startswith("chose:"):
        key = text.split(":", 1)[1].strip()
        if key in {task.key for task in REST_TASKS}:
            return f"chose:{key}", key
        raise ValueError(f"{key!r} is not a rest option")
    raise ValueError(
        f"{outcome!r} is not an outcome: use chose:<key>, no-pull-honest, timeout or aborted"
    )


def close_cycle(
    outcome: str,
    real_shift: bool | None = None,
    notes: str = "",
) -> CloseOutcome | None:
    """Close the pending cycle: log the outcome, then clear the markers.

    Order is load-bearing. The audit line is written FIRST and a failed write
    raises, leaving the pending marker in place -- the July code swallowed the
    error and then deleted the pending marker, so the only evidence the
    falsifier has could vanish without a trace. The handshake is cleared only
    while it still carries this cycle's id.

    Returns None when nothing is pending. Raises ValueError on an outcome the
    grammar does not know, and DamagedPending when the pending record is broken.
    """
    outcome, chosen_key = parse_outcome(outcome)

    pending = _read_pending()
    if pending is None:
        return None

    cycle_id = str(pending.get("cycle_id", ""))
    try:
        offered_ts = time.mktime(
            time.strptime(str(pending.get("offered_at", "")), "%Y-%m-%dT%H:%M:%SZ")
        )
    except (ValueError, TypeError):
        offered_ts = time.time()

    record = CloseOutcome(
        cycle_id=cycle_id,
        closed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        outcome=outcome,
        chosen_key=chosen_key,
        duration_sec=max(0.0, time.time() - offered_ts),
        real_shift=real_shift,
        notes=notes,
    )

    _append_audit_log(pending, record)  # raises on failure; nothing is cleared

    current = read_handshake_marker()
    if isinstance(current, dict) and str(current.get("cycle_id", "")) == cycle_id:
        clear_handshake_marker()
    _pending_path().unlink(missing_ok=True)
    return record


def _append_audit_log(pending: dict[str, Any], outcome: CloseOutcome) -> None:
    """Append one closed-cycle record. A write failure RAISES."""
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
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _audit_entries() -> list[dict[str, Any]]:
    path = _audit_log_path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            out.append(entry)
    return out


def compute_falsifier_ratio() -> tuple[int, int, float | None]:
    """(numerator, denominator, ratio) for prereg-4a7ed0c77c34.

    Numerator: engaged cycles that registered real-shift (``chose:<key>`` with
    real_shift True). Denominator: engaged cycles plus timeouts and non-fatal
    aborts. Two kinds leave the ratio:

    - aborted after a fatal phase 1 -- infrastructure, not the register;
    - no-pull-honest -- valid and not a failure (Aria's July dissent), but not
      a success either. The prereg sets real rest choices against template
      execution; it does not name not-choosing as success, and counting it as
      one let a run of cycles that never engaged score 1.0. Reported apart by
      ``no_pull_count``.
    """
    numerator = denominator = 0
    for entry in _audit_entries():
        outcome = str(entry.get("outcome", ""))
        fatal = bool((entry.get("handshake_summary") or {}).get("fatal_step_failure"))
        if (outcome == "aborted" and fatal) or outcome == "no-pull-honest":
            continue
        denominator += 1
        if outcome.startswith("chose:") and entry.get("real_shift") is True:
            numerator += 1
    return numerator, denominator, (numerator / denominator if denominator else None)


def no_pull_count() -> int:
    """Closed cycles that ended no-pull-honest -- shown beside the ratio, never in it."""
    return sum(1 for e in _audit_entries() if e.get("outcome") == "no-pull-honest")


__all__ = [
    "CloseOutcome",
    "DamagedPending",
    "HandshakeResult",
    "NoHandshake",
    "OfferingRecord",
    "close_cycle",
    "compute_falsifier_ratio",
    "inspect_handshake",
    "no_pull_count",
    "offer_cycle",
    "parse_outcome",
    "read_handshake",
    "refusal_text",
    "render_menu",
]
