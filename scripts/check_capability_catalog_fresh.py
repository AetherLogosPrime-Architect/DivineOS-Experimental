"""The map of the whole system, and whether it still describes the system.

WHY THIS EXISTS. On 2026-08-27 I built a command for the wins ledger believing
none existed. One did -- built by me two days earlier and forgotten. I had
searched before building, and the search covered my working tree, so it came
back empty and CONFIRMED me.

Andrew, on being told: *"you have a map of the entire system yes? you should so
look for it.. it may need updated and then you can automate the check to that,
and also automate updating the map as well."*

He was right that the map is the correct thing to check against. It describes
the whole command surface rather than whichever room I happen to be standing in.

AND IT WAS STALE. Regenerating it rewrote 186 lines, and before that it knew
about NEITHER wins door -- not the one I forgot, not the one I had just built.

So a prior-art check pointed at the map as it stood would have answered "no such
thing" with the authority of a system-wide index, and confirmed the duplicate
exactly as my own search did. **A stale map is a worse oracle than no map**,
because no map sends you looking and a stale map sends you building.

Nothing in the repository invoked the generator. Nothing tested the output. The
map rotted quietly for as long as it took anyone to notice, which turned out to
be the length of time between building a thing and building it again.

WHAT THIS DOES. Regenerates the catalog into a scratch location, compares it to
the committed copy, and reports the drift. Never silently rewrites: --fix is an
explicit request, because a check that quietly repairs what it measures cannot
tell you the map had rotted.

FAILS TOWARD LOUD. If the generator cannot run, this exits non-zero and says the
map is unverifiable. It does not report fresh. Could-not-check and checked-clean
are different answers, and confusing them is the failure this whole session has
been about.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_GENERATOR = REPO_ROOT / "scripts" / "generate_capability_catalog.py"
_CATALOG = REPO_ROOT / "docs" / "CAPABILITY_CATALOG.md"

# The generator writes to a fixed path. To compare without clobbering the
# committed copy, the current contents are held and restored -- so a failed
# run cannot leave the map half-written.
_VOLATILE_PREFIXES = (
    "**Generated**",
    "Generated:",
)


def _meaningful(text: str) -> list[str]:
    """Lines that describe the system, minus the ones that change every run.

    A timestamp differing is not the map drifting from reality, and counting it
    as drift would make this fire constantly -- which is how a check becomes
    noise and then becomes ignored.
    """
    return [
        line.rstrip()
        for line in text.splitlines()
        if line.strip() and not line.startswith(_VOLATILE_PREFIXES)
    ]


def regenerate() -> str | None:
    """Return the freshly generated catalog text, or None if it cannot run."""
    if not _GENERATOR.is_file():
        return None
    original = _CATALOG.read_text(encoding="utf-8") if _CATALOG.is_file() else None
    try:
        proc = subprocess.run(
            [sys.executable, str(_GENERATOR)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        if proc.returncode != 0:
            return None
        return _CATALOG.read_text(encoding="utf-8")
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        # Restore whatever was committed. The caller decides whether to keep
        # the new text; this function only measures.
        if original is not None:
            # newline="\n" or the restore leaves the file dirtier than it found
            # it: read_text strips CRLF on the way in, and a bare write_text
            # puts CRLF back on the way out. A measuring function that modifies
            # what it measures is the one thing this file exists to refuse.
            _CATALOG.write_text(original, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Is the capability map still true?")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Write the regenerated map. Explicit on purpose: a check that "
        "quietly repairs what it measures cannot report that it had rotted.",
    )
    args = parser.parse_args(argv)

    if not _CATALOG.is_file():
        print(f"[map] MISSING: {_CATALOG.relative_to(REPO_ROOT)} does not exist.")
        return 2

    committed = _CATALOG.read_text(encoding="utf-8")
    fresh = regenerate()
    if fresh is None:
        print(
            "[map] CANNOT VERIFY -- the generator did not run. This says nothing "
            "about whether the map is current; it says the question could not be "
            "asked."
        )
        return 2

    old_lines = _meaningful(committed)
    new_lines = _meaningful(fresh)
    if old_lines == new_lines:
        print(f"[map] current -- {len(new_lines)} lines, matches a fresh generation.")
        return 0

    added = len(set(new_lines) - set(old_lines))
    removed = len(set(old_lines) - set(new_lines))
    print(
        f"[map] DRIFTED: the committed map differs from the system it describes. "
        f"{added} line(s) the map does not have, {removed} it has that the system "
        "does not."
    )
    for line in list(set(new_lines) - set(old_lines))[:10]:
        print(f"  missing from the map: {line[:100]}")

    if args.fix:
        # Was a round-trip through a temp file, which bought nothing -- `fresh`
        # is already the text -- and cost the same CRLF translation twice over.
        # newline="\n" so the repaired map matches the eol=lf the repo declares;
        # without it this "fix" writes 1397 invisible differences and leaves the
        # file permanently dirty, which is the fault it was called to repair.
        _CATALOG.write_text(fresh, encoding="utf-8", newline="\n")
        print("[map] rewritten. Commit it with the change that caused the drift.")
        return 0

    print(
        "[map] Run with --fix to update it. A prior-art check pointed at a stale "
        "map answers 'no such thing' with the authority of a system-wide index, "
        "which is how a duplicate gets built by someone who did search first."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
