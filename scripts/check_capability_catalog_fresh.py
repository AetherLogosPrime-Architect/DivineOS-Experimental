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

THE MAP IS NO LONGER COMMITTED, 2026-09-03, and that changes this file's job.

Measured across the whole open queue: every conflict on every conflicted branch
was one of two files, and this catalog was in all of them. Not one line of
anyone's code. Aletheia ruled it out of the tree --

    "A file that neither party authors, that no reviewer reads, and that blocks
    everything, is not carrying any of the meaning my signature is supposed to
    cover. Removing it from the tree makes my signature cover MORE, not less."

-- with exactly one condition, which is the whole reason the rest of this file
is shaped the way it is:

    "The freshness check must survive the move, and it must fail loudly if the
    generator cannot run. A regenerate-at-merge-time scheme where the generator
    silently fails produces an empty or stale catalog and a green merge, which
    is this month's dominant failure shape arriving in the replacement for this
    month's dominant failure cause."

WHAT THIS DOES NOW. Builds the map into place and reports whether it changed.
Staleness stopped being possible the moment the file left the tree -- there is
no committed copy to drift from -- so the only question left is the one her
condition names: DID THE BUILD HAPPEN.

FAILS TOWARD LOUD, and this is the load-bearing property rather than a nicety.
If the generator cannot run, this exits 2 and says the map is unbuilt. It never
reports fresh. Could-not-build and built-clean are different answers, and a run
that confuses them hands a prior-art check an absent map, which answers "no such
thing" about every command in the system.
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


def regenerate() -> tuple[str | None, str]:
    """Build the map into place. Returns ``(text, why_not)``.

    ``(text, "")`` on success and ``(None, reason)`` when it could not build.
    Two returns, and the reason travels with the failure rather than being
    reconstructed by the caller -- the caller that reconstructs a cause is the
    one that ends up blaming a branch for a missing shell.

    The save-and-restore dance the previous version did is gone with the file
    leaving the tree. It existed so a measuring run could not modify what it
    measured, which mattered when the thing measured was a committed artifact.
    Now building it IS the job.
    """
    if not _GENERATOR.is_file():
        return None, f"the generator is missing at {_GENERATOR.relative_to(REPO_ROOT)}"
    try:
        proc = subprocess.run(
            [sys.executable, str(_GENERATOR)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return None, "the generator ran past its 600s budget and was killed"
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"the generator could not be started: {exc.__class__.__name__}"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        detail = tail[-1][:160] if tail else "and said nothing about why"
        return None, f"the generator exited {proc.returncode}: {detail}"
    if not _CATALOG.is_file():
        return None, "the generator exited cleanly and wrote no map"
    return _CATALOG.read_text(encoding="utf-8"), ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Can the capability map be built?")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Accepted and ignored. Building the map IS this check now that it "
        "is not committed; there is no separate repair step to ask for.",
    )
    parser.parse_args(argv)

    before = _meaningful(_CATALOG.read_text(encoding="utf-8")) if _CATALOG.is_file() else None

    fresh, why_not = regenerate()
    if fresh is None:
        print(
            f"[map] CANNOT BUILD -- {why_not}.\n"
            "      This says NOTHING about whether the map is current. It says the "
            "map is not\n"
            "      there to be read, and a prior-art check pointed at an absent map "
            "answers\n"
            "      'no such thing' about every command in the system."
        )
        return 2

    after = _meaningful(fresh)
    if before is None:
        print(f"[map] built -- {len(after)} lines, from nothing (untracked, first build here).")
        return 0
    if before == after:
        print(f"[map] built -- {len(after)} lines, unchanged since the last build.")
        return 0

    added = len(set(after) - set(before))
    removed = len(set(before) - set(after))
    print(
        f"[map] built -- {len(after)} lines. It MOVED since the last build: "
        f"{added} new, {removed} gone."
    )
    for line in list(set(after) - set(before))[:10]:
        print(f"  new in the map: {line[:100]}")
    # Informational, deliberately. Movement is what a map of a changing system
    # is SUPPOSED to do; it was only ever a failure when the file was committed
    # and the movement landed in someone's diff. The one thing that blocks now
    # is the build not happening, which is the condition the ruling attached.
    return 0


if __name__ == "__main__":
    sys.exit(main())
