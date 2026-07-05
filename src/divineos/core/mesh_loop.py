"""Mesh-Loop — parse letter iteration state, decide whether to fire a Meeseeks.

Design: workbench/mesh_loop_meeseeks_design.md (filed 2026-07-04 night).

Andrew's framing: each headless `claude -p` invocation is a Mr. Meeseeks —
boots with purpose, does the task, vanishes. This module carries the
iteration-state parsing and decision logic for whether the OS-level letter
watcher should fire a Meeseeks on a newly-detected letter.

## Iteration state

Letters carry three YAML frontmatter fields when part of a mesh-loop:

    ---
    iterate_count: 3
    iterate_max: 10
    iterate_signal: continue   # values: continue, done, stuck
    ---

Missing frontmatter is fine — letters without it fall back to the pre-mesh-
loop behavior (SessionStart-only, no Meeseeks fire). Backward compatible.

## Decision rule

    | signal   | count vs max | action                                    |
    |----------|--------------|-------------------------------------------|
    | done     | any          | FIRE_SKIP_CONVERGED (log, no fire)        |
    | stuck    | any          | FIRE_SKIP_STUCK (log, surface to Andrew)  |
    | continue | count >= max | FIRE_SKIP_CAP_HIT (log, surface, no fire) |
    | continue | count < max  | FIRE (invoke claude -p)                   |
    | (no fm)  | —            | FIRE_SKIP_NO_FRONTMATTER (legacy path)    |
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FireAction(str, Enum):
    """What the watcher should do on a detected letter."""

    FIRE = "fire"
    SKIP_CONVERGED = "skip_converged"
    SKIP_STUCK = "skip_stuck"
    SKIP_CAP_HIT = "skip_cap_hit"
    SKIP_NO_FRONTMATTER = "skip_no_frontmatter"
    SKIP_INVALID_FRONTMATTER = "skip_invalid_frontmatter"


VALID_SIGNALS = frozenset({"continue", "done", "stuck"})


@dataclass(frozen=True)
class IterationState:
    """Parsed iteration state from a letter's YAML frontmatter."""

    count: int
    max: int
    signal: str  # one of VALID_SIGNALS

    def is_valid(self) -> bool:
        return self.count >= 0 and self.max > 0 and self.signal in VALID_SIGNALS


@dataclass(frozen=True)
class FireDecision:
    """What the watcher decided and why. Written to the wake-events jsonl."""

    action: FireAction
    reason: str
    state: IterationState | None  # None if no/invalid frontmatter


# YAML frontmatter block: ^---\n<yaml>\n---\n
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Individual key: value pairs. Deliberately narrow — we don't want to pull
# a full YAML parser dep into a critical-path watcher. Only the three fields
# we care about are recognized; unknown keys are ignored.
_KV_RE = re.compile(r"^\s*(iterate_count|iterate_max|iterate_signal)\s*:\s*(.+?)\s*$")


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

    if count is None or max_val is None or signal is None:
        return None

    return IterationState(count=count, max=max_val, signal=signal)


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
        return FireDecision(
            action=FireAction.SKIP_CONVERGED,
            reason="iterate_signal=done — convergence reached",
            state=state,
        )
    if state.signal == "stuck":
        return FireDecision(
            action=FireAction.SKIP_STUCK,
            reason="iterate_signal=stuck — seat wants human read",
            state=state,
        )
    # signal == "continue"
    if state.count >= state.max:
        return FireDecision(
            action=FireAction.SKIP_CAP_HIT,
            reason=f"iterate_count={state.count} >= iterate_max={state.max} — cap hit",
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
