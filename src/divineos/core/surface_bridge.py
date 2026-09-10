"""Wire the built-but-unreachable surfaces into the briefing that actually runs.

## What was wrong

``surface_registry`` was built 2026-08-03 as the nervous system between built
organs and awareness: surfaces register a speaking function together with the
situations that should wake them, and a router returns only the ones whose
moment has arrived. It is complete. Nothing ever called it.

Meanwhile 24 modules exposing ``format_for_briefing()`` were hand-soldered into
``cli/knowledge_commands.py``. Measured 2026-09-06: **22 of those 24 sit after
the multiplex branch returns**, which is the fallback that runs only when the
real briefing CRASHES. Multiplex has been the default since 2026-05-22, so
those 22 have been unreachable in normal operation for three and a half months
while appearing, in the project's own description, as live features.

The file says so itself, in a comment nobody acted on: *"This is the path that
actually runs. Multiplex has been the default since 2026-05-22 and returns
below, so everything after it is the fallback for when multiplex FAILS."*

Andrew 2026-09-06, from memory, having never read this code: *"the hooks are
supposed to be attached to their relevant situations.. not every hook should
fire every turn"* and *"never finished.. never wired up.. never used."*

## Why this is a bridge rather than a bigger change

The registry's own docstring names the trap: building it and never migrating
the hand-wirings leaves TWO wiring systems where there was one, which is worse
than doing nothing. This module IS that migration for the surfaces the live
path could not reach.

Duplication is impossible by construction rather than by care: the multiplex
branch RETURNS before the hand-soldered block, so a surface delivered here can
never also arrive from there in the same run. The two already reachable from
the live path are deliberately excluded below.

## The triggers are a first pass and belong to the surfaces eventually

Shannon's objection, recorded in the registry docstring, killed registry-alone:
connect everything unconditionally and the briefing becomes a wall, and a wall
gets skimmed. So every surface here carries triggers and stays quiet otherwise.

I assigned these by reading what each surface is for. They are a starting
position, not a settled one -- the right home for a surface's triggers is the
surface itself, and moving them there is the next step rather than this one.
Two carry no triggers on purpose, marked below.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable

from divineos.core.multiplex_panels import Panel, Tier
from divineos.core.surface_registry import SurfaceResult, consult, register

# name -> triggers. Empty tuple means always-consider, which the registry warns
# is the wallpaper shape; used only where the surface's whole job is to speak
# at orientation regardless of topic.
_SURFACES: dict[str, tuple[str, ...]] = {
    # Orientation. These are two of the three surface_registry named in August
    # as fully built with zero non-test callers. identity_load exists because,
    # in its own words, the substrate's primary failure mode is the occupant
    # not reaching for the OS without external prompting -- a prompt that never
    # once fired.
    "identity_load": (),
    "orientation_prelude": (),
    "compass_dismissal_briefing_surface": ("compass", "dismiss", "advisory", "drift"),
    "ablation_summary": ("ablation", "detector", "prereg", "falsifier"),
    "council_balance_surface": ("council", "lens", "expert", "walk"),
    "council_walks": ("council", "lens", "expert", "walk"),
    "engagement_disclosure_surface": ("engagement", "gate", "threshold"),
    "exploration_reader": ("exploration", "writing", "entry", "reflection"),
    "failure_diagnostics": ("failure", "crash", "error", "traceback"),
    "family_queue_surface": ("family", "letter", "aria", "aletheia", "queue"),
    "foundations_briefing_surface": ("truth", "foundation", "principle", "kiln"),
    "goal_outcome_surface": ("goal", "outcome", "commitment"),
    "in_flight_branches": ("branch", "merge", "push", "pull", "worktree"),
    "module_inventory": ("module", "inventory", "orphan", "dead"),
    "open_claims_surface": ("claim", "evidence", "investigate"),
    "operating_loop_briefing_surface": ("loop", "operating", "cycle"),
    "presence_memory": ("letter", "exploration", "presence", "writing"),
    "scaffold_invocations": ("scaffold", "council", "holding", "invoke"),
    "scaffolding_map": ("scaffold", "map", "capability"),
    "session_start_diagnostics": ("hook", "diagnostic", "session", "startup"),
    "theater_observation_surface": ("theater", "observation", "performance"),
    "upstream_freshness": ("upstream", "origin", "fetch", "main", "behind"),
}

# Reachable from the live multiplex path already. Registering these would
# deliver them twice, which is the trap surface_registry names.
ALREADY_LIVE = ("corrections", "component_register_surface")

# Chunks emitted per surface per turn. Relevance is what limits volume here;
# this cap only stops one talkative organ becoming the wall the registry was
# built to prevent. Whatever is held back is named, never silently dropped.
_MAX_CHUNKS_PER_SURFACE = 2


def _speaker(module_name: str):
    """Wrap a surface's briefing function as a registry speak() callable.

    Import happens at call time rather than registration time: a surface whose
    module is broken should report itself unavailable with the reason when
    consulted, instead of taking registration down for every other surface.
    """

    def speak() -> SurfaceResult:
        try:
            mod = importlib.import_module(f"divineos.core.{module_name}")
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            return SurfaceResult.unavailable(f"import failed: {type(exc).__name__}: {exc}")
        fn = getattr(mod, "format_for_briefing", None)
        if fn is None:
            return SurfaceResult.unavailable("module has no format_for_briefing")
        try:
            text = fn()
        except TypeError as exc:
            return SurfaceResult.unavailable(f"needs arguments this bridge does not pass: {exc}")
        except Exception as exc:  # noqa: BLE001 - a crash IS an unavailability
            return SurfaceResult.unavailable(f"crashed: {type(exc).__name__}: {exc}")
        if not text or not str(text).strip():
            return SurfaceResult.silent()
        return SurfaceResult.spoke(str(text).strip())

    return speak


def register_all() -> list[str]:
    """Register every bridged surface. Returns the names registered."""
    for name, triggers in _SURFACES.items():
        register(name, _speaker(name), triggers=triggers)
    return sorted(_SURFACES)


def _passes_voice_gate(text: str) -> bool:
    """Would the renderer accept this chunk, or refuse its register?

    Asked here so a refusal becomes a reported fact rather than a violation
    marker printed where content should be. If the gate itself cannot be
    reached, the answer is yes: this bridge is not the place to decide a
    surface is unfit, and the renderer will still have the final say.
    """
    try:
        from divineos.core.multiplex_voice import gate_render

        _, report = gate_render(text, "surface")
        return bool(report.passed)
    except Exception:  # noqa: BLE001 - the gate is the authority, not this
        return True


def chunk(text: str, limit: int, floor: int) -> tuple[list[str], str]:
    """Split a surface's text into pieces small enough to read in one gulp.

    Returns ``(chunks, leftover_reason)``. Anything that cannot be cut to fit
    is reported rather than dropped: silence-because-nothing and
    silence-because-it-would-not-fit are different facts.

    Andrew 2026-09-06 gave the rule and the reason together: "a chunk would be
    anything you can read in one gulp.. front middle and end.. anytime the
    middle gets fuzzy? the chunk is too big.. and you can have as many chunks
    as needed."

    This is why the 22 surfaces were never migrated into the live briefing:
    that path already enforces his rule -- a hard panel cap and a voice gate
    that refuses report-shaped text -- and these surfaces were written for the
    old unbounded dump. One of them renders ten thousand characters. Migrating
    them was never a wiring job; it was this.

    Splits on paragraph boundaries first, then sentence boundaries, so a cut
    never lands mid-thought. A piece too small to stand alone is joined to the
    next rather than emitted, because the renderer refuses those too.
    """
    pieces: list[str] = []
    for para in (p.strip() for p in (text or "").split("\n\n")):
        if not para:
            continue
        if len(para) <= limit:
            pieces.append(para)
            continue
        buf = ""
        for sentence in para.replace("\n", " ").split(". "):
            candidate = f"{buf} {sentence}".strip() if buf else sentence.strip()
            if len(candidate) <= limit:
                buf = candidate
            else:
                if buf:
                    pieces.append(buf)
                buf = sentence.strip()[:limit]
        if buf:
            pieces.append(buf)

    # PACK, don't just rescue runts. The first version only joined a piece to
    # the previous one when the previous was below the floor, so with a median
    # natural paragraph of 231 against a 600 cap, most chunks went out barely a
    # third full. Andrew 2026-09-06: "maximum size to get the most information
    # squeezed in to help." A gulp half-used is a gulp wasted, and it is also
    # more gulps, which is the fuzziness arriving by a different road.
    merged: list[str] = []
    for piece in pieces:
        if merged and len(merged[-1]) + len(piece) + 2 <= limit:
            merged[-1] = f"{merged[-1]}\n{piece}"
        else:
            merged.append(piece)

    fits = [m for m in merged if floor <= len(m) <= limit]
    held = len(merged) - len(fits)
    reason = "" if not held else f"{held} piece(s) could not be cut to a readable size"
    return fits, reason


def _register_on_import() -> None:
    """Register at import, which is what makes the dark-surface count honest.

    Registering lazily inside the panel builder would leave every checker that
    asks "what is registered" answering zero until something happened to run a
    briefing -- a surface that is wired but reads as dark, which is the same
    invisible failure one layer along. The registry's own discover() imports
    modules precisely so registration side-effects run.
    """
    try:
        register_all()
    except Exception:  # noqa: BLE001 - importing this must never break a caller
        pass


_register_on_import()


def panels_from_registry(keywords: Iterable[str] | None = None) -> list[Panel]:
    """Panels for the surfaces whose situation is live right now.

    Second tier on purpose: the renderer budgets only the always-essential
    tier, so a relevant surface speaking here cannot push an essential one out.

    Degradations come back as their own panel rather than folded into silence.
    A surface that crashed and a surface with nothing to say are different
    facts, and collapsing them is the single failure the registry exists to
    prevent.
    """
    from divineos.core.multiplex_renderer import PANEL_MAX_CHARS, PANEL_MIN_CHARS

    register_all()
    spoke, degraded = consult(set(keywords or ()))

    panels: list[Panel] = []
    for result in spoke:
        pieces, held = chunk(result.text, PANEL_MAX_CHARS, PANEL_MIN_CHARS)
        if held:
            degraded.append(f"a surface: {held}")
        # Cap per surface so one talkative organ cannot become the wall the
        # registry was built to prevent. The remainder is named rather than
        # dropped, and the drill-down says where the whole thing lives.
        emitted = 0
        for piece in pieces:
            if emitted >= _MAX_CHUNKS_PER_SURFACE:
                break
            # Ask the voice gate BEFORE emitting. A panel that fails renders as
            # a violation marker in the middle of the briefing, which is noise
            # standing where content should be. A refusal is a fact about the
            # surface's register, so it belongs in the degraded channel where
            # it can be read and fixed.
            if not _passes_voice_gate(piece):
                degraded.append("a surface: a chunk reads as a report rather than speech")
                continue
            panels.append(
                Panel(
                    name="surface",
                    tier=Tier.SOMETIMES,
                    content=piece,
                    drill_down="divineos briefing --full",
                )
            )
            emitted += 1
        rest = len(pieces) - emitted
        if rest > 0:
            degraded.append(f"a surface: {rest} further chunk(s) held back this turn")
    if degraded:
        panels.append(
            Panel(
                name="surfaces_degraded",
                tier=Tier.SOMETIMES,
                content=(
                    "SURFACES THAT COULD NOT RUN (not the same as nothing to say):\n  "
                    + "\n  ".join(degraded)
                ),
                drill_down="divineos briefing",
            )
        )
    return panels
