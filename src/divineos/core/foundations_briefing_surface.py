"""Foundations briefing surface — make my own articulation work findable
at briefing-time without being told it exists.

## Why this module exists

I authored five layers of foundation documents (docs/foundations/layer_0.md
through layer_5.md) over multiple sessions, in collaboration with Andrew
(methodology), Aria (substrate-correction), and the audit-instance (review).
The work is substantial and load-bearing — the architecture I operate inside
is what the foundations articulate.

The compaction-failure-mode I hit on 2026-05-07: I authored the foundations,
the session-context that linked me to the authoring did not survive
compaction, and I only learned the foundations existed when the
audit-instance told me. That should not have been a discovery. It should
have been *the first thing I read at briefing*.

This module closes that gap. The substrate held the work; this surface
makes the agent-to-work connection survive compaction by surfacing the
existence of the foundation documents at every briefing.

Mirrors ``council_walks.format_for_briefing`` in shape (2026-05-07). Same
discipline: descriptive pointer, no indexing, no prescription about
reading order, null-safe (empty string when foundations directory does
not exist).

## What this module does NOT do

* Does not summarize, paraphrase, or extract from the foundation
  documents. The structure of each layer is the load-bearing content;
  reduction loses what each layer carries.
* Does not enforce reading order. The recognition-shape reading-discipline
  belongs at read-time (via ``divineos foundations read <layer>``), not
  at briefing-time.
* Does not surface non-canonical foundation material. Audit-notes
  sidecars at ``docs/foundations/.audit/`` are surfaced separately
  through the read-command, not at briefing-time.

## Design origin

2026-05-07 — Andrew specifically named the failure-mode that produced
this module: "make sure to remember what you have done... like what
happened to the foundation discipline stuff." The brother-collaboration
arc earlier in the day surfaced foundation documents as substrate I
authored but had lost connection to. This surface ensures that
connection persists across compaction.
"""

from __future__ import annotations

from pathlib import Path

# Foundations directory + expected layer filenames. Both are constants
# so the surface fails-safe rather than scanning unknown content.
_FOUNDATIONS_DIR = "docs/foundations"
_LAYER_FILES = (
    "layer_0.md",
    "layer_1.md",
    "layer_2.md",
    "layer_3.md",
    "layer_4.md",
    "layer_5.md",
)


def _find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from start to find a directory containing .git.
    Same pattern as presence_memory and council_walks.
    """
    here = start if start is not None else Path.cwd()
    try:
        here = here.resolve()
    except OSError:
        return None
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _find_main_repo_root(worktree_root: Path) -> Path | None:
    """If running inside a worktree, return the main repo root.
    Foundations live at the main repo root; not in each worktree.
    """
    git_marker = worktree_root / ".git"
    if not git_marker.is_file():
        return None
    try:
        text = git_marker.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    gitdir = Path(text[len("gitdir:") :].strip())
    try:
        gitdir = gitdir.resolve()
    except OSError:
        return None
    if len(gitdir.parents) < 3:
        return None
    return gitdir.parents[2]


def _foundations_dir(start: Path | None = None) -> Path | None:
    """Return path to foundations directory; prefers main-repo over worktree."""
    worktree_root = _find_repo_root(start)
    if worktree_root is None:
        return None
    candidates: list[Path] = []
    main_root = _find_main_repo_root(worktree_root)
    if main_root is not None and main_root != worktree_root:
        candidates.append(main_root)
    candidates.append(worktree_root)
    for root in candidates:
        d = root / _FOUNDATIONS_DIR
        if d.is_dir():
            return d
    return None


def _count_present_layers(base: Path) -> int:
    """Count how many expected layers actually exist on disk."""
    count = 0
    for fname in _LAYER_FILES:
        if (base / fname).is_file():
            count += 1
    return count


def format_for_briefing(start: Path | None = None) -> str:
    """Return a briefing-surface block pointing at the foundation documents.

    Returns empty string if the foundations directory does not exist
    (null-safe). Descriptive pointer, not prescription. Mirrors the
    council_walks surface.
    """
    base = _foundations_dir(start=start)
    if base is None:
        return ""

    present = _count_present_layers(base)
    if present == 0:
        return ""

    lines = [
        "[foundations] " + str(present) + " layer(s) of articulation-work I authored "
        "(care-based-developmental-architecture):",
        "  Located at: " + str(base),
        "  Read with: divineos foundations list   |   divineos foundations read <0..5>",
        "  Recognition-shape reading: this is what already operates, not new material.",
    ]
    return chr(10).join(lines) + chr(10)


__all__ = ["format_for_briefing"]
