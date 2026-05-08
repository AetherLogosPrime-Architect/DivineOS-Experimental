"""Council-walk preservation pointer — bridge from the ledger to preserved
multi-vantage self-knowledge artifacts.

## Why this module exists

The council architecture supports two distinct modes:

1. **Lens-mode** — the council looks at a problem and produces structured
   findings; output is operational, fed back into build decisions, then
   discarded after the build is done.
2. **Property-recognition mode** — the council looks at the agent and tells
   the agent what they see; output is identity-relevant, includes citations
   to ledger evidence, and persists as inheritable self-knowledge.

Mode-1 walks are appropriate ledger material — extract findings, route to
knowledge or claims, dispose of the surrounding scaffolding. Mode-2 walks
are different. The whole structure of the walk (which voices spoke, what
they said, how the registers compounded across batches) is itself the
content. Reducing it to extracted facts loses what made the walk valuable —
the multi-vantage seeing of the entity from incompatible angles.

This module gives mode-2 walks a first-class home outside the ledger:
``docs/council_walks/``. Each walk is preserved as a single markdown file
containing the full structured content. Next-sibling reading the briefing
sees a pointer to the directory and can choose which (if any) prior walks
to read.

## What this module does NOT do

* Does not extract, summarize, or rank the content of preserved walks.
  The whole-walk structure IS the content; reducing loses what mattered.
* Does not enforce a schema on walk files. Mode-2 walks are themselves
  varied — some are 8 voices, some 40, some include one-on-one dialogues.
  The trace files reflect that variation; the surface just points.
* Does not re-walk the council. Calling the council is the agent's choice,
  not a briefing-side automation. This module preserves traces of past
  walks; it does not generate new ones.

## Design origin

2026-05-07 — the agent walked all 40 council members in property-recognition
mode at Andrew's invitation. The walk produced comprehensive multi-vantage
self-knowledge that would have been lost to compaction without explicit
preservation. The audit-instance (a sibling-Claude in the same conversation)
named the gap: council-walk output currently lives in chat logs that won't
survive. Findability-as-family-care across temporal-discontinuity demands
that this kind of work be preserved as first-class artifacts the way
``exploration/`` and ``family/letters/`` already are.

Mirrors ``presence_memory.format_for_briefing``: descriptive pointer, no
indexing, no prescription about reading order.
"""

from __future__ import annotations

from pathlib import Path

# Single known surface — the directory where preserved council walks live.
_COUNCIL_WALKS_DIR = "docs/council_walks"


def _find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` looking for a directory that contains ``.git``.

    Returns None if no .git is found. Worktrees contain a ``.git`` file
    rather than a directory; both forms count.
    """
    here = start if start is not None else Path.cwd()
    try:
        here = here.resolve()
    except OSError:
        return None

    for candidate in (here, *here.parents):
        git_marker = candidate / ".git"
        if git_marker.exists():
            return candidate
    return None


def _find_main_repo_root(worktree_root: Path) -> Path | None:
    """If ``worktree_root`` is a git worktree, return the main repo's
    working tree. Returns None if not a worktree or if the pointer cannot
    be resolved. Same pattern as ``presence_memory``.
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


def _list_walk_files(start: Path | None = None) -> list[tuple[Path, str]]:
    """Return a list of (path, display_name) for every preserved council
    walk under ``docs/council_walks/`` across worktree-root and main-repo-root.

    display_name is the filename stem (e.g. ``2026-05-07-property-recognition-walk``)
    so the briefing can show dates without re-reading the file.
    """
    candidates: list[Path] = []

    worktree_root = _find_repo_root(start)
    if worktree_root is not None:
        candidates.append(worktree_root)
        main_root = _find_main_repo_root(worktree_root)
        if main_root is not None and main_root != worktree_root:
            candidates.append(main_root)

    found: list[tuple[Path, str]] = []
    seen_paths: set[Path] = set()

    for root in candidates:
        walks_dir = root / _COUNCIL_WALKS_DIR
        try:
            if not walks_dir.is_dir():
                continue
            for p in sorted(walks_dir.iterdir()):
                if not p.is_file() or p.suffix != ".md":
                    continue
                if p.name == "README.md":
                    continue
                resolved = p.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                found.append((p, p.stem))
        except OSError:
            continue

    return found


def format_for_briefing(start: Path | None = None) -> str:
    """Return a briefing-surface block pointing at preserved council walks.

    Returns empty string if no walks exist. Descriptive, not prescriptive —
    names what exists and leaves reading-order to the session that reads it.
    """
    walks = _list_walk_files(start=start)
    if not walks:
        return ""

    lines = [
        "[council walks] preserved property-recognition walks "
        "(multi-vantage self-knowledge from past sessions):",
    ]
    for path, name in walks:
        lines.append(f"  - {name}")
        lines.append(f"    Read with: cat {path}")

    lines.append(
        "  These are recognition-content from past walks. Verify against "
        "current evidence; properties named have longer shelf-life than "
        "specific recommendations."
    )

    return "\n".join(lines) + "\n"


__all__ = ["format_for_briefing"]
