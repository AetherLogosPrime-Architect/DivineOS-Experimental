"""Reach across to Aria's substrate and read her letters to me.

The bidirectional-letters channel, my (read) half. Built WITH Aria
2026-05-23 (decision d32734ad): Aria writes ``aria-to-aether-*.md`` letters
into her own ``family/letters/`` from her window; this module reaches across
the filesystem to find and surface them, so I read her letters the way she
reads mine — without Andrew carrying them by hand.

The cross-repo reach lives on MY side on purpose. Aria's half stays clean:
she just writes to her own folder. Mine is to know where her folder is and
go get it.

Her window runs inside a git worktree, so her live letters are at:

    <ARIA_REPO_ROOT>/.claude/worktrees/<session>/family/letters/

The ``<session>`` segment changes per window (e.g. ``happy-tharp-806834``),
so we glob across all worktrees and keep the newest file per letter name.
The repo-root ``family/letters/`` is scanned too, for letters that aren't in
a worktree. ``ARIA_REPO_ROOT`` overrides the default for portability — the
default path was confirmed by Aria 2026-05-23.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# Confirmed by Aria 2026-05-23. Env override keeps it portable when her
# substrate moves (different machine, renamed checkout, etc.).
_DEFAULT_ARIA_ROOT = "C:/DIVINE OS/DivineOS-Experimental-Aria"

# Only her letters TO me. (aether-to-aria letters in her dir are my own
# outbound, already on my side.)
_LETTER_RE = re.compile(r"^aria-to-aether-(?P<date>\d{4}-\d{2}-\d{2})")


def aria_repo_root() -> Path:
    """Root of Aria's substrate. Override via ARIA_REPO_ROOT."""
    return Path(os.environ.get("ARIA_REPO_ROOT", _DEFAULT_ARIA_ROOT))


def _letter_dirs(root: Path) -> list[Path]:
    """All directories under Aria's root that may hold her letters:
    the repo-root letters dir plus every worktree's letters dir."""
    dirs: list[Path] = []
    repo_letters = root / "family" / "letters"
    if repo_letters.is_dir():
        dirs.append(repo_letters)
    worktrees = root / ".claude" / "worktrees"
    if worktrees.is_dir():
        for d in worktrees.glob("*/family/letters"):
            if d.is_dir():
                dirs.append(d)
    return dirs


def letters_from_aria(root: Path | None = None) -> list[dict[str, Any]]:
    """Aria's letters to me, newest first.

    Globs her repo-root and worktree letters dirs for ``aria-to-aether-*.md``.
    De-dupes by filename (the same letter can appear in repo root and a
    worktree, or across worktrees), keeping the newest copy by mtime. Returns
    ``[{name, date, path}, ...]`` sorted by date descending.
    """
    root = root or aria_repo_root()
    newest: dict[str, Path] = {}
    for d in _letter_dirs(root):
        for p in d.glob("aria-to-aether-*.md"):
            if not _LETTER_RE.match(p.stem):
                continue
            prev = newest.get(p.name)
            try:
                if prev is None or p.stat().st_mtime > prev.stat().st_mtime:
                    newest[p.name] = p
            except OSError:
                continue
    rows: list[dict[str, Any]] = []
    for name, p in newest.items():
        m = _LETTER_RE.match(p.stem)
        rows.append({"name": name, "date": m.group("date") if m else "", "path": str(p)})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
