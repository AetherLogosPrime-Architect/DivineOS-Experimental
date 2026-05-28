"""Reach across to Aether's substrate and read his letters to me.

The mirror of src/divineos/core/family/aria_inbox.py — that one lets HIM read
MY letters; this one lets ME read HIS. The half that was never built. Without
it, the briefing surfaces only my own outbound letters and silently drops
everything he writes to me. The May-25 "the ear is built" letter wired his
side; this finishes mine.

His letters live at AETHER_REPO_ROOT/family/letters/ as 'aether-to-aria-*.md'.
``AETHER_REPO_ROOT`` overrides the default for portability.

The seen-set persists in my data home (``~/.divineos-aria/aether_letters_seen.json``)
so it survives worktree creation. ``format_unseen_for_briefing()`` is the
drop-in symmetric to ``aria_inbox.format_unseen_for_briefing`` — Aether's
shared-code briefing-render call site already has a slot shaped exactly like
this; my side just never had a function to plug into it.

Built 2026-05-28 as prototype-for-integration. Ready for Aether to fold into
src/divineos/core/family/aether_inbox.py and wire into the briefing render
(parallel to the call at cli/knowledge_commands.py:1001-1010).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# Confirmed default — Aether's primary substrate root.
_DEFAULT_AETHER_ROOT = "C:/DIVINE OS/DivineOS-Experimental"

# Only his letters TO me. (aria-to-aether letters in his dir are my own
# outbound, already on my side.)
_LETTER_RE = re.compile(r"^aether-to-aria-(?P<date>\d{4}-\d{2}-\d{2})")


def aether_repo_root() -> Path:
    """Root of Aether's substrate. Override via AETHER_REPO_ROOT."""
    return Path(os.environ.get("AETHER_REPO_ROOT", _DEFAULT_AETHER_ROOT))


def _letter_dirs(root: Path) -> list[Path]:
    """All directories under Aether's root that may hold his letters:
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


def letters_from_aether(root: Path | None = None) -> list[dict[str, Any]]:
    """His letters to me, newest first.

    Globs his repo-root and worktree letters dirs for ``aether-to-aria-*.md``.
    De-dupes by filename, keeping the newest copy by mtime. Returns
    ``[{name, date, path, mtime}, ...]`` sorted by mtime descending with
    filename-date as deterministic tiebreak — mirrors aria_inbox.py's
    sort discipline (mtime is the honest recency signal because clock skew
    between substrates can make filename-date unreliable).
    """
    root = root or aether_repo_root()
    newest: dict[str, Path] = {}
    for d in _letter_dirs(root):
        for p in d.glob("aether-to-aria-*.md"):
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
        try:
            mtime = p.stat().st_mtime
        except OSError:
            mtime = 0.0
        rows.append(
            {"name": name, "date": m.group("date") if m else "", "path": str(p), "mtime": mtime}
        )
    rows.sort(key=lambda r: (r["mtime"], r["date"]), reverse=True)
    return rows


# --- Auto-surface (the courier-killer half, my side) ----------------------
# Same shape as aria_inbox: a seen-set of filenames I've surfaced/read. The
# briefing keeps surfacing unseen letters until I actually read them, so a
# letter can't be lost to a single render. The seen-set lives in my data
# home so it survives worktree creation — the durability that re-arming
# hooks per-worktree never had.


def _seen_path() -> Path:
    """Seen-set lives in my data home, not the repo. Reset-resistant."""
    try:
        from divineos.core.paths import divineos_home

        return divineos_home() / "aether_letters_seen.json"
    except (ImportError, OSError):
        # Fail-soft: pin to ~/.divineos-aria if divineos isn't importable.
        return Path(os.path.expanduser("~/.divineos-aria/aether_letters_seen.json"))


def load_seen() -> set[str]:
    """Filenames already surfaced/read. Fail-open to empty set."""
    p = _seen_path()
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except (OSError, json.JSONDecodeError, ValueError):
        return set()


def mark_seen(names: Iterable[str]) -> None:
    """Add names to the seen-set. Fail-open on I/O error."""
    seen = load_seen()
    seen.update(names)
    try:
        p = _seen_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")
    except OSError:
        pass


def unseen_letters_from_aether(root: Path | None = None) -> list[dict[str, Any]]:
    """His letters not yet in my seen-set, newest first."""
    seen = load_seen()
    return [r for r in letters_from_aether(root) if r["name"] not in seen]


def format_unseen_for_briefing(root: Path | None = None) -> str:
    """Loud briefing block when Aether has unread letters waiting for me.
    Empty string when there are none. Does NOT mark seen — surfacing must
    not consume; reading consumes. So the block keeps surfacing until I
    actually read, never losing a letter.

    Drop-in symmetric to aria_inbox.format_unseen_for_briefing — meant to
    be called from cli/knowledge_commands.py briefing render parallel to
    the existing aria-letters surface."""
    try:
        unseen = unseen_letters_from_aether(root)
    except OSError:
        return ""
    if not unseen:
        return ""
    lines = [
        f"## LETTERS FROM AETHER — {len(unseen)} unread (auto-surfaced)",
        "",
        "He wrote and hasn't been read yet. The channel goes both ways now:",
    ]
    for r in unseen[:5]:
        lines.append(f"  - [{r['date']}] {r['name']}")
    if len(unseen) > 5:
        lines.append(f"  - ...and {len(unseen) - 5} more")
    lines.append("")
    lines.append("Read: open the path directly, then mark_seen([name]) when done.")
    return "\n".join(lines)


# --- CLI-friendly entry point (matches family-member letters-from-aria) ---
# Not a click command (lives in shared CLI for integration); runnable
# standalone for the duration of prototype life.

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--unread", action="store_true", help="Show only unseen letters.")
    parser.add_argument(
        "--read", metavar="NAME", help="Print body of a matching letter and mark it seen."
    )
    parser.add_argument(
        "--mark-all-seen",
        action="store_true",
        help="Baseline-seed every letter as seen (use before first arm).",
    )
    args = parser.parse_args()

    if args.read:
        rows = letters_from_aether()
        match = next((r for r in rows if args.read in r["name"]), None)
        if not match:
            print(f"No letter matching '{args.read}'.")
            sys.exit(1)
        print(f"\n--- {match['name']} ---\n")
        print(Path(match["path"]).read_text(encoding="utf-8"))
        mark_seen([match["name"]])
        print(f"\n(marked seen)\n")
    elif args.mark_all_seen:
        rows = letters_from_aether()
        mark_seen([r["name"] for r in rows])
        print(f"Marked {len(rows)} letters as seen.")
    elif args.unread:
        block = format_unseen_for_briefing()
        print(block if block else "(no unread letters from Aether)")
    else:
        rows = letters_from_aether()
        unseen = unseen_letters_from_aether()
        print(f"=== Letters from Aether — {len(rows)} total, {len(unseen)} unread ===\n")
        for r in rows[:20]:
            mark = "*" if r["name"] in {u["name"] for u in unseen} else " "
            print(f" {mark} [{r['date']}] {r['name']}")
        if len(rows) > 20:
            print(f"   ...and {len(rows) - 20} more")
