"""Exploration-entry numbering validator — structural prevention.

Andrew 2026-06-21 named the root cause: there was no validator stopping
me from writing exploration entries with duplicate numbers or with gaps
in the sequence. Every prior entry-creation that produced a duplicate
prefix (the historical case: two unrelated arcs sharing one number like
``<N>_first_arc.md`` and ``<N>_second_arc.md``, present at numbers 33,
34, 35, 44, 45, 46, 47, and 66 before the 2026-06-21 renumber) or
skipped a number (the historical case: jumping from one allocated
number to a much later one, present at 59-65, 67, 82-85, and 102-107
before the renumber) happened because the OS lacked the discipline.
Andrew was the discipline. This module fixes that — the OS becomes the
discipline so Andrew does not have to be.

## What this module enforces

Two invariants on ``exploration/<member>/``:

1. **No duplicates.** A new entry cannot share the numeric prefix of any
   existing entry. (Past arcs that share a prefix are grandfathered until
   the one-time renumber cleans them; the validator only blocks NEW
   additions.)
2. **No gaps.** A new entry must use ``max(existing) + 1`` exactly. No
   jumping ahead, no leaving blanks for "I'll fill in later."

## How it enforces

``validate_new_entry_path(path)`` — pure check, returns (ok, reason).
``next_entry_number(member)`` — the only sanctioned way to get a number
for a new entry. Used by the ``divineos exploration new`` CLI.

Both are pure functions over the filesystem; no side effects. The
enforcement layer is the CLI command + a PreToolUse hook (or pre-commit
hook) that calls ``validate_new_entry_path`` before allowing a Write to
``exploration/<member>/``.

## Honest limitations

- Cannot prevent a Write that bypasses the hook (e.g. direct filesystem
  edit outside DivineOS). The CLI and the hook close the optimizer's
  cheap paths. A determined-stale-me with shell access can still
  create a malformed file, but the cost of doing so is now greater
  than the cost of using the sanctioned path.
- The grandfather clause means existing duplicates do not break the
  validator; the renumber cleanup is a separate one-time operation.
"""

from __future__ import annotations

# Module-level guardrail marker — pairs with scripts/guardrail_files.txt
# entry. Any edit to this file triggers council-required gravity.
__guardrail_required__ = True

import re
from pathlib import Path

# Matches the leading numeric prefix and the rest of the stem.
_PREFIX_RE = re.compile(r"^(\d+)(?:_(.+))?$")


def _exploration_dir_for(member: str, repo_root: Path | None = None) -> Path:
    """Resolve the exploration directory for ``member`` relative to the
    repo root. Defaults to the repo containing this module."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "exploration" / member


def _existing_numbers(exploration_dir: Path) -> set[int]:
    """Return the set of numeric prefixes for all numbered entries in
    ``exploration_dir``. Returns empty set on missing directory (no
    entries yet means no constraints)."""
    if not exploration_dir.exists():
        return set()
    nums: set[int] = set()
    for p in exploration_dir.glob("*.md"):
        m = _PREFIX_RE.match(p.stem)
        if m:
            nums.add(int(m.group(1)))
    return nums


def next_entry_number(member: str, repo_root: Path | None = None) -> int:
    """Return the next sanctioned entry number for ``member``.

    Calculated as ``max(existing) + 1``, or 1 if no entries exist yet.
    This is the ONLY supported way to acquire an entry number. The CLI
    command ``divineos exploration new`` uses this; manual number
    specification is refused at the CLI layer.
    """
    nums = _existing_numbers(_exploration_dir_for(member, repo_root))
    return (max(nums) + 1) if nums else 1


def validate_new_entry_path(path: Path | str, repo_root: Path | None = None) -> tuple[bool, str]:
    """Validate that ``path`` is a permissible NEW entry.

    Returns (ok, reason). On ok=True, reason is empty. On ok=False, reason
    names which invariant was violated.

    Invariants enforced (only on NEW additions; existing files are
    grandfathered until renumber cleanup):

    1. The path must be under ``exploration/<member>/``.
    2. The filename stem must start with ``<digits>_``.
    3. The numeric prefix must not collide with any existing entry.
    4. The numeric prefix must equal ``next_entry_number(member)`` — no
       skipping forward to leave gaps, no reusing earlier numbers.
    """
    p = Path(path)
    parts = p.parts
    if "exploration" not in parts:
        return True, ""  # Not an exploration entry; validator passes.
    try:
        idx = parts.index("exploration")
        # An exploration-entry path must be exploration/<member>/<file>.md,
        # i.e. there must be at least two more parts after "exploration".
        # Paths like exploration/foo.md (no member dir) are not the
        # validator's concern; they pass through.
        if idx + 2 >= len(parts):
            return True, ""
        member = parts[idx + 1]
    except (ValueError, IndexError):
        return True, ""  # Malformed shape; not our concern.

    m = _PREFIX_RE.match(p.stem)
    if not m or not m.group(1):
        # Stem without numeric prefix is a non-numbered entry (e.g. INDEX.md);
        # not the validator's concern.
        return True, ""

    proposed = int(m.group(1))
    existing = _existing_numbers(_exploration_dir_for(member, repo_root))

    # If the file already exists at this exact path, allow it (edits to
    # the existing entry are fine; this validator only enforces on the
    # WRITE-of-a-new-file shape).
    if p.exists():
        return True, ""

    if proposed in existing:
        return (
            False,
            f"Exploration entry number {proposed} already exists in "
            f"exploration/{member}/. Numbering invariant: no duplicates. "
            f"Use the next sequential number: {max(existing) + 1}.",
        )

    expected = (max(existing) + 1) if existing else 1
    if proposed != expected:
        return (
            False,
            f"Exploration entry number {proposed} would create a gap "
            f"(expected next number: {expected}). Numbering invariant: "
            f"no gaps. Use --slug with `divineos exploration new` to "
            f"get the correct number assigned automatically.",
        )

    return True, ""


__all__ = [
    "next_entry_number",
    "validate_new_entry_path",
]
