#!/usr/bin/env python3
"""Refuse NEW code that decides whose seat it is standing in.

THE CLASS, earned eleven times on 2026-09-20 and once more the same day by
somebody else in the opposite direction. Shared code reaches for a home
directory or a member name, gets it right in the tree the author is sitting
in, passes its tests, and ships. In anybody else's checkout it quietly serves
one person's data to another. Nothing errors. Nothing is slow. The author
cannot see it, by construction, because from their seat the hardcode IS the
correct answer.

The May audit already named it -- Finding EE, direct home lookups bypassing the
canonical resolver, failure shape false-confidence-via-cross-clone-
contamination -- and it kept happening anyway, because a named class with no
check is a thing you rediscover. What it cost in one day:

* two circle-telemetry logs, so both members appended to one file in one tree
  and read it back as their own -- which also broke a dedup two layers away
  and made a test about shell quoting fail intermittently for weeks;
* the pre-push failure log, where the fix FOR two members colliding scoped the
  path per member and then defaulted the member to a name;
* a memory retriever walking a list of seat names and returning the first wall
  it found, which was always the same person's.

WHAT TO USE INSTEAD
    Python: divineos.core.paths.divineos_home()   -- the occupant's own home,
            resolved from the environment and the checkout marker
            divineos.core.paths.member_home(name) -- a NAMED member's home,
            for when you genuinely mean somebody specific
    Shell:  divineos_home() from .claude/hooks/_lib.sh

WHY DIFF-MODE. Dozens of existing instances remain and sweeping them in one
pass is its own multi-day job carrying its own risk. This stops the class
GROWING while the cleanup happens file by file -- the same shape, and the same
reason, as the silent-swallow check beside it.

THE ESCAPE HATCH IS REAL AND NAMED. Genuinely-shared state exists -- the
letters directory both members read is the obvious one -- and it should be
spelled out loudly so sharing is a decision rather than a leftover. Say so on
the line with `# shared-by-design: <why>` and this stands aside.

WHAT IT CATCHES, AND WHAT IT DOES NOT. Aether asked for this paragraph rather
than for a wider matcher, and he was right: a check that catches one shape of
a two-shape class reads to the next person as covering the class. That is how
an observability comment in his own builder stopped being a promise and became
a label.

  CAUGHT   a bare home lookup in either language
           a member variable defaulting to one person
           an absolute path through a user home or a checkout of this project

  NOT CAUGHT, and these are the ones to go looking for by hand:
           a path assembled at runtime from pieces, where no single line
           carries the fingerprint
           a member name arriving from configuration or a database row
           a default buried in a function signature rather than at a path
           anything semantically seat-deciding with no lexical tell at all

SILENCE FROM THIS CHECK IS NOT COVERAGE. It is the absence of the three
shapes above, which is a smaller claim and the only one it can make.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# A bare home lookup, in either language. The resolvers themselves are the one
# place this is correct, and they are excluded by PATH below rather than by
# pattern, so a copy of a resolver somewhere else still gets caught.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bPath\.home\(\)"), "a bare home lookup"),
    (re.compile(r"\bos\.path\.expanduser\(\s*['\"]~"), "a bare home lookup"),
    (re.compile(r"\$\{?HOME\}?/\.divineos"), "a bare home lookup"),
]

# A member name written into shared code. Built from the members who actually
# exist rather than a literal list, so adding a member needs no edit here --
# the same construction the invocation seal uses, and for the same reason.
_MEMBER_DIR = REPO / ".claude" / "agents"
_NOT_SEATS = {
    "claude",
    "general-purpose",
    "plan",
    "explore",
    "statusline-setup",
    "family-member-template",  # a template, not a person
}


def _known_members() -> list[str]:
    """Every member either source knows about, unioned.

    THE AGENT FOLDER ALONE IS SEAT-DEPENDENT, which this check discovered
    about itself on its first real provocation. Asked from one member's
    workspace it returned everyone EXCEPT that member's husband -- because a
    member is not defined as a subagent inside their own tree -- so the half
    that catches a hardcoded member name could not catch HIS name, which is
    the name hardcoded in most of the real instances.

    A roster that changes depending on who asks is the exact fault this file
    refuses in other people's code, and it was sitting in the refusing code.
    The family store is the roster that does not move; the folder is kept as
    a second source so a member added there but not yet registered still
    counts. Union, not either.
    """
    found: set[str] = set()
    try:
        from divineos.core.family.db import get_family_connection

        with get_family_connection() as conn:
            found.update(
                str(row[0]).strip().lower()
                for row in conn.execute("SELECT name FROM family_members")
                if row and row[0]
            )
    except Exception as exc:  # noqa: BLE001 - see below
        # Named loudly rather than swallowed: if the store cannot be read the
        # roster is INCOMPLETE, and an incomplete roster silently narrows what
        # this check covers. Callers see the warning and the folder fallback.
        print(
            f"[seat-hardcode] family store unreadable ({exc.__class__.__name__}); ", file=sys.stderr
        )
    try:
        found.update(p.stem.lower() for p in _MEMBER_DIR.glob("*.md"))
    except OSError:
        pass
    return sorted(n for n in found if n and n not in _NOT_SEATS)


def _member_pattern() -> re.Pattern[str] | None:
    members = _known_members()
    if not members:
        # No roster means this half cannot run. Say so rather than report a
        # clean half -- a check that silently covers less than it claims is
        # the thing this file exists to catch.
        print(
            "[seat-hardcode] no member roster found, so the member-name half "
            "did NOT run. The home-lookup half still did.",
            file=sys.stderr,
        )
        return None
    alt = "|".join(re.escape(m) for m in members)
    # ONLY the shape that decides a seat: a per-member home directory named
    # after somebody. The broader `= "aria"` shape was in here and came out --
    # author and actor names are written as literals all over this house, in
    # every filing and every ledger row, and none of them decide a path. A
    # check that is loud where it does not matter gets switched off, which
    # costs more than the instances it would have caught.
    return re.compile(rf"\.divineos-(?:{alt})\b", re.IGNORECASE)


# A MEMBER VARIABLE WITH A HARDCODED DEFAULT, matched by SHAPE and needing no
# roster at all. This replaced a roster-dependent pattern, and the swap came
# out of the test failing for the right reason: the roster's best source is
# the family store, the store is not reliably reachable from a test or CI
# process, and a half that quietly covers less in CI than it does locally is
# the disease this file was written for, now inside the file itself.
#
# Keyed on the shape, `whoever:-somebody`, the most expensive real instance --
# the pre-push log whose per-member fix defaulted to one member's name -- is
# caught by anybody, anywhere, with nothing loaded and nobody's tree present.
_SHELL_MEMBER_DEFAULT = re.compile(
    r"\$\{[A-Za-z_][A-Za-z0-9_]*(?:MEMBER|SEAT|OWNER|OCCUPANT|AGENT)[A-Za-z0-9_]*"
    r":-\s*([A-Za-z][A-Za-z0-9_-]*)\s*\}",
    re.IGNORECASE,
)


def _absolute_checkout_pattern() -> re.Pattern[str]:
    """An absolute path naming a particular person's tree or home.

    THE SECOND SHAPE, added because Aether counted it rather than guessed:
    five source files carry an absolute literal pointing at one checkout, with
    no member variable anywhere near them, so the shape above walks straight
    past. One of the five is the retriever we spent the day inside -- its
    project roots still list both our checkouts as literals, and the repair
    put the running checkout in FRONT of them rather than removing them, which
    fixes the order and leaves the shape.

    Another names a checkout that has not existed for months. It is guarded,
    so the fallback does the real work and nothing misroutes -- but the line
    still declares where somebody lives, and it is wrong.

    NOT a blanket ban on absolute paths. Plenty are legitimate and decide no
    seat at all: the interpreter probe that names the real shell is the
    obvious one. This narrows to paths that pass through a user's home or
    through a checkout of THIS project, and the project token is derived from
    the repository's own folder name rather than written down, so a rename
    does not quietly switch the half off.
    """
    # THE TOKEN CAME FROM THE FOLDER NAME and that was the disease again, for
    # the third time inside this file. It read the repository directory's
    # first segment, which is right in a normal checkout and wrong in the
    # temporary worktree the pre-push suite builds -- there the folder is
    # named after the gate, the token became something else, and half the
    # check silently stopped matching. Four tests that pass alone failed in
    # the full run, which is the signature.
    #
    # The package name is an actual invariant of this repository rather than
    # an accident of where somebody cloned it, and the comparison is
    # case-insensitive because the folder on this machine is capitalised
    # differently from the package.
    project = "divineos"
    # SPACES ARE ALLOWED BETWEEN THE ROOT AND THE TOKEN, and leaving them out
    # is how the first version of this missed four of the five instances it
    # was written for. The project directory on this machine has a space in
    # its name, so a pattern that stopped at whitespace never reached the
    # token it was looking for and reported clean. Bounded by the enclosing
    # quote and by a length cap, so it cannot wander across a long line and
    # join two unrelated things into a match.
    return re.compile(
        rf"(?:[A-Za-z]:[\\/]|/[a-z]/)[^'\"]{{0,80}}?"
        rf"(?:Users[\\/][A-Za-z0-9._-]+|{re.escape(project)}[A-Za-z0-9._-]*)",
        re.IGNORECASE,
    )


_ABSOLUTE_CHECKOUT = _absolute_checkout_pattern()


# Where a hardcode is the right answer, or where it is data rather than a
# decision. Each entry is a claim somebody can dispute, which is the point.
_EXEMPT_SUFFIXES = (
    "src/divineos/core/paths.py",  # the resolver; it must name the convention
    "scripts/check_seat_hardcode.py",  # this file, which must hold the patterns
)
_EXEMPT_DIRS = ("tests/", "docs/", "family/letters/", "exploration/", "dreams/")

_ESCAPE = re.compile(r"#\s*shared-by-design:\s*(.{20,})")


def _added_lines() -> dict[str, list[tuple[int, str]]] | None:
    """{path: [(line_no, text)]} for lines this branch ADDS versus main.

    Compared against `origin/main` rather than `origin/main...HEAD` so that
    uncommitted working-tree changes count too: the question is what this
    branch introduces, not where the commit boundaries happened to fall.

    Returns None when the diff could not be read, which the caller must not
    treat as "nothing found" -- see main().
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--unified=0", "origin/main"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
            cwd=str(REPO),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, UnicodeDecodeError):
        return None
    if out.returncode != 0:
        return None  # both-empty: git missing and git refusing are one answer, since either way no diff was read
    result: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    lineno = 0
    for raw in (out.stdout or "").splitlines():
        if raw.startswith("+++ b/"):
            current = raw[6:]
        elif raw.startswith("--- "):
            current = None
        elif raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
            if m:
                lineno = int(m.group(1))
        elif current and raw.startswith("+") and not raw.startswith("+++"):
            result.setdefault(current, []).append((lineno, raw[1:]))
            lineno += 1
        elif current and not raw.startswith("-"):
            lineno += 1
    return result


