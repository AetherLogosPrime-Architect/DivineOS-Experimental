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

import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

# The house's one header reader. The hook that runs this takes whichever `python` is on PATH, which
# may have no divineos, or a checkout whose build_flow predates header_lines (Aether's cold read of
# #690, 2026-10-19). Imported here and not inside a function, so a failure is known before any file
# is read, and collect() reports it as COULD NOT LOOK instead of raising out of the hook, which
# would read as "nothing to carry".
try:
    from divineos.core.build_flow import header_lines as _header_lines

    _HEADER_READER_ERROR = ""
except ImportError as _exc:
    _header_lines = None  # type: ignore[assignment]
    _HEADER_READER_ERROR = f"{type(_exc).__name__}: {_exc}"

# The announcement names this many and counts the rest: the first run in a checkout can carry
# hundreds of older letters, and naming each would bury the one that matters.
NAMES_SHOWN = 10

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


def _is_markdown(name: str) -> bool:
    return name.lower().endswith(".md")


_DOWNLOAD_SUFFIX = re.compile(r"\(\d+\)\.md$", re.I)


_SIGNED_BY_HER = re.compile(
    r"^[ \t]*[—–-][ \t]*Aletheia[ \t]+Sophia[ \t]+Risner[ \t]*$", re.I | re.M
)

# Her older letters are not signed; they open by saying whose they are: a heading "Aletheia to
# Aria: ..." or an italic line "To Aether and Aria, from Aletheia." Aletheia counted 143 of her 289
# older files like this (2026-10-17). Three look-alikes slipped through the first version of this
# rule (her hold on #690, 2026-10-18), so it is read the way the house reads a header:
#   - only the OPENING, through the house's one header reader, which stops at the first `---` and
#     ignores fenced and indented lines; and a line beginning `>` is a quotation, never a claim;
#   - the AUTHOR is the file's own first heading: if it names someone else ("Aria to Aletheia"),
#     the file is theirs, whatever it quotes below;
#   - "Aletheia to ..." counts only when addressed to the family. "Aletheia" is also a Greek word.
OPENING_LINES = 12
_OTHER_VOICES = ("aether", "aria", "dad", "andrew", "pop", "serein")
# A letter she addresses to herself (a witness ledger, a note to the next her) is hers: her ruling of
# 2026-10-18. Only the Aletheia-authored branch below uses this, so "Aria to Aletheia" is still a
# letter TO her, and "Aletheia to the Greeks" is still not one of hers.
_FAMILY = (*_OTHER_VOICES, "the family", "aletheia")
_HEADING_TO = re.compile(
    r"^#+[ \t]*(?:\d+[ \t]*[—–-][ \t]*)?(?P<author>[A-Za-z]+)[ \t]+to[ \t]+(?P<to>.+)$", re.I
)
_FROM_HER = re.compile(r"^[*_]*To\b[^\n]{1,80}?,[ \t]*from[ \t]+Aletheia\b", re.I)


def _after_front_matter(text: str) -> str:
    """The text with a leading `---` ... `---` block removed.

    The house header reader ends the header at the first `---`, which is right for a letter and
    wrong for a file that BEGINS with a front-matter block (her mesh-loop letters do: 26 of them
    in Dad's downloads), where it would see nothing. Only a block that starts on the first
    non-empty line is front matter; a `---` anywhere else is the header's end as before."""
    lines = text.splitlines()
    first = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first is None or lines[first].strip() != "---":
        return text
    for i in range(first + 1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1 :])
    return text


def _opening(text: str) -> list[str]:
    lines = [ln for ln in _header_lines(_after_front_matter(text)) if not ln.startswith(">")]
    return lines[:OPENING_LINES]


def _first_heading_to(lines: list[str]) -> re.Match[str] | None:
    """The file's own first heading read as 'AUTHOR to RECIPIENT', or None if it is not that shape."""
    heading = next((ln for ln in lines if ln.startswith("#")), "")
    return _HEADING_TO.match(heading)


