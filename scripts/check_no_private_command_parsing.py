"""Refuse a new private copy of shell-command-head parsing.

WHY THIS EXISTS, AND WHY DELETING THE COPIES WAS NEVER GOING TO WORK.

Andrew 2026-09-19: *"you keep making the same mistake over and over, and even
being fully aware of it does not help.. only structure does.. make the mistake
impossible to do, by automating the correct choice before you need to make
it."*

The mistake: a caller needs to know what a shell command is actually doing,
writes five lines to find the head, and gets it subtly wrong in a way that lets
a real act past a gate. There is a module that owns exactly this question --
``divineos.core.command_parsing`` -- built after the fault had already been
filed twice. It went on happening anyway.

Aletheia counted five sites on 2026-09-19 and found the sixth herself: the
private copy in the gravity classifier did not know that ``VAR=value`` before a
command is assignment syntax, so a backdated commit escaped the gate entirely.
The seventh was worse placed than all of them -- the act-anchor, which computes
the key the whole gate system binds recorded thinking to. It could not handle a
multi-line command and returned the ENTIRE command text as the key, so filing
never stuck, and the escape telemetry counted the resulting retries as evidence
about my discipline.

**Every repair until now deleted a copy and left the gradient untouched**, and
the count climbing after each repair is the evidence. The gradient is a cost
difference at the moment of writing: five lines costs nothing right now, and
discovering the shared module costs a search that only succeeds if you already
suspect it exists. So this moves the information to the moment of the reach,
and the refusal carries the import line rather than a scolding -- a refusal
that names a fault and leaves the reader to find the remedy is precisely where
avoidance grows.

WHAT THIS CANNOT DO, said plainly so silence is never mistaken for coverage.
It matches on shapes, shapes are rephraseable, and the person who would want to
route around it is the person who wrote it. The game-walk recorded that, plus
the allowlist, plus the entire hooks tree being outside its eyes. It is a
signpost, not a wall, and it succeeds only if finding the home stays cheaper
than evading the check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEARCH_ROOTS = (ROOT / "src", ROOT / "scripts")
HOME = "divineos.core.command_parsing"

# The two shapes that mean "I am resolving a command head myself": a list of
# shell builtins treated as skippable noise, and a regex stripping the
# NAME=value prefix. Both are the real fingerprints -- the first is what every
# private copy grew, and the second is the specific thing they kept getting
# wrong. Deliberately narrow: a noisy check teaches the route around itself,
# which is the failure this repairs one level up.
_WRAPPER_LIST = re.compile(
    r"""["'](?:cd|env|sudo|exec|source)["']\s*,\s*["'](?:cd|env|sudo|exec|source|set|time)["']"""
)
_ASSIGN_STRIP = re.compile(r"\^\s*\[A-Za-z_\]\[A-Za-z0-9_\]\*=|\^\\w\+=")

# Files permitted to carry the shape, each with its reason WRITTEN DOWN.
# An entry is a claim somebody made, not a verification. The game-walk named
# "add an allowlist entry" as the cheapest route around this check, which is
# why the reason is mandatory and gets read in audit rather than trusted.
ALLOWED = {
    "src/divineos/core/command_parsing.py": "the shared home itself -- this IS the implementation",
    "scripts/check_no_private_command_parsing.py": "names the shapes in order to find them",
    # FOUND BY THIS CHECK ON ITS FIRST RUN, by shapes my own greps had missed.
    #
    # It is not a private copy. It is a SECOND extracted home, for the adjacent
    # question of whether a command INVOKES a named thing or merely MENTIONS
    # it, built after that fault recurred across three gates that were blocking
    # people for saying a word. Four callers and its own tests.
    #
    # THE ENTRY ADMITS SOMETHING RATHER THAN CLOSING THE CASE. Both homes
    # handle quotes, both know executors and assignment prefixes, and neither
    # imports the other -- the same knowledge learned twice. The honest reading
    # is that the seam is drawn in the wrong place: there is a lower layer,
    # take a command apart safely, and two questions that should both rest on
    # it. Merging is a real change against gates that refuse people, where
    # being wrong in the permissive direction lets work through silently, and
    # it is not an end-of-session change. Flagged to Aletheia unresolved.
    #
    # Granting myself an exemption on this check's first run is the exact route
    # the game-walk named as cheapest, so the defence has to be checkable by
    # someone else: the callers and the tests are facts, not a feeling. And the
    # refutation is countable without my judgement -- if this list grows, the
    # shapes are matching the wrong thing.
    "src/divineos/core/command_match.py": (
        "second extracted home for invoke-versus-mention, four callers -- the overlap with "
        "the parsing home is real, unresolved, and flagged for audit rather than fixed here"
    ),
}


def offenders() -> tuple[list[tuple[str, str]], int]:
    """Files carrying a private head-parser shape without calling the home."""
    found: list[tuple[str, str]] = []
    read = 0
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel in ALLOWED:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                # Cannot-read is not clean and must not render as a pass. It is
                # reported as its own answer, which is the whole lesson of the
                # branch this check was born on.
                found.append((rel, "COULD NOT READ THIS FILE -- unknown, not clean"))
                continue
            read += 1
            if "command_parsing" in text:
                continue
            if _WRAPPER_LIST.search(text):
                found.append((rel, "keeps its own list of shell wrappers to skip"))
            elif _ASSIGN_STRIP.search(text):
                found.append((rel, "strips NAME=value prefixes itself"))
    return found, read


def main() -> int:
    hits, read = offenders()
    if not hits:
        # Says what it searched. A quiet check and a check that ran are not the
        # same thing, and zero findings is satisfied by both.
        print(f"No private command-head parsing in {read} files outside {HOME}.")
        return 0
    print("PRIVATE COMMAND-HEAD PARSING - call the shared home instead:\n")
    for rel, why in hits:
        print(f"  {rel}\n      {why}")
    print(
        f"\n{HOME} already owns this question. It is quote-aware, treats a\n"
        "newline as the statement separator it is, and knows that NAME=value\n"
        "before a command is assignment syntax rather than the command.\n"
        "\n"
        "  from divineos.core.command_parsing import resolve_command_head\n"
        "  from divineos.core.command_parsing import split_shell_segments\n"
        "\n"
        "Every private copy so far has been wrong in a way that let a real act\n"
        "past a gate. If this file genuinely cannot use the home, add it to\n"
        "ALLOWED with the reason written out -- the reason is read in audit, so\n"
        "an empty one is worse than the import.\n"
        "\n"
        "AND THE PART THAT DIFFERS BY CALLER, because you will hit it within\n"
        "minutes: the home answers cannot-parse with None. An allowlist reads\n"
        "that as not-permitted, its safe direction. A gate asking whether an\n"
        "act OCCURRED must not read it as yes -- an act either happened or it\n"
        "did not. A gate asking whether something deserves scrutiny must not\n"
        "read it as no. Decide which question you are asking, and say which at\n"
        "the callsite rather than leaving it to a docstring in another file."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
