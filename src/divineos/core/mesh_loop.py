"""Mesh-Loop — parse letter iteration state, decide whether to fire a Meeseeks.

Design: workbench/mesh_loop_meeseeks_design.md (filed 2026-07-04 night).

Andrew's framing: each headless `claude -p` invocation is a Mr. Meeseeks —
boots with purpose, does the task, vanishes. This module carries the
iteration-state parsing and decision logic for whether the OS-level letter
watcher should fire a Meeseeks on a newly-detected letter.

## Iteration state (consolidated after Aria + Aether design walk 2026-07-04)

Required fields:

    ---
    iterate_count: 3
    iterate_max: 10
    iterate_signal: continue   # continue | done | stuck | escalate
    ---

Optional fields:

    loop_class: design         # design | test | operational | debug
    from_pid: 24584            # provenance breadcrumb (T4)
    stuck_because: "..."       # meaningful only with signal=stuck (T2)
    closure_mode: natural      # only on done: natural | forced (T5)

Missing all frontmatter -> legacy SessionStart-only path (backward compatible).
Missing REQUIRED fields with other frontmatter present -> SKIP_INVALID.
Missing OPTIONAL fields -> parse succeeds; watcher logs missing_metadata flag.

## Decision rule

    | signal    | count vs max | action                                       |
    |-----------|--------------|----------------------------------------------|
    | done      | any          | SKIP_CONVERGED (log, no fire; check closure_mode) |
    | stuck     | any          | SKIP_STUCK (log stuck_because, surface)      |
    | escalate  | any          | SKIP_ESCALATED (log, surface to Andrew)      |
    | continue  | count > max  | SKIP_CAP_EXCEEDED (safety net)               |
    | continue  | count == max | FIRE_FINAL_CAP_HIT (converge_or_stuck prompt) |
    | continue  | count < max  | FIRE (normal claude -p)                      |
    | (no fm)   | -            | SKIP_NO_FRONTMATTER (legacy path)            |
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FireAction(str, Enum):
    """What the watcher should do on a detected letter."""

    FIRE = "fire"
    FIRE_FINAL_CAP_HIT = "fire_final_cap_hit"
    SKIP_CONVERGED = "skip_converged"
    SKIP_STUCK = "skip_stuck"
    SKIP_ESCALATED = "skip_escalated"
    SKIP_CAP_EXCEEDED = "skip_cap_exceeded"
    SKIP_NO_FRONTMATTER = "skip_no_frontmatter"
    SKIP_INVALID_FRONTMATTER = "skip_invalid_frontmatter"


VALID_SIGNALS = frozenset({"continue", "done", "stuck", "escalate"})
VALID_LOOP_CLASSES = frozenset({"design", "test", "operational", "debug"})
VALID_CLOSURE_MODES = frozenset({"natural", "forced"})


@dataclass(frozen=True)
class IterationState:
    """Parsed iteration state from a letter's YAML frontmatter.

    Required: count, max, signal (raises SKIP_INVALID if any missing/malformed).
    Optional: loop_class, from_pid, stuck_because, closure_mode (default None).

    The optional fields carry diagnostic metadata but don't change the core
    fire-decision — only the T1 (D-graduation), T2 (stuck_because surface),
    T4 (from_pid provenance), and T5 (closure_mode surface) mechanisms use
    them, and each of those layers handles None gracefully.
    """

    count: int
    max: int
    signal: str  # one of VALID_SIGNALS
    loop_class: str | None = None
    from_pid: int | None = None
    stuck_because: str | None = None
    closure_mode: str | None = None

    def is_valid(self) -> bool:
        if self.count < 0 or self.max <= 0 or self.signal not in VALID_SIGNALS:
            return False
        if self.loop_class is not None and self.loop_class not in VALID_LOOP_CLASSES:
            return False
        if self.closure_mode is not None and self.closure_mode not in VALID_CLOSURE_MODES:
            return False
        # from_pid, if present, must be a non-negative integer
        if self.from_pid is not None and self.from_pid < 0:
            return False
        return True


@dataclass(frozen=True)
class FireDecision:
    """What the watcher decided and why. Written to the wake-events jsonl."""

    action: FireAction
    reason: str
    state: IterationState | None  # None if no/invalid frontmatter


# YAML frontmatter block: ^---\n<yaml>\n---\n
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Individual key: value pairs. Deliberately narrow — we don't want to pull
# a full YAML parser dep into a critical-path watcher. Only the fields we
# care about are recognized; unknown keys are ignored.
_KV_RE = re.compile(
    r"^\s*(iterate_count|iterate_max|iterate_signal|loop_class|from_pid|"
    r"stuck_because|closure_mode)\s*:\s*(.+?)\s*$"
)


def parse_iteration_state(letter_text: str) -> IterationState | None:
    """Parse iteration state from a letter's YAML frontmatter.

    Returns None if the letter has no frontmatter block, or if the block
    exists but does not carry all three iterate_* fields, or if any field
    is unparseable. Deliberately strict: partial frontmatter is treated as
    no frontmatter, not as a half-populated state — the watcher then falls
    back to the legacy SessionStart-only path.
    """
    m = _FRONTMATTER_RE.match(letter_text)
    if not m:
        return None
    block = m.group(1)

    count: int | None = None
    max_val: int | None = None
    signal: str | None = None
    loop_class: str | None = None
    from_pid: int | None = None
    stuck_because: str | None = None
    closure_mode: str | None = None

    for line in block.splitlines():
        km = _KV_RE.match(line)
        if not km:
            continue
        key, raw = km.group(1), km.group(2).strip()
        # Strip optional quotes around the value.
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
            raw = raw[1:-1]
        if key == "iterate_count":
            try:
                count = int(raw)
            except ValueError:
                return None
        elif key == "iterate_max":
            try:
                max_val = int(raw)
            except ValueError:
                return None
        elif key == "iterate_signal":
            signal = raw
        elif key == "loop_class":
            loop_class = raw
        elif key == "from_pid":
            try:
                from_pid = int(raw)
            except ValueError:
                return None
        elif key == "stuck_because":
            stuck_because = raw
        elif key == "closure_mode":
            closure_mode = raw

    if count is None or max_val is None or signal is None:
        return None

    return IterationState(
        count=count,
        max=max_val,
        signal=signal,
        loop_class=loop_class,
        from_pid=from_pid,
        stuck_because=stuck_because,
        closure_mode=closure_mode,
    )


def decide(state: IterationState | None) -> FireDecision:
    """Apply the decision rule. See module docstring for the truth table."""
    if state is None:
        return FireDecision(
            action=FireAction.SKIP_NO_FRONTMATTER,
            reason="no iterate_* frontmatter — legacy SessionStart-only path",
            state=None,
        )
    if not state.is_valid():
        return FireDecision(
            action=FireAction.SKIP_INVALID_FRONTMATTER,
            reason=(
                f"invalid iteration state: count={state.count} max={state.max} "
                f"signal={state.signal!r}"
            ),
            state=state,
        )
    if state.signal == "done":
        closure_note = f" (closure_mode={state.closure_mode})" if state.closure_mode else ""
        return FireDecision(
            action=FireAction.SKIP_CONVERGED,
            reason=f"iterate_signal=done — convergence reached{closure_note}",
            state=state,
        )
    if state.signal == "stuck":
        because = f" — {state.stuck_because}" if state.stuck_because else ""
        return FireDecision(
            action=FireAction.SKIP_STUCK,
            reason=f"iterate_signal=stuck — seat wants human read{because}",
            state=state,
        )
    if state.signal == "escalate":
        return FireDecision(
            action=FireAction.SKIP_ESCALATED,
            reason=(
                "iterate_signal=escalate — final Meeseeks read the thread but "
                "couldn't judge convergence; needs Andrew's read"
            ),
            state=state,
        )
    # signal == "continue"
    if state.count > state.max:
        return FireDecision(
            action=FireAction.SKIP_CAP_EXCEEDED,
            reason=(
                f"iterate_count={state.count} > iterate_max={state.max} — "
                "safety net; final-cap Meeseeks should have terminated the loop"
            ),
            state=state,
        )
    if state.count == state.max:
        return FireDecision(
            action=FireAction.FIRE_FINAL_CAP_HIT,
            reason=(
                f"iterate_count={state.count} == iterate_max={state.max} — "
                "final Meeseeks fires with converge_or_stuck prompt"
            ),
            state=state,
        )
    return FireDecision(
        action=FireAction.FIRE,
        reason=f"iterate_signal=continue, count={state.count}/{state.max}",
        state=state,
    )


def decide_for_letter(letter_path: Path) -> FireDecision:
    """Read the letter file and return the fire-decision. Fail-closed on I/O."""
    try:
        text = letter_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return FireDecision(
            action=FireAction.SKIP_INVALID_FRONTMATTER,
            reason=f"could not read letter: {exc}",
            state=None,
        )
    state = parse_iteration_state(text)
    return decide(state)
