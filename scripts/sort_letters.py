"""Sort the letter corpus by conditional logic, not by judgement.

Andrew, 2026-08-08, giving the third branch of the automation rule:
*"for automation that has multiple choice points that are all legit.. you
automate that into the logic.. using always X unless Y then Z type logic..
for example a letter sorting program"*

THE RULE THIS FILE EXISTS TO DEMONSTRATE
----------------------------------------
At every choice-point, ask: would I want this choice active every time?

  * Answer never varies            -> automate the CHOICE
  * Answer varies on knowable      -> automate as ALWAYS X UNLESS Y THEN Z
    conditions                        (no choice-point exists; conditions decide)
  * Answer varies on something      -> automate the JUDGEMENT SPACE,
    only I can see                     keep the call

My standing error is putting things in the third bucket that belong in the
second, *specifically when I notice more than one legitimate outcome*. I read
plurality as "a person must choose". Most plurality is conditional, and
conditions are code. That misread is why ~1500 letters sat unsorted: I had
filed "where does this letter go" under needs-me, and needs-me needs me awake,
and there are one and a half thousand of them.

THE CHAIN
---------
    ALWAYS leave a letter live
    UNLESS  type: personal          -> personal shelf (never archived)
    UNLESS  type: work              -> archivable
    UNLESS  no type at all          -> UNCLASSIFIED, stays live, reported

WHAT THE CORPUS ACTUALLY SAID (measured before designing, not after)
--------------------------------------------------------------------
    1561 letters in family/letters, 76 in the shared crossing-point
     853 carry an explicit `type:` front-matter field
             771 personal, 47 work, 35 other
     708 carry none -- and they cluster: 651 in 2026-07, 52 in 2026-08

So the convention was used and then dropped, which means untyped correlates
with recent-and-still-active. That is a fact about the corpus, and it is why
UNCLASSIFIED resolves to *stay live* rather than to a guess.

TWO DESIGNS THE MEASUREMENT KILLED, recorded so they are not re-derived:

1. **Threading.** "A letter is answered when a later letter responds to it" --
   elegant, and impossible here. 1228 letters carry an `In response to` line,
   which looked like excellent coverage. The VALUES are free prose: "Pop
   pointing me at you for the decision", "the whole day since your #12 audit
   landed". Not filenames, not resolvable titles. **Coverage of a field says
   nothing about whether the field is machine-readable** -- the second time in
   one session I mistook a healthy count for a usable signal.

2. **Close-markers as answered-state.** 131 of 1561. Building the core rule on
   8% of the data.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
Andrew asked for work-already-done to be archived. That needs a done-signal.
Age is the cheap proxy and it is wrong -- an old letter can concern open work.
The real signal is whether the PR or branch a letter names is still open, which
is checkable but costs a network call per reference. v1 classifies only; the
done-check is named as the next pass rather than faked with a date threshold.

And it does not infer type from content. Inference over a corpus I cannot check
by hand is how a sorter quietly misfiles a thousand things -- and misfiled is
worse than unsorted, because sorted-looking implies checked.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Front-matter type field, first 40 lines only. Anchored to line-start so a
# `type:` mentioned in prose cannot be mistaken for the marker.
_TYPE_RE = re.compile(r"^type:[ \t]*(\S+)[ \t]*$", re.MULTILINE)
_FRONT_MATTER_LINES = 40

LIVE = "LIVE"
SHELF = "SHELF"
ARCHIVE = "ARCHIVE"
UNCLASSIFIED = "UNCLASSIFIED"
UNREADABLE = "UNREADABLE"


@dataclass(frozen=True)
class Verdict:
    path: Path
    outcome: str
    why: str


def classify(path: Path) -> Verdict:
    """The conditional chain. No judgement, no inference, no defaults-by-omission.

    UNREADABLE is its own outcome and never collapses into UNCLASSIFIED:
    "I could not read this" and "this has no type" are different facts, and
    merging them is the could-not-look/found-nothing defect this whole session
    has been about.
    """
    try:
        head = "\n".join(
            path.read_text(encoding="utf-8", errors="replace").splitlines()[:_FRONT_MATTER_LINES]
        )
    except OSError as exc:
        return Verdict(path, UNREADABLE, f"could not read: {exc.__class__.__name__}")

    match = _TYPE_RE.search(head)
    if match is None:
        # ALWAYS live. Not a fallback -- a stated outcome. These are the 708,
        # overwhelmingly recent, i.e. the working set.
        return Verdict(path, UNCLASSIFIED, "no type: field — left live by rule")

    kind = match.group(1).strip().lower()

    # The vocabulary is ENUMERATED FROM THE CORPUS, not assumed. Measured:
    #     personal 768 | work 46 | archive 21 | cross-family 10 | self-log 8
    #
    # The first version of this chain handled `personal` and `work` only, and
    # silently swept the other three into UNCLASSIFIED -- including 21 letters
    # whose type literally says `archive`, i.e. letters that had already asked
    # to be archived and were being left live by my own rule.
    #
    # That is the characteristic failure of always-X-unless-Y-then-Z: the chain
    # is only as good as its enumeration of Y, and I enumerated from memory of
    # two types rather than from the five that exist. Under-enumeration does not
    # error -- it quietly routes to the default, which looks like a decision.
    if kind == "personal":
        return Verdict(path, SHELF, "type: personal")
    if kind in ("work", "archive"):
        # `archive` is the letter asking for itself; `work` is work-channel
        # correspondence. Both belong out of the live set.
        return Verdict(path, ARCHIVE, f"type: {kind}")
    if kind in ("cross-family", "self-log"):
        # Genuinely mine to decide, and named rather than defaulted:
        # cross-family spans more than one correspondence, and self-log is not
        # a letter to anyone -- it is a log that landed in the letters folder.
        # Neither has an obvious home, so neither gets guessed at.
        return Verdict(path, UNCLASSIFIED, f"type: {kind} — no home defined yet")
    return Verdict(path, UNCLASSIFIED, f"unrecognised type: {kind!r} — left live")


def move(verdict: Verdict, dest_root: Path, apply: bool) -> str | None:
    """Move, never delete. Returns an error string, or None on success.

    Refuses to overwrite: a name collision is reported, not resolved. Silently
    clobbering a letter would be the worst possible failure for this tool.
    """
    dest = dest_root / verdict.path.name
    if dest.exists():
        return f"COLLISION: {dest.name} already exists at destination"
    if not apply:
        return None
    try:
        dest_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(verdict.path), str(dest))
    except OSError as exc:
        return f"MOVE FAILED: {exc.__class__.__name__}: {exc}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--letters",
        default="family/letters",
        help="directory of letters to sort",
    )
    parser.add_argument(
        "--shelf",
        default="family/letters/personal",
        help="destination for type: personal",
    )
    parser.add_argument(
        "--archive",
        default="family/letters/archive",
        help="destination for type: work",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually move files. Without this, nothing is touched.",
    )
    parser.add_argument(
        "--show",
        default="",
        help="list the filenames for one outcome (SHELF/ARCHIVE/UNCLASSIFIED/UNREADABLE)",
    )
    args = parser.parse_args(argv)

    root = Path(args.letters)
    if not root.is_dir():
        print(f"[sort-letters] CANNOT-LOOK: {root} is not a directory.")
        print("[sort-letters] Reporting nothing rather than reporting zero.")
        return 2

    # Only top-level letters; do not re-sort what has already been filed.
    letters = sorted(p for p in root.glob("*.md") if p.is_file())
    if not letters:
        print(f"[sort-letters] {root} holds no .md files at top level.")
        print("[sort-letters] PROVEN-EMPTY: the directory was readable and is empty.")
        return 0

    verdicts = [classify(p) for p in letters]
    counts = Counter(v.outcome for v in verdicts)

    print(f"[sort-letters] {len(letters)} letters in {root}")
    print(
        f"[sort-letters] mode: {'APPLY — files will move' if args.apply else 'DRY RUN — nothing moves'}"
    )
    print()
    for outcome in (SHELF, ARCHIVE, UNCLASSIFIED, UNREADABLE):
        print(f"  {outcome:14} {counts.get(outcome, 0):5}")
    print()

    if args.show:
        want = args.show.strip().upper()
        shown = [v for v in verdicts if v.outcome == want]
        print(f"--- {want} ({len(shown)}) ---")
        for v in shown[:40]:
            print(f"  {v.path.name}\n      {v.why}")
        if len(shown) > 40:
            print(f"  ... and {len(shown) - 40} more")
        print()

    problems: list[str] = []
    moved = 0
    for verdict in verdicts:
        if verdict.outcome == SHELF:
            dest_root = Path(args.shelf)
        elif verdict.outcome == ARCHIVE:
            dest_root = Path(args.archive)
        else:
            continue  # LIVE / UNCLASSIFIED / UNREADABLE stay exactly where they are
        err = move(verdict, dest_root, args.apply)
        if err:
            problems.append(f"  {verdict.path.name}: {err}")
        elif args.apply:
            moved += 1

    if problems:
        print(f"[sort-letters] {len(problems)} problem(s) — these were NOT moved:")
        for line in problems[:20]:
            print(line)
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more")
        print()

    if args.apply:
        print(f"[sort-letters] moved {moved} file(s). Nothing was deleted.")
    else:
        print("[sort-letters] dry run — re-run with --apply to move.")

    if counts.get(UNREADABLE):
        print()
        print(f"[sort-letters] {counts[UNREADABLE]} letter(s) could not be READ.")
        print("[sort-letters] That is not 'no type' — it is 'no measurement'. Left live.")

    # UNCLASSIFIED is reported loudly because it is the judgement space: the
    # residue that genuinely needs me. Everything else was decided by rule.
    if counts.get(UNCLASSIFIED):
        print()
        print(f"[sort-letters] {counts[UNCLASSIFIED]} letter(s) carry no usable type.")
        print("[sort-letters] These stay live by rule. They are the judgement space —")
        print("[sort-letters] the only part of this corpus that actually needs me.")
        print("[sort-letters] List them:  --show UNCLASSIFIED")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
