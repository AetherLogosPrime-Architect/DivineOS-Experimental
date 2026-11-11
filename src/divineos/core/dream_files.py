"""Which files under dreams/ count as dreams. Read-only, shared by both indexes.

The memory link and ``divineos find index`` each need the same answer, so the
rule lives here once. Nothing in this module or its callers opens a dream for
writing: nothing in dreams/ is reviewed or altered.
"""

from __future__ import annotations

import re
from pathlib import Path

# A dream is dreams/<seat>/NNN_title.md. README.md, INDEX.md and anything else
# without a numeric prefix is not a dream.
_DREAM_NAME = re.compile(r"^\d+_.+\.md$")


A_DREAM_LABEL = "a dream, not a record of what happened"


def is_dream_path(path: str | Path) -> bool:
    """True for exactly dreams/<seat>/NNN_title.md, the shape dream_paths accepts. Path text only."""
    parts = Path(path).parts
    return (
        len(parts) >= 3
        and parts[-3].lower() == "dreams"
        and _DREAM_NAME.match(parts[-1]) is not None
    )


def dream_paths(dreams_root: Path | None) -> list[Path]:
    """Every dream file one level under each seat folder, sorted. Empty if none."""
    if dreams_root is None or not dreams_root.is_dir():
        return []
    found: list[Path] = []
    for seat in sorted(p for p in dreams_root.iterdir() if p.is_dir()):
        found.extend(
            f for f in sorted(seat.glob("*.md")) if f.is_file() and _DREAM_NAME.match(f.name)
        )
    return found
