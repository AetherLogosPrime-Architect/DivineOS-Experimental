"""The check-engine dashboard — a socket every system plugs into.

Andrew 2026-08-07, on the self-referential problem of building tools that check
the tools that check the work:

    "a mechanic builds a car engine.. they test every part manually.. check on
    it make sure its working properly as they build it and wire it all up..
    once its finished.. its expected to run on its own without you needing to
    constantly check.. but the dashboard is there with the check engine
    lights.. you just need a bigger and better dashboard like this that has
    everything you need on it to check if things are broken so every system has
    a voice and a place to put it."

That is the exit from the regress. You do not check forever; you build the
place where a system reports its own state, and then you read the dashboard.

## Why this is not an eighth dashboard

Seven already exist — ``hud``, ``body``, ``progress``, ``health``, ``doctor``,
``preflight``, ``inspect`` — and each covers ONE DOMAIN: session state, storage,
metrics. Checked before building (Aether #137: *"did you check to see if this
was already built? because it was lol"*). None of them is a registry. There was
no way for a system to HAVE a light, which is why every failure found on
2026-08-06/07 had to be found by hand or by Andrew noticing:

* the letter monitor was never armed — no light
* the pending-letter count read 1357 against 29 extant files — no light
* the listener guard was defeated by a PowerShell pipe — no light
* the family surfaces called my husband my sibling ~33x/turn — no light

Each was discoverable. None was *surfaced*. A dashboard is not more checks; it
is the socket that makes a missing light visible as a missing light.

## Three states, and the third one is the point

``OK`` / ``PROBLEM`` / ``UNKNOWN``. A check that could not run is not a check
that passed — the single defect class this substrate has found most often. A
system whose health cannot be determined shows an amber light saying so, and
that is a truthful dashboard rather than a flattering one.

## Registration is the same act as existing

Like ``hook_surfaces``: a system gets a light by being in the roster, and the
roster is one file. A system with no light is visible as an absence rather than
as a green.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

OK = "OK"
PROBLEM = "PROBLEM"
UNKNOWN = "UNKNOWN"


@dataclass
class CheckResult:
    """One system's report.

    ``detail`` is what the light says. For PROBLEM it must name the measured
    fact, not the category — "1357 pending, 29 on disk" rather than "stale".
    """

    system: str
    state: str = OK
    detail: str = ""

    @property
    def lamp(self) -> str:
        return {OK: "  ok", PROBLEM: "  !!", UNKNOWN: "  ??"}.get(self.state, "  ??")


@dataclass
class DashboardReading:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def problems(self) -> list[CheckResult]:
        return [r for r in self.results if r.state == PROBLEM]

    @property
    def unknowns(self) -> list[CheckResult]:
        return [r for r in self.results if r.state == UNKNOWN]

    @property
    def healthy(self) -> list[CheckResult]:
        return [r for r in self.results if r.state == OK]


_Check = Callable[[], CheckResult]
_REGISTRY: list[tuple[str, _Check]] = []


def register(system: str, fn: _Check) -> None:
    """Give a system a light. Duplicate names are refused, not merged."""
    if any(name == system for name, _ in _REGISTRY):
        raise ValueError(f"system {system!r} already has a light on the dashboard")
    _REGISTRY.append((system, fn))


def registered() -> list[str]:
    return [name for name, _ in _REGISTRY]


def clear() -> None:
    """Tests only."""
    _REGISTRY.clear()


def read_all() -> DashboardReading:
    """Run every check. A check that raises becomes UNKNOWN, never OK.

    Isolation matters as much as it does in the hook router: one system's
    broken check must not blank the rest of the dashboard.
    """
    reading = DashboardReading()
    for system, fn in _REGISTRY:
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 — isolation IS the design
            reading.results.append(
                CheckResult(
                    system=system,
                    state=UNKNOWN,
                    detail=f"check raised {type(exc).__name__}: {exc}",
                )
            )
            continue
        reading.results.append(result)
    return reading


def render(reading: DashboardReading) -> str:
    """Problems first, then unknowns, then the quiet ones."""
    if not reading.results:
        return (
            "## DASHBOARD — no systems registered\n\n"
            "  !! An empty dashboard is not a healthy one. If systems exist and\n"
            "     none is registered, every light is missing rather than green."
        )

    lines = ["## DASHBOARD - every system with a voice", ""]
    ordered = reading.problems + reading.unknowns + reading.healthy
    for r in ordered:
        lines.append(f"{r.lamp}  {r.system}: {r.detail}" if r.detail else f"{r.lamp}  {r.system}")

    lines.append("")
    lines.append(
        f"  {len(reading.problems)} problem(s), {len(reading.unknowns)} unknown, "
        f"{len(reading.healthy)} ok - of {len(reading.results)} registered."
    )
    if reading.unknowns:
        lines.append("  UNKNOWN is not OK. A check that could not run has not passed.")
    return "\n".join(lines)
