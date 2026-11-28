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

# "writing" is the lane that reads the folders we write in (dreams, evenings, the walk). Those files
# quote Dad often, and the hold returns False at once for any source not named here, so the lane
# must be named before it exists (memory walk, hole one).
HELD_SOURCES = frozenset({"correction", "knowledge", "worklist", "letter", "writing"})

# A sidecar line shorter than this is ignored: it is a hand-edited file, and a stray
# letter would otherwise hold nearly every line in the store.
_MIN_SIDECAR_PHRASE = 8

_CURLY_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "′": "'"})

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


def _normalize(text: str) -> str:
    """Lowercase, straight apostrophes, single spaces: text pasted from chat carries curly ones."""
    return " ".join((text or "").translate(_CURLY_APOSTROPHES).lower().split())


_sidecar_cache: tuple[tuple[Path, int, int], tuple[str, ...]] | None = None


def _extra_phrases() -> tuple[str, ...]:
    """The sidecar phrases, read again only when the file, its modified time or its size changes."""
    global _sidecar_cache
    path = _sidecar()
    try:
        st = path.stat()
    except OSError:
        return ()
    stamp = (path, st.st_mtime_ns, st.st_size)
    if _sidecar_cache is not None and _sidecar_cache[0] == stamp:
        return _sidecar_cache[1]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    phrases = tuple(
        n
        for n in (_normalize(s) for s in lines if s.strip() and not s.startswith("#"))
        if len(n) >= _MIN_SIDECAR_PHRASE
    )
    _sidecar_cache = (stamp, phrases)
    return phrases


def is_held(source: str, text: str) -> bool:
    """True when this stored line is a record of his hurt and must not surface unasked."""
    if source not in HELD_SOURCES:
        return False
    normalized = _normalize(text)
    return any(_normalize(p) in normalized for p in PHRASES) or any(
        p in normalized for p in _extra_phrases()
    )
