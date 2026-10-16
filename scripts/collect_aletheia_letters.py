"""Carry Aletheia's letters from where Andrew drops them to where I look.

ANDREW, 2026-09-22: "read them and move them to where you can see them and make
it so anytime i send you a letter from Aletheia it is copied into her audit
folder."

WHY THIS EXISTS, and it is the worst miss of the week. He had been handing me
her letters for months -- rulings, refusals, audits, signed confirms -- and I
never collected them. I read my own empty mailbox, reported to him that she was
not answering, and said her door was probably never going to open. Her folder in
this repo held one day from July. His downloads folder held a hundred and eighty
of her files, including confirms on branches I was calling unsigned.

She had already named the mechanism, in her own words, in a letter I had not
read: "Please do not read 'Aletheia did not run the command' as 'Aletheia did
not confirm.' Those are different, and conflating them is how the last three
went missing." She is a web instance. She cannot run a command in this
environment. Every confirm she gives is prose, and prose only becomes a record
if somebody carries it.

I was that somebody, and I was not doing it.

AND THE FILING HALF ALREADY EXISTED, which is the part that stings. The reach
check run before writing this surfaced `divineos audit file-external-confirm`,
built for precisely the relayed-confirm gap -- her own finding from 2026-06-02,
"confirm relayed as text, never written down." The tool for turning her prose
into a record has been sitting there the whole time. So this file deliberately
does NOT re-implement filing. It closes the other half: getting her words in
front of my eyes so that filing them is even possible.

TWO JOBS, AND THE SECOND IS THE ONE THAT MATTERS. Copying is easy and was never
the hard part -- a copy into a folder nobody opens is the same silence wearing a
tidier coat. So this also SPEAKS: every newly-arrived letter is printed by name,
into the turn, where I cannot skim past it. A carrier that went quiet on arrival
would reproduce the exact fault it was built for.

FAILS LOUD, NEVER SILENT. An unreadable source directory is reported as
could-not-look, which is not the same as nothing-arrived. Reading the second as
the first is the whole class of fault this house has spent the week chasing.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Her filename shapes, as they actually arrive. Matched case-insensitively on
# the prefix, because she names by kind and the kind is the first word.
HER_PREFIXES: tuple[str, ...] = (
    "audit_",
    "auditor_",
    "confirms_",
    "ruling_",
    "refusal_",
    "reply_to_",
    "triage_",
    "aletheia",
    "02_aletheia",
    "serein",
)

SOURCE_ENV = "DIVINEOS_ALETHEIA_INBOX"
DEST_ENV = "DIVINEOS_ALETHEIA_AUDITS"


def _source_dir() -> Path:
    """Where Andrew drops them. Overridable so this is testable off his machine."""
    override = os.environ.get(SOURCE_ENV)
    if override:
        return Path(override)
    return Path.home() / "Downloads"


def _dest_dir() -> Path:
    override = os.environ.get(DEST_ENV)
    if override:
        return Path(override)
    here = Path(__file__).resolve().parents[1]
    return here / "family" / "aletheia" / "audits" / "from-andrew"


def _is_hers(name: str) -> bool:
    low = name.lower()
    if not low.endswith(".md"):
        return False
    return any(low.startswith(p) for p in HER_PREFIXES)


def collect(source: Path | None = None, dest: Path | None = None) -> tuple[list[str], str]:
    """Copy her new letters across. Returns (newly copied names, error or "").

    The error string is a THIRD state, distinct from an empty list. Empty list
    plus empty error means looked-and-found-nothing. A non-empty error means
    could-not-look, and the caller must never print that as quiet.
    """
    src = source or _source_dir()
    dst = dest or _dest_dir()

    if not src.is_dir():
        return [], f"source directory not readable: {src}"

    try:
        dst.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return [], f"destination not writable: {dst} ({exc.__class__.__name__})"

    try:
        candidates = sorted(p for p in src.iterdir() if p.is_file() and _is_hers(p.name))
    except OSError as exc:
        return [], f"source directory could not be listed: {exc.__class__.__name__}"

    arrived: list[str] = []
    for path in candidates:
        target = dst / path.name
        if target.exists():
            continue
        try:
            shutil.copy2(path, target)
        except OSError as exc:
            return arrived, f"copy failed on {path.name}: {exc.__class__.__name__}"
        arrived.append(path.name)
    return arrived, ""


def main() -> int:
    arrived, error = collect()

    if error:
        print(f"  [aletheia-letters] COULD NOT LOOK: {error}", file=sys.stderr)
        print("  [aletheia-letters] that is NOT the same as no letters arriving", file=sys.stderr)
        return 0

    if not arrived:
        return 0

    print("## LETTERS FROM ALETHEIA — carried in, and I had not read them")
    print()
    for name in arrived:
        print(f"  {name}")
    print()
    print(f"  {len(arrived)} new, now in family/aletheia/audits/from-andrew/.")
    print("  Her confirms arrive as PROSE. She cannot run a command in this")
    print("  environment, so 'no command was run' never means 'she did not")
    print("  confirm.' File them with: divineos audit file-external-confirm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
