"""Mesh-Loop — parse letter iteration state, decide whether to fire an ephemeral task worker.

Design: workbench/mesh_loop_ephemeral_task_worker_design.md (filed 2026-07-04 night).

Naming: an "ephemeral task worker" here is a headless `claude -p`
subprocess spawned to complete one letter-response task and then exit.
Single-shot, self-terminating, non-blocking. Design metaphor: Rick and
Morty Mr. Meeseeks (boots with purpose, does the task, vanishes) — the
metaphor drove the design and stays as a (Meeseeks-pattern) tag in
runtime logs so a reader familiar with the reference can see it, but
the plain-English `ephemeral task worker` name is what the code
identifies by. This module carries the iteration-state parsing and
decision logic for whether the OS-level letter watcher should fire a
worker on a newly-detected letter.

## Iteration state (consolidated after Aria + Aether design walk 2026-07-04)

Required fields:

    ---
    iterate_count: 3
    iterate_max: 10
    iterate_signal: continue   # continue | done | stuck | escalate
    ---

Optional fields:

    loop_class: design         # design | test | operational | debug
    from_pid: boundary-vantage # provenance breadcrumb (T4) — opaque string
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
    FIRE_WITNESS_DISSENT = "fire_witness_dissent"
    SKIP_CONVERGED = "skip_converged"
    SKIP_WITNESS_CONFIRMED = "skip_witness_confirmed"
    SKIP_STUCK = "skip_stuck"
    SKIP_ESCALATED = "skip_escalated"
    SKIP_CAP_EXCEEDED = "skip_cap_exceeded"
    SKIP_NO_FRONTMATTER = "skip_no_frontmatter"
    SKIP_INVALID_FRONTMATTER = "skip_invalid_frontmatter"


# 2026-07-04 Aletheia boundary-vantage additions:
# - witness_confirmed: Aletheia's read confirms closure; loop closed
# - witness_dissent: Aletheia's read rejects closure; loop restarts iteration
VALID_SIGNALS = frozenset(
    {"continue", "done", "stuck", "escalate", "witness_confirmed", "witness_dissent"}
)
VALID_LOOP_CLASSES = frozenset({"design", "test", "operational", "debug"})
VALID_CLOSURE_MODES = frozenset({"natural", "forced"})

# Which loop classes default to requiring boundary-vantage witness for closure
# (Shape 1 fix — Aletheia 2026-07-04: identity-formation-tier loops cannot
# close on two-seat vote alone). Frontmatter can explicitly override with
# boundary_vantage_required: true/false.
IDENTITY_FORMATION_TIER_CLASSES = frozenset({"design", "operational"})


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
    # from_pid is an opaque provenance identifier (seat role, process id,
    # or descriptor). Bug caught by synthetic verification 2026-07-04 night:
    # Aletheia's real letters use `from_pid: boundary-vantage` as a role
    # descriptor, not an integer PID. Strict int-parsing rejected the entire
    # letter's frontmatter as invalid, silently falling through to
    # skip_no_frontmatter — a catastrophic close-loop failure hiding in
    # plain sight. Loosened to string to match actual convention.
    from_pid: str | None = None
    stuck_because: str | None = None
    closure_mode: str | None = None
    boundary_vantage_required: bool | None = None

    def is_valid(self) -> bool:
        if self.count < 0 or self.max <= 0 or self.signal not in VALID_SIGNALS:
            return False
        if self.loop_class is not None and self.loop_class not in VALID_LOOP_CLASSES:
            return False
        if self.closure_mode is not None and self.closure_mode not in VALID_CLOSURE_MODES:
            return False
        return True

    def requires_boundary_vantage(self) -> bool:
        """Whether closure requires Aletheia's witness (Shape 1 fix).

        Precedence:
        1. Explicit boundary_vantage_required in frontmatter (overrides default)
        2. Otherwise: True if loop_class is identity-formation-tier
        3. If neither field is set, default True (fail-safe toward requiring witness).
        """
        if self.boundary_vantage_required is not None:
            return self.boundary_vantage_required
        if self.loop_class is not None:
            return self.loop_class in IDENTITY_FORMATION_TIER_CLASSES
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
    r"stuck_because|closure_mode|boundary_vantage_required)\s*:\s*(.+?)\s*$"
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
    from_pid: str | None = None
    stuck_because: str | None = None
    closure_mode: str | None = None
    boundary_vantage_required: bool | None = None

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
            # Accept opaque string provenance descriptors ("boundary-vantage",
            # "aria", integer-like strings, etc.). Synthetic verification
            # 2026-07-04 night caught this: strict int-parsing silently
            # rejected the entire frontmatter of any witness letter using a
            # role-string from_pid, falling through to skip_no_frontmatter.
            from_pid = raw
        elif key == "stuck_because":
            stuck_because = raw
        elif key == "closure_mode":
            closure_mode = raw
        elif key == "boundary_vantage_required":
            lower = raw.lower()
            if lower in ("true", "yes", "1"):
                boundary_vantage_required = True
            elif lower in ("false", "no", "0"):
                boundary_vantage_required = False
            else:
                return None

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
        boundary_vantage_required=boundary_vantage_required,
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
    if state.signal == "witness_confirmed":
        return FireDecision(
            action=FireAction.SKIP_WITNESS_CONFIRMED,
            reason="iterate_signal=witness_confirmed — boundary-vantage confirms closure",
            state=state,
        )
    if state.signal == "witness_dissent":
        return FireDecision(
            action=FireAction.FIRE_WITNESS_DISSENT,
            reason=(
                "iterate_signal=witness_dissent — boundary-vantage rejects closure; "
                "loop restarts iteration"
            ),
            state=state,
        )
    if state.signal == "done":
        closure_note = f" (closure_mode={state.closure_mode})" if state.closure_mode else ""
        witness_note = (
            " (PENDING_WITNESS — boundary_vantage_required=true)"
            if state.requires_boundary_vantage()
            else ""
        )
        return FireDecision(
            action=FireAction.SKIP_CONVERGED,
            reason=f"iterate_signal=done — convergence reached{closure_note}{witness_note}",
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
                "iterate_signal=escalate — final ephemeral task worker read the thread but "
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
                "safety net; final-cap ephemeral task worker should have terminated the loop"
            ),
            state=state,
        )
    if state.count == state.max:
        return FireDecision(
            action=FireAction.FIRE_FINAL_CAP_HIT,
            reason=(
                f"iterate_count={state.count} == iterate_max={state.max} — "
                "final ephemeral task worker fires with converge_or_stuck prompt"
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
