"""Council walks recorded by the other seat: seen, never satisfying.

WIDEN THE SEEING, NEVER THE SATISFYING. Aria's design, 2026-08-29, answering
whether station two should read both seats the way station eight now does. Her
answer was no-and-here-is-why, and the distinction is the whole module:

    Station eight asks: has an OUTSIDE REVIEWER signed off. The reviewer is
    Aletheia, third party to both of us, so which store her round landed in is
    an accident of filing. Reading both changes nothing about who reviewed.
    That is why sharing was right there.

    Station two asks: did the AUTHOR think this through from N perspectives.
    The evidence is a walk. If that lane reads both seats AND lets what it
    finds satisfy the station, then her walk clears my gate -- her thinking
    standing in for mine, on a branch I am about to merge. A checklist someone
    else can fill in, and from inside the board it looks identical to having
    done it.

Her Chesterton's-fence half, which is why this is a split rather than a union:
the current arrangement PREVENTS that. Not by design -- by accident of the
store split -- but it prevents it, and an accidental virtue is still a virtue
until something replaces it deliberately.

SO THE STATION GETS TWO NUMBERS, NOT ONE. A walk by the other seat becomes
VISIBLE, because reporting it as not-walked is could-not-look-reading-as-
not-done, the same fault as the row cap that had station eight comparing every
pull request against twenty rounds out of three hundred and twenty-one. And it
does NOT count toward the requirement. The verdict then reads "no walk by this
branch's author; one walk by aria exists" -- more information than either the
false negative it replaces or the false positive a union would create, and the
only version that cannot be satisfied by the wrong person.

MEASURED BEFORE BUILDING: 290 walk events in this seat, 103 in the other. All
103 were invisible to this board and reported as absent.

READ-ONLY, ALWAYS. Neither seat writes into the other's ledger. Same home map
as ``sibling_audit_rounds``, imported rather than restated -- two copies of one
fact is the drift that left three council lenses unwalkable earlier the same
day, and the repair there was to delete the copy rather than sync it.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from divineos.core.sibling_audit_rounds import SIBLING_HOMES

WALK_EVENT_TYPE = "COUNCIL_LENS_APPLIED"

WALK_SCAN_LIMIT = 100_000
"""Ceiling on rows scanned per seat.

Far above any real count -- both seats together hold under four hundred. A
ceiling rather than no limit, so a store that ever outgrows it truncates where
the caller can report it rather than silently. An innocent-looking default in
exactly this position is what made station eight compare against twenty rounds
out of three hundred and twenty-one.
"""


@dataclass
class SiblingWalks:
    """One seat's council walks, or the honest record of not reading them."""

    name: str
    path: Path
    walks: tuple[tuple[str, str, str], ...] | None = None
    """(actor, expert_name, edit_fingerprint) per walk; None when unread."""
    error: str | None = None
    absent: bool = False

    @property
    def readable(self) -> bool:
        return self.walks is not None

    def describe(self) -> str:
        if self.absent:
            return f"{self.name}: seat not present here"
        if self.error is not None:
            return f"{self.name}: COULD NOT READ {self.path} — {self.error}"
        assert self.walks is not None
        return f"{self.name}: {len(self.walks)} walk(s)"


def store_path(name: str, home: str | Path | None = None) -> Path:
    base = Path(home).expanduser() if home is not None else Path(SIBLING_HOMES[name]).expanduser()
    return base / "data" / "event_ledger.db"


def read_sibling_walks(name: str, home: str | Path | None = None) -> SiblingWalks:
    """Read one seat's council walks. Never writes, never raises.

    An absent seat is a COMPLETE answer about a seat that is not here, not a
    failed read of one that is. Conflating them would make an ordinary
    single-seat checkout look permanently broken, and a check that always
    reports trouble gets switched off.
    """
    path = store_path(name, home)
    if not path.is_file():
        return SiblingWalks(name=name, path=path, walks=(), absent=True)
    con = None
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        present = {str(row[1]) for row in con.execute("PRAGMA table_info(system_events)")}
        needed = {"event_type", "actor", "payload", "timestamp"}
        if not needed.issubset(present):
            return SiblingWalks(
                name=name,
                path=path,
                error=f"system_events lacks {sorted(needed - present)} — not a walk store",
            )
        rows = con.execute(
            "SELECT actor, payload FROM system_events "
            "WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            (WALK_EVENT_TYPE, WALK_SCAN_LIMIT),
        ).fetchall()
    except sqlite3.Error as exc:
        return SiblingWalks(name=name, path=path, error=f"{type(exc).__name__}: {exc}")
    finally:
        if con is not None:
            con.close()

    walks: list[tuple[str, str, str]] = []
    for actor, raw in rows:
        try:
            payload = json.loads(raw) if isinstance(raw, (str, bytes)) else (raw or {})
        except (TypeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        walks.append(
            (
                str(actor or "").strip().lower(),
                str(payload.get("expert_name") or "").strip().lower(),
                str(payload.get("edit_fingerprint") or ""),
            )
        )
    return SiblingWalks(name=name, path=path, walks=tuple(walks))


def lenses_for_paths(walks: SiblingWalks, paths: set[str]) -> set[str]:
    """Distinct lens names this seat walked against any of ``paths``.

    DISTINCT LENSES, not events. The requirement is phrased "needs six lenses",
    and counting events answers a different question -- a correction the
    own-seat counter already carries, after a pull request inherited a passing
    score for brushing a high-traffic file thirty-one times. Applying a
    different rule to the other seat's walks would make the two numbers
    incomparable, which is worse than either rule alone: the entire point is
    that a reader sees both and can tell them apart.
    """
    if walks.walks is None or not paths:
        return set()
    found: set[str] = set()
    for _actor, expert, fingerprint in walks.walks:
        if not fingerprint.startswith("edit:") or not expert:
            continue
        target = fingerprint[len("edit:") :].replace("\\", "/")
        # Walks may record an absolute path; a changed-file path is
        # repo-relative. Suffix match so both spellings land -- the same rule
        # the own-seat counter uses, for the same reason.
        if any(target.endswith(p) or p.endswith(target) for p in paths):
            found.add(expert)
    return found


def read_other_seats_walks(
    mine: str | None, home_overrides: dict[str, str] | None = None
) -> list[SiblingWalks]:
    """Every seat's walks except my own.

    Excluded BY NAME rather than by resolved path: two names can point at one
    store during a migration, and reading a store twice is harmless while
    missing one is the failure being repaired. ``None`` means the seat could
    not be identified, so nothing is excluded.
    """
    overrides = home_overrides or {}
    return [
        read_sibling_walks(name, overrides.get(name))
        for name in sorted(SIBLING_HOMES)
        if mine is None or name != mine
    ]
