"""Seven doorbells — one OS-side router behind each harness hook event.

Andrew 2026-06-30, the founding principle (via Aether's migration tracker):

    *"Make the hooks dumber so they can't be wrong; put the logic in the OS so
    the decision happens where the contract is. Replace the decision with
    structure so it makes the choice for you."*

Andrew 2026-08-06: *"you had a brilliant idea of consolidating the 100 hooks
to 7 hooks and routing the logic into the OS itself."*

## Why seven

The harness offers exactly seven hook event types. Measured 2026-08-06, all
100 registrations live under them: SessionStart 14, UserPromptSubmit 30,
PreCompact 1, PostCompact 1, PreToolUse 26, PostToolUse 11, Stop 17.

Seven is not a compression target chosen for tidiness. It is the number of
doors the building has. One doorbell per door; the OS decides who is behind it.

## The cost this design exists to pay for

100 separate hook files have one virtue worth protecting: **a bug in one
affects exactly one surface.** The blast radius is naturally tiny. A router
inverts that — one bug could break every surface on an event.

So fault isolation is not a feature here, it is the whole architecture:

* **Every surface runs in its own guard.** A surface that raises is recorded in
  the result and skipped. It can never take another surface down with it.
* **No short-circuit on refusal.** Every surface runs even after one has
  refused, and all refusals are reported together. Short-circuiting would hide
  the second reason behind the first — and this substrate has spent days
  finding failures that hid behind other failures.
* **A router-level crash still exits 0.** A broken doorbell must never block
  work; that is the same fail-open contract every hook already has.

## The third word

``RouterResult.errored`` lists surfaces that raised. A surface that could not
run is not a surface that passed, and the result keeps those separate from
``refusals`` (ran, said no) and ``ran`` (ran, said nothing). Three states,
because two would let "the check crashed" render as "the check was fine" —
which is the single defect class this substrate has found most often.

## Migration is incremental, on purpose

The router coexists with the existing `.sh` hooks. Surfaces move one at a
time; a hook file is deleted only once its replacement is proven live. A
big-bang cutover of 100 hooks is precisely the shape that leaves a silent hole
nobody notices for a fortnight — see the cross-substrate emitter, dead from
2026-07-21 because one delegate line vanished from a regenerated file.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from dataclasses import dataclass, field

# The seven doors. Measured from .claude/settings.json 2026-08-06; this tuple
# is the authority the router validates against, so an unknown event is a
# loud error rather than a silent no-op.
EVENTS: tuple[str, ...] = (
    "SessionStart",
    "UserPromptSubmit",
    "PreCompact",
    "PostCompact",
    "PreToolUse",
    "PostToolUse",
    "Stop",
)


@dataclass
class SurfaceOutcome:
    """What one surface did. ``refused`` blocks; ``error`` means it could not run."""

    name: str
    output: str = ""
    refused: bool = False
    reason: str = ""
    error: str | None = None


@dataclass
class RouterResult:
    """Aggregate of every surface for one event.

    ``ran``, ``refusals`` and ``errored`` are deliberately three lists rather
    than a pass/fail pair. A surface that crashed did not pass.
    """

    event: str
    ran: list[SurfaceOutcome] = field(default_factory=list)
    refusals: list[SurfaceOutcome] = field(default_factory=list)
    errored: list[SurfaceOutcome] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.refusals)

    def stdout(self) -> str:
        """Everything the surfaces wanted to say, in registration order."""
        return "\n".join(o.output for o in self.ran if o.output.strip())

    def stderr(self) -> str:
        """Refusals first, then any surface that could not run.

        Errors are reported even though they do not block. A surface failing
        silently is how a check that never ran becomes indistinguishable from
        a check that passed.
        """
        parts: list[str] = []
        for o in self.refusals:
            parts.append(f"BLOCKED by {o.name}: {o.reason}")
        for o in self.errored:
            parts.append(
                f"[router] surface {o.name} COULD NOT RUN: {o.error} "
                "— this is not the same as it passing."
            )
        return "\n".join(parts)

    def exit_code(self) -> int:
        """2 blocks the tool call; 0 allows. Errors never block."""
        return 2 if self.refusals else 0


# event -> [(surface_name, callable)]. Populated by register().
_Surface = Callable[[dict], "SurfaceOutcome | None"]

_REGISTRY: dict[str, list[tuple[str, _Surface]]] = {e: [] for e in EVENTS}


def register(event: str, name: str, fn: _Surface) -> None:
    """Attach a surface to an event. Order of registration is order of run."""
    if event not in _REGISTRY:
        raise ValueError(f"unknown hook event {event!r}; known: {', '.join(EVENTS)}")
    if any(n == name for n, _ in _REGISTRY[event]):
        raise ValueError(f"surface {name!r} already registered for {event}")
    _REGISTRY[event].append((name, fn))


def registered(event: str) -> list[str]:
    """Surface names attached to ``event``, in run order."""
    return [n for n, _ in _REGISTRY.get(event, [])]


def clear(event: str | None = None) -> None:
    """Drop registrations. Tests only — never called from a doorbell."""
    if event is None:
        for e in _REGISTRY:
            _REGISTRY[e] = []
    else:
        _REGISTRY[event] = []


def dispatch(event: str, payload: dict) -> RouterResult:
    """Run every surface for ``event``. One failure never stops the rest.

    This function is the load-bearing piece the whole consolidation rests on,
    so it does the least possible: iterate, isolate, collect. No surface can
    see another's result, and none can prevent another from running.
    """
    result = RouterResult(event=event)
    if event not in _REGISTRY:
        result.errored.append(SurfaceOutcome(name="<router>", error=f"unknown event {event!r}"))
        return result

    for name, fn in _REGISTRY[event]:
        try:
            outcome = fn(payload)
        except Exception as exc:  # noqa: BLE001 — isolation IS the design
            result.errored.append(
                SurfaceOutcome(
                    name=name,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        if outcome is None:
            continue
        if outcome.error is not None:
            result.errored.append(outcome)
        elif outcome.refused:
            # No break. Every surface still runs; every refusal is reported.
            result.refusals.append(outcome)
        else:
            result.ran.append(outcome)
    return result


def main(event: str, payload: dict) -> int:
    """Doorbell entry point. Prints, returns the exit code, never raises.

    A router that crashes must not block work — same fail-open contract the
    hooks already carry.
    """
    import sys

    try:
        result = dispatch(event, payload)
    except Exception:  # noqa: BLE001 — a broken router must never wall me in
        print(f"[router] dispatch crashed for {event}:", file=sys.stderr)
        print(traceback.format_exc()[:800], file=sys.stderr)
        return 0

    out = result.stdout()
    if out:
        print(out)
    err = result.stderr()
    if err:
        print(err, file=sys.stderr)
    return result.exit_code()