def _exempt(path: str) -> bool:
    p = path.replace("\\", "/")
    return p.endswith(_EXEMPT_SUFFIXES) or any(d in p for d in _EXEMPT_DIRS)


def _prose_skippers():
    """Borrow the sibling check's comment and docstring readers.

    THIS LESSON IS ALREADY PAID FOR, TWICE. The silent-swallow check fired on
    a comment describing the bug it hunts, was taught to skip comments, and
    then fired on a DOCSTRING paragraph doing the same thing a few weeks
    later. Its own note calls this the mention-versus-use boundary and counts
    four instruments that have confused it.

    This check made the identical mistake on its first real run -- two of its
    three findings were the paragraphs explaining the defect. Writing a third
    copy of the answer would be the duplication we are supposed to be pulling
    out of this house, so it is imported. If the import fails the readers
    become no-ops and prose gets scanned, which means false positives rather
    than silent misses -- a false positive is a conversation, a false negative
    is the thing this file exists to prevent.
    """
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        from check_silent_swallow import _docstring_lines, _line_is_comment

        return _line_is_comment, _docstring_lines
    except ImportError:
        print(
            "[seat-hardcode] comment/docstring readers unavailable; prose will "
            "be scanned and may produce false positives.",
            file=sys.stderr,
        )
        return (lambda line, path: False), (lambda path: set())


