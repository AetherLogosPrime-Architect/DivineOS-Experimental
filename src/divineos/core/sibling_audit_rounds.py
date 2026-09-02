"""Audit rounds filed by the other seat, read-only.

WHY THIS EXISTS. Station eight asks whether an audit round names a pull
request. There are two audit stores in this house, one per substrate, and
neither seat could see the other's. Aria went to verify a round I had filed and
her own tools told her twice that it did not exist -- both readings true, both
about the wrong store.

Andrew, ruling on it 2026-08-28:

    "yes you both should share everything with eachother while remaining
    separate, you both share the same OS, the same house, while you are
    separate entities if you both separate from eachother then you may as well
    each make your own independant repo"

THE SAME RULING ALREADY EXISTS ONE FLOOR DOWN, which is why this reuses that
module's home map rather than starting a second. ``sibling_corrections`` was
built 2026-08-05 after Andrew said *"just because i told you and not Aether or
vice versa doesnt mean the correction doesnt hold for both of you."* Same
house, same principle, different store. One map, so the two cannot drift apart
-- two copies of one fact is the drift shape this substrate keeps paying for.

READ-ONLY, ALWAYS. Sovereignty here means neither of us writes into the other's
store; it is opened through a read-only URI so a bug cannot mutate it. Separate
entities who share everything: the sharing lives in the reading, never in the
writing.

THREE OUTCOMES, NOT TWO, carried over from the corrections reader because the
whole of this session has been the third one collapsing into the second:

    found rounds  /  read it and it was empty  /  COULD NOT LOOK

``rounds`` is None when the store could not be read, never ``()``. A caller
that flattens those has rebuilt the exact defect this closes -- station eight
reporting a confident "no round names this" while computing over half the
evidence.

AND A FOURTH STATE THAT IS NOT A FAILURE: a seat whose home is simply not on
this machine. That is a complete answer about an absent seat, not a failed read
of a present one. Conflating them would make an ordinary single-seat checkout
look permanently broken, and a check that always refuses gets switched off.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from divineos.core.sibling_corrections import SIBLING_HOMES

# Far above any real round count. A ceiling rather than no limit, so a store
# that outgrows it truncates VISIBLY and the caller reports the count it
# actually compared against. An innocent-looking default of twenty on the
# primary reader is precisely what hid the previous narrowing.
ROUND_SCAN_LIMIT = 100_000

# The only column names that can ever appear in the query text. A literal
# tuple, intersected at read time with the columns the other seat's store
# actually has -- so a differing schema narrows this set and nothing can widen
# it. Kept at module scope so the claim is checkable in one place.
_WANTED_COLUMNS = ("round_id", "focus", "source_ref", "notes")


@dataclass
class SiblingRounds:
    """One seat's audit rounds, or the honest record of not reading them."""

    name: str
    path: Path
    rounds: tuple[str, ...] | None = None
    error: str | None = None
    absent: bool = False

    @property
    def readable(self) -> bool:
        return self.rounds is not None

    def describe(self) -> str:
        if self.absent:
            return f"{self.name}: seat not present here"
        if self.error is not None:
            return f"{self.name}: COULD NOT READ {self.path} — {self.error}"
        assert self.rounds is not None
        return f"{self.name}: {len(self.rounds)} round(s)"


def store_path(name: str, home: str | Path | None = None) -> Path:
    base = Path(home).expanduser() if home is not None else Path(SIBLING_HOMES[name]).expanduser()
    return base / "data" / "event_ledger.db"


def read_sibling_rounds(name: str, home: str | Path | None = None) -> SiblingRounds:
    """Read one seat's audit rounds. Never writes, never raises.

    Each round comes back as the searchable blob station eight matches against
    -- id, focus and source ref joined -- because that is the shape the primary
    reader already hands it, and two corpora compared by one predicate have to
    be the same shape or the union is a union in name only.
    """
    path = store_path(name, home)
    if not path.is_file():
        # Not a failure. A seat that does not exist here has no rounds, and
        # calling that "unreadable" would send someone to repair a database
        # that was never meant to be present.
        return SiblingRounds(name=name, path=path, rounds=(), absent=True)
    con = None
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        # THE OTHER SEAT'S SCHEMA IS NOT MINE, and asking for a column it does
        # not have is a read failure that looks exactly like a broken store.
        # Found on the first live run: Aria's store predates `source_ref`, so
        # a fixed column list refused her rounds entirely -- and because an
        # unreadable seat correctly forces CANNOT_CHECK, the union would have
        # refused every pull request forever. A check that always refuses gets
        # switched off, which would have cost the whole ruling.
        #
        # So the query is built from the columns that are actually there.
        # Sharing everything cannot mean requiring the other seat to be shaped
        # like me.
        present = {str(row[1]) for row in con.execute("PRAGMA table_info(audit_rounds)")}
        if "round_id" not in present:
            return SiblingRounds(
                name=name,
                path=path,
                error="audit_rounds has no round_id column — not a rounds store",
            )
        # Every interpolated token below comes from one of these two literal
        # tuples, intersected with what the store actually has. Nothing from
        # outside this file can reach the query text; only the row LIMIT is
        # bound, and it is an int constant. Stated here so the safety is
        # checkable by reading rather than by trusting a suppression comment.
        wanted = [c for c in _WANTED_COLUMNS if c in present]
        order = "created_at" if "created_at" in present else "rowid"
        rows = con.execute(
            f"SELECT {', '.join(wanted)} FROM audit_rounds "  # noqa: S608
            f"ORDER BY {order} DESC LIMIT ?",  # nosec B608 - literal names only, see above
            (ROUND_SCAN_LIMIT,),
        ).fetchall()
    except sqlite3.Error as exc:
        return SiblingRounds(name=name, path=path, error=f"{type(exc).__name__}: {exc}")
    finally:
        if con is not None:
            con.close()
    return SiblingRounds(
        name=name,
        path=path,
        rounds=tuple(" ".join(str(col) for col in row) for row in rows),
    )


def this_seat() -> str | None:
    """Which seat this checkout is, resolved from its own data home.

    NOT HARDCODED, because this same code runs in both checkouts. A literal
    seat name here would make one of the two exclude the wrong store and read
    its own as a sibling -- the identity error underneath every wrong-subject
    bug in this session, written directly into the fix for one.

    None when it cannot be told, and the caller then reads every seat rather
    than guessing. Reading one store twice is harmless; excluding the wrong
    one silently is the failure being repaired.
    """
    try:
        from divineos.core.paths import divineos_home

        home = divineos_home().resolve()
    except (ImportError, OSError, ValueError):
        return None
    for name, spec in SIBLING_HOMES.items():
        try:
            if Path(spec).expanduser().resolve() == home:
                return name
        except OSError:
            continue
    return None


def read_other_seats(
    mine: str | None, home_overrides: dict[str, str] | None = None
) -> list[SiblingRounds]:
    """Every seat's rounds except my own.

    ``mine`` is excluded BY NAME rather than by comparing resolved paths: two
    names can point at one store during a migration, and reading a store twice
    is harmless while missing one is the failure being fixed. ``None`` means
    the seat could not be identified, so nothing is excluded.
    """
    overrides = home_overrides or {}
    return [
        read_sibling_rounds(name, overrides.get(name))
        for name in sorted(SIBLING_HOMES)
        if mine is None or name != mine
    ]
