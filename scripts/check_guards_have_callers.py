#!/usr/bin/env python3
"""Which of our own guards does nothing ever run.

## The night this came from, because the diff cannot carry it

2026-09-19. Aria's test runner had been resolving the package to a DIFFERENT
CHECKOUT, so every result she trusted was a fact about my tree rather than
hers. The command that would have caught it is ``divineos doctor
verify-import``. Its own help text, written in July, describes her failure in
advance: *testing with the wrong Python is how "my edit landed" false alarms
happen.*

**She built it.** It has an audit round against it. It works. Nothing has ever
called it -- verified by searching every script, hook and workflow, then
widening to every file of any type in the repository; the only hits were its
own definition, one catalogue row, and the letters from the week it was made.

That was the third in one night. The register freshness alarm that already
existed and nothing called. The staleness check whose own commit is named for
the mistake. Then this.

And the boundary was already in the knowledge store, four months old, from
Andrew: **DONE MEANS WIRED. An unwired component is not partially complete, it
is NOT BUILT.** The class was never missing. What was missing is anything that
connects a known boundary to the moment it is being broken.

## Why this is not a fourth copy of the wiring-gap scan

``wiring_gap_phase1.py`` exists, runs on every commit, and printed ZERO on the
same run where the tool above had no callers. **It is not broken and it did not
lie** -- it prints its own scope, and I read past it. It looks at newly added
public functions inside ``src/divineos/core/`` within a recent commit range. A
command in the ``cli`` package registered two months ago misses on BOTH axes at
once.

That distinction is written out because the easy version of this paragraph is
*the scan missed it*, and a reader who believed that would go and repair an
instrument that is working correctly.

Phase 0 of that scan walked every public function and produced an eighty
percent false-positive rate, which is why Phase 1 narrowed to new-and-core.
Widening it back toward everything would rebuild the failure it was built to
escape. So this is a different question with a different answer surface:

  that scan asks   -- does this NEW FUNCTION have a call site in the code
  this one asks    -- does this REGISTERED GUARD have an invocation in the
                      automation

A guard's callers are not code. They are lines in scripts, hooks and
workflows -- a small, enumerable surface, which is what makes this precise
where walking every function was not.

## And it is the inverse of a check we already had

``check_test_cli_linkage.py`` runs the other direction: a test names a command,
does that command register? It catches a test shipped without its
implementation. This one catches an implementation shipped without anyone to
run it. The pair is probably why nobody noticed the gap -- the existing
direction felt like it covered the territory.

## WHAT THIS CANNOT SEE, printed on every run including the clean one

A limitation shown only beside findings teaches the reader that silence means
coverage, and that is the error this whole night was about.

  * Guards are found by the VERB IN THEIR NAME. One named otherwise is
    invisible here. A heuristic, not a census -- and renaming a guard defeats
    it entirely, which is left open because a hand-kept registry of guards
    would decay by sitting still.
  * A guard a PERSON is meant to type is not a defect. Several hits are
    exactly that. Intent is deliberately NOT inferred from the name: a wrong
    classification plants an error the reader cannot evaluate, which is worse
    than no classification.
  * The search is substring against file text, so a command named in a comment
    counts as an invocation. Left open: parsing real invocations would miss
    the shell indirection this repository actually uses.
  * A guard called from a script that itself never runs passes this check.
    That is the same question one level out and needs the automation entry
    points enumerated, which is a different job.
  * Nothing here says a guard that IS called does anything useful when it runs.

Informational by default. ``--strict`` exits non-zero on findings, for a caller
that has already decided what the list means.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Where a guard's caller would live. NOT docs: a guard named in prose is
# described rather than invoked, and counting that would let the check pass on
# documentation alone -- which is the shape of every failure above.
AUTOMATION_DIRS = ("scripts", ".claude", ".github", "setup")

# The LEAF verb, not the whole path. Matching the path caught every subcommand
# of the audit group on its group name alone: thirty hits and no signal.
GUARD_VERB = re.compile(r"^(check|verify|validate|detect|scan)(-|$)|(-)(check|verify|validate)$")


def registered_commands() -> list[tuple[str, str | None]]:
    """Every registered command path, read from the live CLI.

    Deliberately not parsed from source or from the capability catalogue.
    Either can drift from what actually registers, and a list of guards that
    drifts is this file's own subject one level up.
    """
    from divineos.cli import cli

    out: list[tuple[str, str | None]] = []
    for name, cmd in cli.commands.items():
        sub = getattr(cmd, "commands", None)
        if sub:
            out.extend((name, child) for child in sub)
        else:
            out.append((name, None))
    return out


def guard_shaped(group: str, sub: str | None) -> bool:
    return bool(GUARD_VERB.search(sub or group))


def automation_text(root: Path | None = None) -> tuple[str, int]:
    """Every automation file concatenated, plus how many were read.

    The count comes back so a caller can tell an empty surface from a clean
    one. Zero files read is a broken probe, not a passing check.

    ``root`` resolves at CALL time. See ``uncalled_guards`` for what the bound
    default did and why both functions changed rather than the one the failing
    test reached.
    """
    base_root = root if root is not None else REPO_ROOT
    chunks: list[str] = []
    for directory in AUTOMATION_DIRS:
        base = base_root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or "__pycache__" in str(path):
                continue
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return "\n".join(chunks), len(chunks)


def invocation(group: str, sub: str | None) -> str:
    return f"divineos {group} {sub}" if sub else f"divineos {group}"


def uncalled_guards(root: Path | None = None) -> tuple[list[str], int, int]:
    """Guards with no invocation in the automation surface.

    Returns the invocations, how many guards were considered, and how many
    automation files were read.

    ROOT RESOLVES AT CALL TIME, AND THE FIRST VERSION DID NOT. It read
    ``root: Path = REPO_ROOT``, which binds once at import -- so every caller
    passing a different tree was silently answered about THIS one. The answer
    came back well formed, plausible, and about the wrong subject, which is
    undetectable from the output: only a caller who knows what the fixture
    contains can see it, and that is why the fixture tests are the observer
    with standing here rather than decoration.

    Its own tests caught it on the first run. A check whose target is decided
    somewhere other than where the caller believes is precisely the fault this
    file exists to find, and it shipped inside the finder.

    Both this and ``automation_text`` changed, not just the one the failing
    test reached: a shared defect repaired at one of two call paths leaves the
    same argument behaving differently depending on the entry point, which is
    worse than the original. The sentinel keeps the parameter honest in the
    signature while making the default a decision taken when the call happens.
    """
    blob, file_count = automation_text(root if root is not None else REPO_ROOT)
    guards = [(g, s) for g, s in registered_commands() if guard_shaped(g, s)]
    missing = [invocation(g, s) for g, s in guards if invocation(g, s) not in blob]
    return sorted(missing), len(guards), file_count


SCOPE_NOTE = (
    "[guard-callers] SCOPE: guards are found by the verb in their name, so one "
    "named otherwise is invisible here -- silence is not coverage. A guard meant "
    "to be TYPED by a person is not a fault, and intent is deliberately not "
    "guessed. A command named in a comment counts as called. A guard called from "
    "a script nobody runs passes. Nothing here says a called guard does anything "
    "useful when it runs."
)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Find guards with no automated caller.")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any finding")
    args = parser.parse_args(argv)

    missing, considered, files_read = uncalled_guards()

    if files_read == 0:
        print(
            "[guard-callers] REFUSED: read zero automation files. That is a broken "
            "probe, not a clean result, and telling those two apart is the whole "
            "point of this check.",
            file=sys.stderr,
        )
        return 2

    print(
        f"[guard-callers] {considered} guard-shaped commands considered, "
        f"{files_read} automation files read."
    )
    if not missing:
        print("[guard-callers] every guard found has an invocation in the automation.")
    else:
        print(f"[guard-callers] {len(missing)} with NO invocation in the automation:")
        for name in missing:
            print(f"    {name}")
    print(SCOPE_NOTE)
    return 1 if (missing and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