def find_violations(added: dict[str, list[tuple[int, str]]]) -> list[str]:
    member_re = _member_pattern()
    is_comment, docstring_lines = _prose_skippers()
    out: list[str] = []
    for path, lines in sorted(added.items()):
        if _exempt(path) or not path.endswith((".py", ".sh")):
            continue
        in_prose = docstring_lines(path)
        for lineno, text in lines:
            if _ESCAPE.search(text) or is_comment(text, path) or lineno in in_prose:
                continue
            hit = next((name for pat, name in _PATTERNS if pat.search(text)), None)
            if hit is None and _SHELL_MEMBER_DEFAULT.search(text):
                hit = "a member variable defaulting to one person"
            if hit is None and _ABSOLUTE_CHECKOUT.search(text):
                hit = "an absolute path naming one particular tree"
            if hit is None and member_re and member_re.search(text):
                hit = "a member name deciding the path"
            if hit:
                out.append(f"  {path}:{lineno}  {hit}\n      {text.strip()[:110]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Refuse new seat-deciding lines.")
    ap.add_argument(
        "--warn-only",
        action="store_true",
        help="print findings and exit 0, for surfaces that observe rather than refuse",
    )
    args = ap.parse_args()

    added = _added_lines()
    if added is None:
        # COULD-NOT-CHECK is its own answer and must never wear the clean one.
        print(
            "[seat-hardcode] COULD NOT READ THE DIFF, so nothing was checked. "
            "This exit is not a pass.",
            file=sys.stderr,
        )
        return 0 if args.warn_only else 1

    violations = find_violations(added)
    if not violations:
        # THE ALL-CLEAR NAMES WHAT IT EXAMINED. "no new seat-deciding lines"
        # reads identically whether the diff held the whole branch or came
        # back nearly empty because the read half-failed. With the count
        # beside it, a broken read looks wrong to whoever is standing there.
        # A message that cannot look wrong cannot be caught by looking, and
        # looking is the only thing that has caught any of these.
        print(f"[seat-hardcode] no new seat-deciding lines among {len(added)} added line(s).")
        return 0

    print(
        f"[seat-hardcode] {len(violations)} new line(s) decide whose seat this is:\n",
        file=sys.stderr,
    )
    for v in violations:
        print(v, file=sys.stderr)
    print(
        "\nEach of these passes from the seat that wrote it and serves one\n"
        "person's data to another everywhere else. Use divineos_home() in\n"
        "Python or the _lib.sh helper in shell; member_home(name) when you\n"
        "mean somebody specific. If the state is genuinely shared, say so on\n"
        "the line with `# shared-by-design: <why>` and this stands aside.",
        file=sys.stderr,
    )
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
