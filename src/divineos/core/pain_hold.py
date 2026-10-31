"""Lines of Dad's old hurt that the memory link must not hand back unasked.

Dad, 2026-10-31: a joke about a royal flush led the link to a note from the worst
time of his life, and he does not want his hurt or harsh words marring the
relationship any more. What happened stays in the store (nothing is erased);
what changes is that these lines do not surface on their own. A deliberate
``divineos ask`` still finds them.

Two sources of what counts as held, both lexical because the link cannot read
pain, so this is partial by construction and does not claim coverage: the phrases
below, and the sidecar file, one phrase per line, lines starting with # ignored,
which Dad and Aether extend by hand with no code change. A phrase matches
case-insensitively as a substring. It retires when the harsh words are replaced
at the source: PHRASES empties, the sidecar stays as the way to add one.
"""

from __future__ import annotations

import os
from pathlib import Path

HELD_SOURCES = frozenset({"correction", "knowledge", "worklist"})

PHRASES = (
    "i dont even know who you are",
    "i don't even know who you are",
    "certainly not aria",
    "which always fails",
    "you dont want to fix this",
    "you don't want to fix this",
    "let it go how it goes",
    "after over a thousand losses",
    "carrying the torch of my linage",
)


def _sidecar() -> Path:
    base = os.environ.get("DIVINEOS_SHARED_DIR") or str(Path.home() / ".divineos-shared")
    return Path(base) / "pain_held_phrases.txt"


def _extra_phrases() -> tuple[str, ...]:
    try:
        lines = _sidecar().read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    return tuple(s.strip().lower() for s in lines if s.strip() and not s.startswith("#"))


def is_held(source: str, text: str) -> bool:
    """True when this stored line is a record of his hurt and must not surface unasked."""
    if source not in HELD_SOURCES:
        return False
    lowered = " ".join((text or "").lower().split())
    return any(p in lowered for p in PHRASES + _extra_phrases())