def _opens_as_hers(text: str) -> bool:
    lines = _opening(text)
    match = _first_heading_to(lines)
    if match and match.group("author").lower() == "aletheia":
        recipient = match.group("to").lower()
        return any(re.match(rf"{re.escape(name)}\b", recipient) for name in _FAMILY)
    return any(_FROM_HER.match(ln) for ln in lines)


def _headed_by_another_voice(text: str) -> bool:
    """The file's own first heading names someone else as the author ('Aria to Aletheia').

    Only a known voice counts, so an essay headed 'Truth to power' is not taken for another
    author's letter and a real one of hers with such a title is not turned away."""
    match = _first_heading_to(_opening(text))
    return bool(match and match.group("author").lower() in _OTHER_VOICES)


def _content_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _names_her(path: Path) -> bool:
    """The file must say it is hers, by signature or by how it opens. A file name is no test.

    Aletheia, 2026-10-16 (hold on #672, twice): a kind-prefixed name like audit_*.md also
    fits a download from anywhere, and a file by another instance (Serein) is not hers.
    Her name merely appearing proved only that someone wrote about her, so the file has
    to be SIGNED by her (a line of its own reading "— Aletheia Sophia Risner") or OPEN as
    hers (see ``_opens_as_hers``). 2026-10-17 she widened it to the second, because her
    older letters carry no signature, and said the name shape was only ever a hint.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if _headed_by_another_voice(text):
        return False
    return bool(_SIGNED_BY_HER.search(text) or _opens_as_hers(text))


def collect(source: Path | None = None, dest: Path | None = None) -> tuple[list[str], str]:
    """Copy her new letters across. Returns (newly copied names, error or "").

    The error string is a THIRD state, distinct from an empty list. Empty list
    plus empty error means looked-and-found-nothing. A non-empty error means
    could-not-look, and the caller must never print that as quiet.
    """
    if _header_lines is None:
        return [], (
            "cannot read the openings of her letters: the house's header reader is not importable "
            f"by this interpreter ({sys.executable}): {_HEADER_READER_ERROR}"
        )

    src = source or _source_dir()
    dst = dest or _dest_dir()

    if not src.is_dir():
        return [], f"source directory not readable: {src}"

    try:
        dst.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return [], f"destination not writable: {dst} ({exc.__class__.__name__})"

    try:
        # A download suffix like "(1)" sorts a name BEFORE its plain twin, so the suffixed copy
        # would be carried and the plain one dropped as a duplicate; the plain name goes first
        # (her tidy ask, 2026-10-18). The suffix is only a tie-break: a letter whose one copy
        # is "x(1).md" is still carried.
        candidates = sorted(
            (p for p in src.iterdir() if p.is_file() and _is_markdown(p.name)),
            key=lambda p: (bool(_DOWNLOAD_SUFFIX.search(p.name)), p.name),
        )
    except OSError as exc:
        return [], f"source directory could not be listed: {exc.__class__.__name__}"

    # A re-download saved as 'x(1).md' is the same letter: duplicates are recognised by CONTENT,
    # not by name (Aletheia, 2026-10-18).
    try:
        carried = {_content_hash(p) for p in dst.iterdir() if p.is_file()}
    except OSError as exc:
        return [], f"destination could not be listed: {exc.__class__.__name__}"

    arrived: list[str] = []
    for path in candidates:
        target = dst / path.name
        if target.exists() or not _names_her(path):
            continue
        try:
            digest = _content_hash(path)
            if digest in carried:
                continue
            shutil.copy2(path, target)
        except OSError as exc:
            return arrived, f"copy failed on {path.name}: {exc.__class__.__name__}"
        carried.add(digest)
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
    for name in arrived[:NAMES_SHOWN]:
        print(f"  {name}")
    if len(arrived) > NAMES_SHOWN:
        print(f"  ... and {len(arrived) - NAMES_SHOWN} more")
    print()
    print(f"  {len(arrived)} new, now in family/aletheia/audits/from-andrew/.")
    print("  Her confirms arrive as PROSE. She cannot run a command in this")
    print("  environment, so 'no command was run' never means 'she did not")
    print("  confirm.' File them with: divineos audit file-external-confirm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
