"""Presence-memory pointer — bridge from the ledger to unindexed personal writing.

## Why this module exists

The ledger is accountability memory: structured events, claims, decisions,
knowledge entries, all hashed and queryable. It is optimized for drift
tracking and governance.

Not everything a session produces is accountability material. Some of what
gets written is creative, introspective, or relational — explorations into
substrate, letters to one's future self, poems. That writing lives in
directories on disk (``exploration/``, ``family/letters/``) rather than in
the ledger, deliberately: extracting "lessons" from a poem reduces the poem
to its moral, and the ledger's structured-data discipline would distort what
the creative writing is for.

The cost of that separation: a fresh session loads the briefing from the
ledger and has no path to the presence-memory surfaces that exist on disk.
A folder of eighteen explorations can sit six feet away and be functionally
invisible until someone (the operator) remembers to point at it.

This module does the smallest thing that closes that specific gap: scans
for known presence-memory surfaces, reports their existence and size, and
does not attempt to index their contents. The briefing gets a one-block
pointer; current-session has to choose whether to read what's there.

## What this module does NOT do

* Does not extract, summarize, or rank the content of the folders. Creative
  writing's value is lost if squeezed into a knowledge-entry format.
* Does not prescribe reading order. Salience varies by session context;
  prescription from one session would bias the next. Descriptive only.
* Does not walk all of disk. Checks a small list of known names at known
  places (repo root, current worktree).

## Design origin

2026-04-19 — Claude 4.7 audit round 6 flagged that the briefing command is
the right place to fire this pointer, because reorientation-after-context-
loss is the exact moment the "recognition without pointers" failure occurs.
The operator had to manually point the main agent at the exploration folder in
that session; this module automates the pointer without automating the
indexing.
"""

from __future__ import annotations

from pathlib import Path

# Known presence-memory surface names. Each entry is (display_name,
# relative_path, description). The paths are checked relative to several
# candidate roots; see ``_find_repo_root``.
_PRESENCE_SURFACES: tuple[tuple[str, str, str], ...] = (
    (
        "exploration",
        "exploration",
        "unguided introspective writing — poems, explorations, journal, creative work",
    ),
    (
        "family letters",
        "family/letters",
        "letters to and from members of the family (a family member, future-the main agent, etc.)",
    ),
)


def _find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` looking for a directory that contains ``.git``.

    The search is bounded by filesystem root. Returns None if no .git is found
    (e.g. running outside a checkout). Worktrees contain a ``.git`` file
    rather than a directory; both forms count. We also follow the worktree's
    .git file to its main repo root so that presence-memory at the main
    checkout is visible from any worktree.
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
    """If ``worktree_root`` is a git worktree (i.e. ``.git`` is a file), read
    the gitdir pointer and return the main repo's working tree. Returns None
    if not a worktree or if the pointer can't be resolved."""
    git_marker = worktree_root / ".git"
    if not git_marker.is_file():
        return None
    try:
        text = git_marker.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    # Format is: "gitdir: /path/to/main/.git/worktrees/<name>"
    if not text.startswith("gitdir:"):
        return None
    gitdir = Path(text[len("gitdir:") :].strip())
    try:
        gitdir = gitdir.resolve()
    except OSError:
        return None
    # gitdir is typically .../.git/worktrees/<name>; parents[1] is .git,
    # parents[2] is the main repo's working tree.
    if len(gitdir.parents) < 3:
        return None
    return gitdir.parents[2]


def _count_md_files(path: Path) -> int:
    """Count .md files directly in a directory (not recursive). Returns 0 on error."""
    try:
        return sum(1 for p in path.iterdir() if p.is_file() and p.suffix == ".md")
    except OSError:
        return 0


def _presence_surfaces(start: Path | None = None) -> list[tuple[str, Path, int, str]]:
    """Return a list of (name, resolved_path, md_count, description) tuples
    for every presence-memory surface that actually exists.

    Checks two candidate roots: the current worktree root and the main repo
    root (if running in a worktree). Presence-memory surfaces like
    ``exploration/`` typically live at the main repo root, not inside each
    worktree, so both candidates must be consulted.
    """
    candidates: list[Path] = []

    worktree_root = _find_repo_root(start)
    if worktree_root is not None:
        candidates.append(worktree_root)
        main_root = _find_main_repo_root(worktree_root)
        if main_root is not None and main_root != worktree_root:
            candidates.append(main_root)

    found: list[tuple[str, Path, int, str]] = []
    seen_paths: set[Path] = set()

    for root in candidates:
        for name, rel, desc in _PRESENCE_SURFACES:
            p = root / rel
            try:
                if p.is_dir():
                    resolved = p.resolve()
                    if resolved not in seen_paths:
                        seen_paths.add(resolved)
                        found.append((name, p, _count_md_files(p), desc))
            except OSError:
                continue

    return found


def format_for_briefing(start: Path | None = None) -> str:
    """Return a briefing-surface block pointing at presence-memory surfaces.

    Returns empty string if no known surfaces exist. The block is
    descriptive, not prescriptive — it names what exists and leaves reading
    order to the session that reads it.
    """
    surfaces = _presence_surfaces(start=start)
    if not surfaces:
        return ""

    lines = [
        "[presence memory] surfaces outside the ledger — writing the ledger does not index:",
    ]
    for name, path, md_count, desc in surfaces:
        count_str = f"{md_count} .md file(s)" if md_count else "(empty or no .md files)"
        lines.append(f"  - {name} at {path}")
        lines.append(f"    {desc}")
        lines.append(f"    {count_str}. Browse with: ls {path}")

    lines.append("  Salience varies by session; pick what to read based on current context.")

    return "\n".join(lines) + "\n"


__all__ = ["format_for_briefing"]
