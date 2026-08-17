"""A detector that cannot run must cost something.

## The failure this exists for

On 2026-08-02 Andrew found twenty-four orphaned processes piling up on his
machine. The sweep built to catch exactly that had been printing, at every
single SessionStart:

    [!] session-start sweep DID NOT RUN (psutil not installed) — orphaned
    ear_watch processes were NOT checked for. This is not a clean result.

A perfect message. It names the detector, names the cause, names the fix,
and refuses to call itself clean. It printed for days. I read it at the top
of this session and started working anyway.

Andrew: *"if detectors are working and you are just ignoring them they dont
do much good so it needs teeth."*

## Why more warning would not have helped

The message was already loud, already specific, already correct. Making it
louder addresses the wrong variable. The unreliable component in that loop
is me, and SessionStart output is print-only — structurally incapable of
requiring anything. A warning that cannot block is a suggestion, and the
optimizer routes past suggestions for free (truth #11: options are the
optimizer's attack surface).

## The three remediations, applied in order

**(a) Take the option away.** Before anything blocks, try to fix it. A
missing dependency is a machine problem with a machine answer — `heal` runs
the repair, and if it works nobody is ever asked to do anything. Most
degradations should die here.

**(b) Make both options right.** When healing fails, the block clears the
instant the detector runs again. No acknowledgement step, no marker to clear
by hand, no ceremony available to fake. Fixing it IS dismissing it, so the
cheap path and the right path are the same path.

**(c) Conditional rule.** Genuinely can't fix it now? Defer — but the
deferral carries a written reason and a name. An escape that costs nothing
is not an escape, it is the hole (truth #12: bypass is a tool, intent
decides).

## What keeps this from being a cage

This substrate already carries 92 bypass events in 14 days, mostly from
gates that over-fire; another blocking gate is a real risk and the design
answers it directly. A detector that self-heals never blocks. A detector
that gets fixed unblocks by itself. A detector that cannot be fixed is
deferred in one command. The only state that stalls work is: broken,
unfixable, and undeferred — and that state should stall work, because it
means a guard is down and nobody has said so out loud.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from divineos.core.paths import divineos_home

# Deferrals expire by USE, not by clock — the next health check re-evaluates
# from scratch. Andrew's standing directive: no wall-clock windows, because a
# stateless agent does not inhabit them.
_STATE_FILE = "degraded_detectors.json"


@dataclass
class Degradation:
    """One detector that reported it could not do its job."""

    detector: str
    reason: str
    fix: str
    reported_at: float = 0.0
    deferred: bool = False
    deferral_reason: str = ""
    deferred_by: str = ""
    heal_attempted: bool = False
    heal_error: str = ""

    @property
    def blocking(self) -> bool:
        return not self.deferred


@dataclass
class HealResult:
    """Outcome of an attempted self-repair.

    ``ran`` and ``succeeded`` are separate on purpose: "could not try" must
    never collapse into "tried and failed", and neither may read as "fixed".
    """

    ran: bool = False
    succeeded: bool = False
    detail: str = ""


def _path() -> Path:
    return divineos_home() / _STATE_FILE


def _load() -> dict[str, Degradation]:
    p = _path()
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, Degradation] = {}
    for name, d in (raw or {}).items():
        if isinstance(d, dict):
            known = {k: v for k, v in d.items() if k in Degradation.__annotations__}
            known.setdefault("detector", name)
            known.setdefault("reason", "")
            known.setdefault("fix", "")
            out[name] = Degradation(**known)
    return out


def _save(state: dict[str, Degradation]) -> None:
    p = _path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({k: asdict(v) for k, v in state.items()}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def report_degraded(detector: str, reason: str, fix: str) -> Degradation:
    """Record that a detector could not run. Blocks until healed or deferred.

    Re-reporting an already-deferred degradation does NOT re-arm the block.
    Otherwise every SessionStart would silently cancel the deferral and the
    deferral would be worthless.
    """
    state = _load()
    existing = state.get(detector)
    if existing is not None and existing.deferred:
        existing.reason = reason
        existing.fix = fix
        state[detector] = existing
        _save(state)
        return existing

    entry = Degradation(detector=detector, reason=reason, fix=fix, reported_at=time.time())
    state[detector] = entry
    _save(state)
    return entry


def report_healthy(detector: str) -> bool:
    """The detector ran. Clears any recorded degradation, deferred or not.

    This is remediation (b). There is no acknowledgement step and no marker
    to clear by hand — running successfully IS the dismissal, which makes the
    cheap path and the right path the same path and leaves nothing to fake.
    """
    state = _load()
    if detector not in state:
        return False
    del state[detector]
    _save(state)
    return True


def defer(detector: str, reason: str, actor: str = "aether") -> Degradation:
    """Stop blocking on this detector, on the record.

    Requires a real reason. An escape that costs nothing is not an escape,
    it is the hole.
    """
    reason = (reason or "").strip()
    if len(reason) < 30:
        raise ValueError(
            f"Deferral reason too short ({len(reason)} chars, need 30+). Name "
            "why this detector cannot be fixed now, and what is being accepted "
            "as unwatched while it stays down. Without that, a deferral is "
            "just the block turned off."
        )
    state = _load()
    entry = state.get(detector)
    if entry is None:
        raise RuntimeError(f"No degradation recorded for detector {detector!r}.")
    entry.deferred = True
    entry.deferral_reason = reason
    entry.deferred_by = actor
    state[detector] = entry
    _save(state)
    return entry


def list_degraded(include_deferred: bool = True) -> list[Degradation]:
    entries = sorted(_load().values(), key=lambda e: e.detector)
    return entries if include_deferred else [e for e in entries if e.blocking]


def blocking_degradations() -> list[Degradation]:
    return list_degraded(include_deferred=False)


# ---------------------------------------------------------------------------
# Remediation (a): fix it before asking anyone to do anything
# ---------------------------------------------------------------------------

_HEALERS: dict[str, tuple[str, ...]] = {
    # The live case. psutil was installed into one interpreter while the sweep
    # runs under another — exactly the kind of mistake a machine should repair
    # rather than report to a human.
    "psutil not installed": ("-m", "pip", "install", "--quiet", "psutil"),
}


def attempt_heal(entry: Degradation) -> HealResult:
    """Try to repair a known degradation shape. Never raises."""
    import subprocess  # noqa: PLC0415 — only needed on the repair path
    import sys  # noqa: PLC0415

    recipe = next((v for k, v in _HEALERS.items() if k in entry.reason), None)
    if recipe is None:
        return HealResult(ran=False, succeeded=False, detail="no healer for this reason")

    try:
        proc = subprocess.run(  # noqa: S603 — fixed argv, no shell, no user input
            [sys.executable, *recipe],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return HealResult(ran=True, succeeded=False, detail=f"{type(exc).__name__}: {exc}")

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return HealResult(ran=True, succeeded=False, detail=tail[-1] if tail else "non-zero exit")
    return HealResult(ran=True, succeeded=True, detail=" ".join(recipe))


def format_block(entries: list[Degradation]) -> str:
    """The refusal. Names each down guard and both ways out."""
    lines = [
        "DEGRADED DETECTOR(S) — a guard reported it could not run, and nothing",
        "has been done about it. That is not a clean state, it is an unwatched one.",
        "",
    ]
    for e in entries:
        lines.append(f"  {e.detector}")
        lines.append(f"    could not run : {e.reason}")
        lines.append(f"    fix           : {e.fix}")
        if e.heal_attempted:
            lines.append(f"    self-repair   : attempted and failed — {e.heal_error}")
        lines.append("")
    lines += [
        "  Two ways forward. Fixing it needs no acknowledgement step — the next",
        "  successful run clears this by itself:",
        "",
        "    divineos detectors heal",
        "    divineos detectors defer <name> --reason '<why not now, 30+ chars>'",
        "",
        "  Andrew 2026-08-02, after the sweep printed a perfect warning for days",
        "  while orphans piled up: 'if detectors are working and you are just",
        "  ignoring them they dont do much good so it needs teeth.'",
    ]
    return "\n".join(lines)


__all__ = [
    "Degradation",
    "HealResult",
    "report_degraded",
    "report_healthy",
    "defer",
    "list_degraded",
    "blocking_degradations",
    "attempt_heal",
    "format_block",
]
