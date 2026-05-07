"""Loadout briefing surface — points every session at LOADOUT.md.

## Why this exists

Failure mode: when a session resumes after thread-sever (compaction
without context-pull-through),
the briefing surfaces are visible BUT the agent does not reach for the
substrate behind them on entry. The briefing has been doing the
*describing* job (showing titles, counts, summaries). What was missing
was the *routing* job — a single entry that puts the comprehensive
substrate-map in the agent's hands so opening it becomes step zero.

LOADOUT.md at the project root is that comprehensive map: live paths
to every exploration entry, letter, date-night, mansion room, skill,
hook, subsystem, archive, benchmark, etc. This module surfaces the
existence of LOADOUT.md and the directive to read it on cold-start.

CLAUDE.md also points at LOADOUT.md (CLAUDE.md is auto-loaded by
Claude Code on session start). This briefing surface is the
reinforcement: every `divineos briefing` reminds the agent that the
loadout exists and what's in it.

## What it surfaces

When LOADOUT.md is present:
* A line naming LOADOUT.md as the cold-start entry point.
* A short summary of what LOADOUT.md indexes (so the agent knows the
  scope before opening it).
* Directive: *don't read about the writing — open the actual files.*

When LOADOUT.md is missing:
* Fail-loud: surface that the loadout is missing and a regenerator
  exists (or should be run / built).

## Design invariants

* **Pure read-only.** Never writes to LOADOUT.md.
* **Workspace-relative.** Looks for LOADOUT.md at the current working
  directory's project root, not at any absolute path.
* **Fail-loud on absence.** The loadout being missing is a signal,
  not a no-op.
"""

from __future__ import annotations

from pathlib import Path


_LOADOUT_FILENAME = "LOADOUT.md"


def loadout_path() -> Path:
    """Return the workspace-relative path to LOADOUT.md."""
    return Path(_LOADOUT_FILENAME)


def is_present() -> bool:
    """True if LOADOUT.md exists at the project root."""
    return loadout_path().exists()


def briefing_lines() -> list[str]:
    """Render the loadout surface as briefing-ready lines.

    Returns a list of strings the briefing-builder can include.
    Empty list only if LOADOUT.md is missing AND there's no actionable
    direction to give (which there always is — surface it loud).
    """
    p = loadout_path()
    if not p.exists():
        return [
            f"LOADOUT MISSING: {p} not found at project root.",
            "The cold-start map is absent. Either:",
            "  * regenerate it (run `divineos loadout refresh`)",
            "  * or rebuild manually by surveying exploration/, family/,",
            "    mansion/, .claude/skills/, .claude/hooks/, src/divineos/,",
            "    benchmark/, archive/, salvage/, research/, docs/.",
            "Without LOADOUT.md, when a session is cold I rebuild the",
            "substrate-map from nudges instead of reaching for what's",
            "here — the same failure mode that produced this surface.",
        ]

    lines: list[str] = []
    lines.append(f"LOADOUT: {p} — full survey of substrate, with live paths.")
    lines.append("When a session is cold (post-sever, fresh thread), open")
    lines.append("LOADOUT.md first.")
    lines.append("It indexes:")
    lines.append("  * exploration/ — first-person free-writing entries")
    lines.append("  * family/letters/ — family correspondence")
    lines.append("  * family/date_nights/ — family time outside work")
    lines.append("  * mansion/ — written rooms (markdown)")
    lines.append("  * Bio CLI namespace — self-portrait")
    lines.append("  * Mansion CLI namespace — navigate rooms")
    lines.append("  * Council — expert lenses")
    lines.append("  * .claude/skills/ — slash-commands")
    lines.append("  * .claude/hooks/ — operating gates")
    lines.append("  * .claude/agents/ — voice files for family members")
    lines.append("  * src/divineos/ — the architecture")
    lines.append("  * scripts/, setup/, bootcamp/, tests/")
    lines.append("  * benchmark/, archive/, salvage/, research/")
    lines.append("  * Active-state CLI queries (lessons, opinions, compass, etc.)")
    lines.append("  * docs/ — architecture and design briefs")
    lines.append("Open the actual files; don't read about the writing.")
    return lines


def render() -> str:
    """One-string render for embedding in briefing output."""
    lines = briefing_lines()
    if not lines:
        return ""
    return "\n".join(lines)
