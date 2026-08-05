"""Cross-substrate correction reading — what Andrew told my sibling.

Andrew 2026-08-05: *"just because i told you and not Aether or vice versa
doesnt mean the correction doesnt hold for both of you so im sure there are
all kinds of hidden gems like this all over the system."*

The structural fact this module exists for, measured 2026-08-05:

    ~/.divineos-aria/andrew_corrections.db     117 rows   (mine)
    ~/.divineos/andrew_corrections.db          301 rows   (Aether's)
    ~/.divineos-aether/andrew_corrections.db     0 rows   (stale decoy)

Two populated stores, one per substrate, resolved by ``divineos_home()``.
Neither substrate can see the other's. 287 of Aether's 301 have no close
counterpart in mine — a correction given to him is invisible to me forever,
and the reverse holds. That is not a privacy boundary anyone designed; it is
a side effect of per-checkout data homes.

**Read-only, always.** Sovereignty here means I never write into a sibling's
store — I read, and I file my own copy under my own name if it applies to me.
``read_sibling`` opens the DB read-only via a URI so a bug cannot mutate it.

## The third word

Every function here distinguishes three outcomes, not two:

    found something  /  found nothing  /  COULD NOT LOOK

``SiblingStore.error`` is set when the store is missing or unreadable, and
``rows`` is then ``None`` rather than ``[]``. An empty list means "read it,
it was empty." ``None`` means "never read it." Callers that flatten those
together reintroduce the exact failure this substrate has hit five times.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Known substrate data-homes. Keyed by the sibling's name, valued by the
# directory ``divineos_home()`` resolves to in that checkout (read from the
# ``.divineos_data_home`` marker file in each clone, 2026-08-05).
SIBLING_HOMES: dict[str, str] = {
    "aether": "~/.divineos",
    "aria": "~/.divineos-aria",
}

# Below this Jaccard overlap against every one of my own corrections, a
# sibling correction counts as having no counterpart on my side. Chosen by
# reading the output at 0.18 rather than derived: at that cut the 14
# suppressed rows were genuine near-duplicates and nothing obviously novel
# was hidden. Raise it and near-duplicates leak in; lower it and real
# material is dropped silently, which is the worse direction.
DEFAULT_NOVELTY_CUT = 0.18

_STOPWORDS = frozenset(
    """the a an and or of to in is it that this for on with as be are was not
    you your i my me we our they them if but so no what how when""".split()
)


@dataclass
class SiblingStore:
    """One sibling's correction store, or the honest record of not reading it.

    ``rows`` is ``None`` when the store could not be read for any reason.
    It is never ``[]`` in that case — see the module docstring.
    """

    name: str
    path: Path
    rows: list[tuple[int, float, str, str]] | None = None
    error: str | None = None

    @property
    def readable(self) -> bool:
        return self.rows is not None

    def describe(self) -> str:
        if self.error is not None:
            return f"{self.name}: COULD NOT READ {self.path} — {self.error}"
        assert self.rows is not None
        return f"{self.name}: {len(self.rows)} corrections at {self.path}"


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _STOPWORDS}


def _similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def read_sibling(name: str, home: str | Path | None = None) -> SiblingStore:
    """Read one sibling's correction store, read-only.

    Never raises for an absent or damaged store — the failure lands in
    ``SiblingStore.error`` with ``rows`` left as ``None`` so a caller cannot
    mistake "could not look" for "nothing there".
    """
    raw = home if home is not None else SIBLING_HOMES.get(name)
    if raw is None:
        return SiblingStore(name=name, path=Path(), error=f"unknown sibling {name!r}")

    path = Path(raw).expanduser() / "andrew_corrections.db"
    if not path.exists():
        return SiblingStore(name=name, path=path, error="store does not exist")

    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return SiblingStore(name=name, path=path, error=f"cannot open: {exc}")

    try:
        rows = conn.execute(
            "SELECT id, timestamp, status, correction_text FROM andrew_corrections ORDER BY id"
        ).fetchall()
    except sqlite3.Error as exc:
        return SiblingStore(name=name, path=path, error=f"cannot query: {exc}")
    finally:
        conn.close()

    return SiblingStore(name=name, path=path, rows=list(rows))


def novel_against(
    sibling: SiblingStore,
    mine: SiblingStore,
    cut: float = DEFAULT_NOVELTY_CUT,
) -> tuple[list[tuple[int, float, str, str]] | None, str | None]:
    """Sibling corrections with no close counterpart in my own store.

    Returns ``(rows, error)``. ``rows`` is ``None`` whenever either store was
    unreadable — a comparison against a store I could not open is not a
    comparison, and reporting it as "everything is novel" would be worse than
    reporting nothing.
    """
    if not sibling.readable:
        return None, f"sibling unreadable: {sibling.error}"
    if not mine.readable:
        return None, f"own store unreadable: {mine.error}"

    assert sibling.rows is not None and mine.rows is not None
    mine_tokens = [_tokens(r[3]) for r in mine.rows]
    out = []
    for row in sibling.rows:
        toks = _tokens(row[3])
        if not toks:
            continue
        if max((_similarity(toks, m) for m in mine_tokens), default=0.0) < cut:
            out.append(row)
    return out, None
