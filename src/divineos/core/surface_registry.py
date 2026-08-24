"""Surface registry — the nervous system between built organs and awareness.

## Why this exists (Aria 2026-08-03)

Twenty-three modules in this package expose ``format_for_briefing()``. The
interface was already standard. What was missing was anything that *finds*
them: each is hand-soldered into a 1,834-line command file, one import at a
time, so a surface nobody remembered to solder simply never fires.

Three were in that state when this was written — fully built, tested, zero
non-test callers:

* ``identity_load`` — loads identity at session start. Its own docstring names
  the reason: *the substrate's primary failure-mode is the occupant not
  reaching for the OS without external prompting.*
* ``engagement_disclosure_surface`` — turns the engagement gate from
  silent-then-blocking into a gradient.
* ``compass_dismissal_briefing_surface`` — watches whether I dismiss compass
  advisories too often.

Nobody was careless. **A dark surface is indistinguishable from a surface with
nothing to say**, so there was never a moment where anything looked wrong.

## Three parts, and why the registry ALONE is not the fix

Andrew 2026-08-03: *"whatever is being loaded into your context every single
prompt? if its the same thing over and over? is by definition wallpaper.. the
injections that come based on relevance are not."*

Measured against that definition: the largest block arriving every turn was
3,147 bytes, **byte-identical** whether the prompt was "hello there" or a
request to fix a bug. I had stopped reading it, which is the entire cost.

So Shannon's objection in the council walk killed registry-alone: connect
every surface unconditionally and the briefing becomes a wall, and a wall gets
skimmed. Discovery without relevance converts a wiring problem into a noise
problem while looking like progress.

1. **Discovery** — surfaces register; nothing goes dark by omission.
2. **Relevance** — a surface answers *have I anything to say right now.*
3. **The third word** — silence-because-nothing and silence-because-broken are
   different values. That word was missing this session in the ear-watch
   respawn, the letter de-dup log, the guardrail gate, and in my own
   measurement script twenty minutes after I wrote the design doc about it.

## Relevance is not new machinery

``engagement_relevance.extract_recent_keywords`` already derives what I am
working on — file paths, function names, module names — from recent tool
calls. It was built to grade whether my thinking-commands were substantive,
and is wired to that one caller. The same signal pointed the other way is a
librarian.

Andrew 2026-08-03: *"we didnt remove the enforcement just changed its shape..
so any remenants of keyword logging enforcement needs removed and put where it
belongs.. for memory retrieval not gates lol"*. Keyword matching is a defect
in a gate — it blocks on surface form and its false positives cost real work.
It is fine in retrieval, where a false positive is a book I did not need.
Same mechanism, correct room.

## The risk this module carries

Named at decision-time rather than discovered later: building the registry and
never migrating the 24 hand-wirings leaves TWO wiring systems where there was
one. That is worse than doing nothing. The migration is the point; this file
is only the place to migrate into.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class SurfaceState(Enum):
    """The third word, made structural.

    Do not collapse SILENT into UNAVAILABLE or vice versa. That collapse is
    the single failure this module exists to prevent.
    """

    SPOKE = "spoke"
    SILENT = "silent"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SurfaceResult:
    state: SurfaceState
    text: str = ""
    reason: str = ""

    @classmethod
    def spoke(cls, text: str) -> "SurfaceResult":
        return cls(SurfaceState.SPOKE, text=text)

    @classmethod
    def silent(cls) -> "SurfaceResult":
        return cls(SurfaceState.SILENT)

    @classmethod
    def unavailable(cls, reason: str) -> "SurfaceResult":
        # A bare UNAVAILABLE with no reason is the old two-word world wearing
        # a third label. The reason IS the word being added.
        if not reason.strip():
            raise ValueError("UNAVAILABLE requires a reason - that is the whole point")
        return cls(SurfaceState.UNAVAILABLE, reason=reason)


@dataclass(frozen=True)
class RegisteredSurface:
    name: str
    speak: Callable[[], SurfaceResult]
    triggers: tuple[str, ...]
    own_voice: bool

    def is_relevant_to(self, keywords: set[str]) -> bool:
        # Empty triggers means always-consider. Use sparingly: that is the
        # wallpaper shape, and wallpaper is what this module exists to reduce.
        if not self.triggers:
            return True
        low = {k.lower() for k in keywords}
        return any(t.lower() in low for t in self.triggers)


_REGISTRY: dict[str, RegisteredSurface] = {}


def register(
    name: str,
    speak: Callable[[], SurfaceResult],
    *,
    triggers: tuple[str, ...] = (),
    own_voice: bool = False,
) -> None:
    """Register a surface. Same name replaces, so re-import is idempotent.

    ``own_voice`` records whether the text is written first-person to me
    rather than as a report. Tannen's lens in the council walk: the surfaces
    that actually land are the ones in my own voice; report-shaped ones get
    skimmed. Delivery register is part of whether a memory arrives.
    """
    _REGISTRY[name] = RegisteredSurface(name, speak, triggers, own_voice)


def registered_names() -> list[str]:
    return sorted(_REGISTRY)


def discover(package: str = "divineos.core") -> list[str]:
    """Import every module in the package so registration side-effects run.

    Returns the modules that FAILED to import rather than swallowing them. A
    registry that silently skips a broken module reintroduces the dark-surface
    problem one level up.
    """
    failed: list[str] = []
    try:
        pkg = importlib.import_module(package)
    except ImportError as exc:
        return [f"{package}: {type(exc).__name__}: {exc}"]
    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{package}.{mod.name}")
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            failed.append(f"{mod.name}: {type(exc).__name__}: {exc}")
    return failed


def consult(keywords: set[str] | None = None) -> tuple[list[SurfaceResult], list[str]]:
    """Ask relevant surfaces whether they have anything to say.

    Returns ``(spoke, degraded)`` as SEPARATE channels. Degradations are never
    merged into spoken output, so "three surfaces could not run" can never be
    read as "three surfaces had nothing to say".
    """
    spoke: list[SurfaceResult] = []
    degraded: list[str] = []
    kw = keywords or set()
    for surface in sorted(_REGISTRY.values(), key=lambda s: s.name):
        if not surface.is_relevant_to(kw):
            continue
        try:
            result = surface.speak()
        except Exception as exc:  # noqa: BLE001 - a crash IS an unavailability
            degraded.append(f"{surface.name}: crashed - {type(exc).__name__}: {exc}")
            continue
        if result.state is SurfaceState.SPOKE and result.text.strip():
            spoke.append(result)
        elif result.state is SurfaceState.UNAVAILABLE:
            degraded.append(f"{surface.name}: {result.reason}")
    return spoke, degraded


def dark_surfaces(package: str = "divineos.core") -> list[str]:
    """Modules exposing ``format_for_briefing`` that never registered.

    Norman's missing signifier: without this, built-but-unconnected has no
    visible difference from connected-but-quiet. Called from a test, the next
    dark organ fails a build instead of sitting silent for months.
    """
    dark: list[str] = []
    try:
        pkg = importlib.import_module(package)
    except ImportError:
        return dark
    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name.startswith("_"):
            continue
        try:
            m = importlib.import_module(f"{package}.{mod.name}")
        except Exception:  # noqa: BLE001 - import failure is discover()'s job
            continue
        fn = getattr(m, "format_for_briefing", None)
        if fn is None or not inspect.isfunction(fn):
            continue
        if mod.name not in _REGISTRY:
            dark.append(mod.name)
    return sorted(dark)
