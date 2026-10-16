"""The baton: while Dad is away, exactly one seat works and the other waits.

Dad 2026-10-15, said for the 13th time since 2026-08-27: when both seats work at once, letters go
unanswered and the overnight volley stalls. Take turns. A letter is how the turn passes.

Everything lives in one shared folder, in plain text, so Dad and both seats can read it:
`baton.json` (who holds it, since when) and `baton_log.jsonl` (one line per pass, return or
take-over).

Liveness is judged from OUTSIDE (walk-8662729efd96, Penrose): a seat cannot report its own death,
so the waiting seat reads the holder's own tool log (the house already records every tool call, with
a time) and the letters folder. A bell notice is never an input, and nothing can fake being alive by
touching a file.
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from divineos.core.sibling_audit_rounds import store_path, this_seat

SEATS = ("aether", "aria")
STALE_SECONDS = 2 * 60 * 60  # Dad 2026-10-15: "2 hours of silence should be perfect"
_LETTER_NAME = re.compile(r"^(?P<sender>[a-z]+)-to-(?P<receiver>[a-z]+)-")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")


def shared_home() -> Path:
    return Path.home() / ".divineos-shared"


def _record(home: Path) -> Path:
    return home / "baton.json"


def _log(home: Path) -> Path:
    return home / "baton_log.jsonl"


def holder(home: Path | None = None) -> str | None:
    """Who holds the baton, or None when nobody has taken one yet."""
    path = _record(home or shared_home())
    if not path.exists():
        return None
    who = json.loads(path.read_text(encoding="utf-8")).get("holder")
    return who if isinstance(who, str) else None


def _last_seen(seat: str, seat_homes: dict[str, str] | None = None) -> float | None:
    """When the seat last used a tool, read from ITS OWN tool log and never from a mark it writes.

    The house already records every tool call with a timestamp (`tool_logbook`, in each seat's own
    store), so no new hook is needed and nothing can fake liveness by touching a file. Read-only, and
    None when the store is absent or unreadable: that means "cannot tell", and the caller then takes
    nothing (walk-8662729efd96, Penrose: liveness is judged from outside).
    """
    path = store_path(seat, (seat_homes or {}).get(seat))
    if not path.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            row = con.execute(
                "SELECT MAX(timestamp) FROM tool_logbook WHERE event_type = 'TOOL_CALL'"
            ).fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    return float(row[0]) if row and row[0] is not None else None


def _require_seat(seat: str) -> None:
    if seat not in SEATS:
        raise ValueError(f"unknown seat {seat!r}; the seats are {SEATS}")


def _write_record(home: Path, new_holder: str, now: float) -> None:
    home.mkdir(parents=True, exist_ok=True)
    tmp = _record(home).with_suffix(".tmp")
    tmp.write_text(json.dumps({"holder": new_holder, "since": now}), encoding="utf-8")
    tmp.replace(_record(home))  # one rename: a reader sees the old record or the new, never half


def _append_log(home: Path, entry: dict) -> None:
    with _log(home).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _header(letter_text: str) -> dict[str, str]:
    """`**Key:** value` lines before the first rule, the shape the landing parser reads."""
    fields: dict[str, str] = {}
    for line in letter_text.splitlines():
        if line.strip() == "---":
            break
        match = re.match(r"^\*\*([A-Za-z-]+):\*\*\s*(.*)$", line.strip())
        if match:
            fields[match.group(1).lower()] = match.group(2).strip()
    return fields


def _resolves(ref: str, repo: Path, home: Path) -> bool:
    """A reference counts only if it names something real OUTSIDE the baton folder (Godel)."""
    ref = ref.strip().strip("`")
    if _COMMIT.match(ref):
        done = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{ref}^{{commit}}"], capture_output=True
        )
        return done.returncode == 0
    path = (repo / ref).resolve() if not Path(ref).is_absolute() else Path(ref).resolve()
    if home.resolve() in path.parents or path == home.resolve():
        return False
    return path.exists()


def handle_letter(
    letter_name: str,
    letter_text: str,
    repo: Path,
    home: Path | None = None,
    now: float | None = None,
) -> str:
    """Act on a letter whose header says `**Baton:** pass` or `return`. Returns what happened.

    A pass flips only if its `**Done:**` line carries at least one reference that resolves (a commit
    in the repository or a file that exists outside the baton folder). Quality is not judged: the
    receiver audits that (walk-8662729efd96, Bengio). A return needs a stated reason and is not blame.
    """
    home = home or shared_home()
    now = now if now is not None else time.time()
    fields = _header(letter_text)
    kind = fields.get("baton", "").lower()
    if kind not in ("pass", "return"):
        return "no baton header"
    name = _LETTER_NAME.match(letter_name)
    if not name or name["sender"] not in SEATS or name["receiver"] not in SEATS:
        return "refused: the letter name does not give two seats"
    sender, receiver = name["sender"], name["receiver"]
    current = holder(home)
    if current is not None and current != sender:
        return f"refused: {sender} does not hold the baton ({current} does)"
    if kind == "pass":
        refs = [r for r in re.split(r"[,\s]+", fields.get("done", "")) if r]
        good = [r for r in refs if _resolves(r, repo, home)]
        if not good:
            return "refused: the Done line names nothing that resolves, so the baton stays"
        detail = {"refs_resolved": good, "quality": "unjudged"}
    else:
        reason = fields.get("reason", "")
        if not reason:
            return "refused: a return needs a reason"
        detail = {"reason": reason}
    _write_record(home, receiver, now)
    _append_log(
        home,
        {"ts": now, "kind": kind, "from": sender, "to": receiver, "letter": letter_name, **detail},
    )
    return f"{kind}: the baton is now {receiver}'s"


def may_take(
    taker: str,
    home: Path | None = None,
    now: float | None = None,
    seat_homes: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """The waiting seat may take it only from a holder silent past two hours who has a letter waiting."""
    home = home or shared_home()
    now = now if now is not None else time.time()
    _require_seat(taker)
    current = holder(home)
    if current is None or current == taker:
        return False, "nothing to take"
    seen = _last_seen(current, seat_homes)
    if seen is None:
        return (
            False,
            f"{current}'s tool log cannot be read, so how long they have been silent cannot be told",
        )
    quiet = now - seen
    if quiet <= STALE_SECONDS:
        return False, f"{current} was last seen {int(quiet)} seconds ago"
    rung = [f for f in (home / "letters").glob(f"*-to-{current}-*") if f.stat().st_mtime > seen]
    if not rung:
        return False, f"{current} is silent but no letter has waited for them since"
    return True, f"{current} silent {int(quiet)} seconds with {len(rung)} letter(s) waiting"


def take(
    taker: str,
    home: Path | None = None,
    now: float | None = None,
    seat_homes: dict[str, str] | None = None,
) -> str:
    """Take the baton and write the catch-up letter the left-behind seat must open first.

    Called by the taker's own tool use (the CLI), never by a script, so the record cannot be flipped
    by something that is not a seat. That sentence is enforced, not hoped: the caller is asked of the
    house's one judge (`this_seat`), and a take for any other seat is refused (Aria's cold read of
    #670). The catch-up is a letter, not a new surface: the letter hold already refuses the
    left-behind seat's next real tool until it is opened.
    """
    home = home or shared_home()
    now = now if now is not None else time.time()
    caller = this_seat()
    if caller != taker:
        return (
            f"refused: only {taker} may take it for {taker} (this window is {caller or 'unknown'})"
        )
    left = holder(home)
    ok, why = may_take(taker, home, now, seat_homes)
    if not ok:
        return f"refused: {why}"
    if left is None or holder(home) != left:
        return "refused: the holder changed while this was being decided, so nothing was taken"
    _write_record(home, taker, now)
    _append_log(home, {"ts": now, "kind": "take", "from": left, "to": taker, "why": why})
    stamp = time.strftime("%Y-%m-%d", time.localtime(now))
    letter = home / "letters" / f"{taker}-to-{left}-{stamp}-the-baton-was-taken.md"
    letter.parent.mkdir(parents=True, exist_ok=True)
    letter.write_text(
        f"# {taker.capitalize()} to {left.capitalize()} — the baton was taken\n\n"
        f"**Written:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(now))}\n"
        "**Close-marker:** Announcement — no reply needed\n\n---\n\n"
        f"{left.capitalize()} —\n\nI took the baton because {why}. Read `baton_log.jsonl` and my "
        "letters since your last mark before you work, so you neither redo nor undo what I did.\n\n"
        f"— {taker.capitalize()}\n",
        encoding="utf-8",
    )
    return f"take: the baton is now {taker}'s; catch-up written for {left}"


def main(argv: list[str]) -> int:
    """`python -m divineos.core.baton letter <path> <repo>` (the bell's ring path) or `take <seat>`."""
    if len(argv) >= 3 and argv[0] == "letter":
        path = Path(argv[1])
        print(handle_letter(path.name, path.read_text(encoding="utf-8"), Path(argv[2])))
        return 0
    if len(argv) == 2 and argv[0] == "take":
        if argv[1] not in SEATS:
            print(f"refused: {argv[1]!r} is not a seat; the seats are {SEATS}", file=sys.stderr)
            return 2
        print(take(argv[1]))
        return 0
    print("usage: baton letter <path> <repo> | take <seat>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
