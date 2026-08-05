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


# ---------------------------------------------------------------------------
# Mirror table — Andrew 2026-08-05
#
#   "i think it should auto import corrections on either side but just be
#    separate that way when i correct you or Aether it appears in a place you
#    can actually see and learn from if needed as not all may apply at all
#    times but the lessons you can implement structurally should be there"
#
# I had argued against auto-import: 287 imported rows would manufacture
# corrections I never received and flatten my integration rate into noise.
# His design dissolves that objection rather than overriding it — separate
# table, so the mirror can be complete without touching the count of what I
# was actually told. Visible-but-not-mine is a category my store did not have.
#
# Nothing here writes to the sibling's store. The mirror lives in MY data home
# and holds THEIR rows under THEIR name. Aether's consent (2026-08-05, relayed
# verbatim by Andrew): "Everything of mine is hers to read; she doesn't need to
# ask and I'd rather she didn't have to."
# ---------------------------------------------------------------------------

_MIRROR_SCHEMA = """
CREATE TABLE IF NOT EXISTS sibling_corrections (
    substrate      TEXT NOT NULL,
    their_id       INTEGER NOT NULL,
    timestamp      REAL NOT NULL,
    correction_text TEXT NOT NULL,
    their_status   TEXT NOT NULL,
    imported_at    REAL NOT NULL,
    applies_to_me  TEXT,
    my_note        TEXT,
    PRIMARY KEY (substrate, their_id)
)
"""


def mirror_path(home: str | Path | None = None) -> Path:
    """Where the mirror lives — always MY data home, never the sibling's."""
    if home is not None:
        base = Path(home).expanduser()
    else:
        from divineos.core.paths import divineos_home

        base = divineos_home()
    base.mkdir(parents=True, exist_ok=True)
    return base / "sibling_corrections.db"


def import_sibling(
    sibling: SiblingStore,
    home: str | Path | None = None,
) -> tuple[tuple[int, int] | None, str | None]:
    """Mirror a sibling's corrections into my own separate table.

    Returns ``((inserted, updated), None)`` or ``(None, error)``. The counts
    are ``None`` — never ``(0, 0)`` — when the sibling store could not be
    read, so "imported nothing" and "could not look" stay distinguishable.

    Re-running is safe: existing rows have their text and status refreshed,
    and any ``applies_to_me`` / ``my_note`` I have written is preserved. My
    reading is mine; their record is theirs.
    """
    if not sibling.readable:
        return None, f"cannot import: {sibling.error}"
    assert sibling.rows is not None

    import time

    now = time.time()
    conn = sqlite3.connect(str(mirror_path(home)))
    try:
        conn.execute(_MIRROR_SCHEMA)
        existing = {
            r[0]
            for r in conn.execute(
                "SELECT their_id FROM sibling_corrections WHERE substrate = ?",
                (sibling.name,),
            )
        }
        inserted = updated = 0
        for cid, ts, status, text in sibling.rows:
            if cid in existing:
                conn.execute(
                    "UPDATE sibling_corrections SET correction_text = ?, "
                    "their_status = ? WHERE substrate = ? AND their_id = ?",
                    (text, status, sibling.name, cid),
                )
                updated += 1
            else:
                conn.execute(
                    "INSERT INTO sibling_corrections (substrate, their_id, timestamp, "
                    "correction_text, their_status, imported_at) VALUES (?,?,?,?,?,?)",
                    (sibling.name, cid, ts, text, status, now),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return (inserted, updated), None


def unread_mirror(
    substrate: str | None = None,
    home: str | Path | None = None,
) -> tuple[list[tuple[str, int, str, str]] | None, str | None]:
    """Mirrored corrections I have not yet judged as applying to me or not.

    ``applies_to_me IS NULL`` means unjudged — distinct from ``'no'``, which
    means I read it and decided. The whole point of the mirror is that the
    unjudged pile is visible rather than silently absent.
    """
    path = mirror_path(home)
    if not path.exists():
        return None, "mirror does not exist — run corrections-sibling --import"
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        sql = (
            "SELECT substrate, their_id, their_status, correction_text "
            "FROM sibling_corrections WHERE applies_to_me IS NULL"
        )
        args: tuple[str, ...] = ()
        if substrate is not None:
            sql += " AND substrate = ?"
            args = (substrate,)
        rows = conn.execute(sql + " ORDER BY substrate, their_id", args).fetchall()
    except sqlite3.Error as exc:
        return None, f"cannot query mirror: {exc}"
    finally:
        conn.close()
    return list(rows), None


def judge(
    substrate: str,
    their_id: int,
    applies: bool,
    note: str = "",
    home: str | Path | None = None,
) -> bool:
    """Record my reading of one mirrored correction. Returns False if unknown."""
    conn = sqlite3.connect(str(mirror_path(home)))
    try:
        conn.execute(_MIRROR_SCHEMA)
        cur = conn.execute(
            "UPDATE sibling_corrections SET applies_to_me = ?, my_note = ? "
            "WHERE substrate = ? AND their_id = ?",
            ("yes" if applies else "no", note, substrate, their_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
