"""Find comments that make a capability claim nothing tests.

WHY THIS EXISTS. Twice in one session a comment answered the exact question a
reader would ask before opening the code, and answered it wrongly.

    # A real pipeline, not a logical-or and not a pipe inside quotes-only.

That line sat two lines above a raw substring test. It had never excluded a
quoted bar. I went looking for precisely whether quoted bars were handled,
found that sentence, and moved on -- twice, hours apart, in a file I was
actively repairing.

Aletheia named the class on 2026-08-27: which comments in this house make a
capability claim, and does anything test them? She called it the painted-door
class relocated into documentation, and the relocation is what makes it worse
than a stale comment. A stale comment decays away from a truth. These were
wrong when written, and they sit where verification BEGINS -- so they do not
merely fail to help, they terminate the search that would have found the bug.

WHAT IT REPORTS, AND WHAT IT DOES NOT. A claim whose enclosing symbol is named
nowhere in tests/ is reported UNVERIFIED. That is not an accusation that the
comment is false. It is the statement that nothing in this repository would
notice if it became false.

    claimed     the comment asserts a behaviour
    covered     some test names the enclosing symbol
    UNVERIFIED  claimed and not covered

DELIBERATELY NOT A GATE, and the reason comes from the same finding. Wiring
this to refuse commits would fire on hundreds of honest comments and teach
everyone to route around it -- the decay path this house has already watched
turn a working hook into noise. It is a search instrument. It ranks where to
look. The standing risk of the alternative is a tool built and never
connected; this one is connected to a person, on purpose, and says so rather
than pretending a threshold would make it safe.

SUBJECT-REPORT, NOT SELF-REPORT (Aletheia, same day). Every run prints what it
EXAMINED -- files opened, comments read, claims matched -- not merely that it
ran. An instrument reporting on itself cannot report on its subject, and zero
findings from a scanner that opened no files is indistinguishable from a clean
house.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# EXCLUSION claims only, and the narrowing is the whole design.
#
# The first version matched any present-tense capability verb and returned
# 1,353 findings against this repo -- unusable, and unusable in the specific
# way that gets an instrument switched off.
#
# What the two real instances had in common was not that they claimed a
# capability. It was that they claimed a NON-capability: this does not happen,
# that case is excluded, only these inputs reach here. And the failure
# direction is why that matters.
#
#   a wrong POSITIVE claim ("handles UTF-8") fails LOUDLY -- the unhandled
#   case arrives and something breaks
#
#   a wrong EXCLUSION claim ("not a pipe inside quotes") fails SILENTLY --
#   the reader consults it to decide whether their case is covered, is told
#   it is, and stops looking
#
# The second is the painted door. It does not merely fail to help; it ends
# the search that would have found the defect. Same asymmetry that runs
# through every finding in this house: the direction that fails toward
# silence is the one worth an instrument.
_CLAIM = re.compile(
    r"(\bnot an?\b|\bnever\b|\bexcludes?\b|\bignores?\b|\bskips?\b"
    r"|\bstrips?\b|\bfilters? out\b|\brefuses?\b|\bdoes not\b|\bcannot\b"
    r"|\bonly (?:fires|runs|matches|applies|counts|reaches|when|if)\b)",
    re.IGNORECASE,
)

# Prose describing a PLAN, a REASON, or an INCIDENT is not a capability claim
# about the code beneath it. Treating it as one buries the real findings under
# the house's own history, of which this repo has a great deal.
_NOT_A_CLAIM = re.compile(
    r"\b(would|should|could|might|used to|no longer|why|because|todo|"
    r"wanted|meant to|tried|failed|instance|20\d\d-\d\d-\d\d)\b",
    re.IGNORECASE,
)


# A claim only becomes a PAINTED DOOR when it sits over a branch.
#
# The exclusion narrowing alone still returned 1,219 findings, because
# "not a" appears in ordinary explanatory prose throughout this repo --
# "name a design class, not a corrective evaluation" claims nothing about
# code at all.
#
# What both real instances shared was position: each sat directly above a
# guard and described what THAT GUARD excludes. That is the checkable form,
# and it is the form a reader consults. Nobody opens a module header to find
# out whether their input reaches line 400; they read the comment above the
# branch that would turn it away.
#
# So the subject is not the verb and not the file. It is a comment making an
# exclusion claim within a few lines of the branch that would enforce it.
_GUARD_LINE = re.compile(
    r"^\s*(if|elif|return|raise|continue|break|sys\.exit|exit)\b"
    r"|^\s*\[\[|^\s*\]\]\s*&&|^\s*(fi|then)\b"
)


def _guard_lines(lines: list[str]) -> set[int]:
    return {i for i, raw in enumerate(lines, start=1) if _GUARD_LINE.search(raw)}


@dataclass(frozen=True)
class Claim:
    path: str
    line: int
    symbol: str
    text: str
    covered: bool


@dataclass
class Tally:
    """What the run EXAMINED. Printed always, including on a clean result."""

    files_opened: int = 0
    files_unparsed: int = 0
    comments_read: int = 0
    claims_matched: int = 0


def _test_corpus() -> str:
    parts = []
    for path in sorted((REPO_ROOT / "tests").rglob("*.py")):
        try:
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def _python_symbols(text: str) -> list[tuple[int, int, str]]:
    """Return (start_line, end_line, name) for every def and class."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    out: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(node, "end_lineno", None) or node.lineno
            out.append((node.lineno, end, node.name))
    out.sort(key=lambda item: item[1] - item[0], reverse=True)
    return out


def _enclosing(symbols: list[tuple[int, int, str]], line: int) -> str:
    """The tightest symbol containing this line, or the one just below it.

    A capability claim usually sits ABOVE the thing it describes -- a header
    comment on a function, or a note over a guard. Searching only inside
    bodies would miss exactly the placement that misleads.
    """
    best = ""
    for start, end, name in symbols:
        if start <= line <= end:
            best = name
    if best:
        return best
    below = [(start, name) for start, _end, name in symbols if 0 < start - line <= 4]
    return min(below)[1] if below else ""


def scan_file(path: Path, corpus: str, tally: Tally) -> list[Claim]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        tally.files_unparsed += 1
        return []
    tally.files_opened += 1

    symbols = _python_symbols(text) if path.suffix == ".py" else []
    guards = _guard_lines(text.splitlines())
    if path.suffix == ".py" and not symbols and "def " in text:
        tally.files_unparsed += 1

    found: list[Claim] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped.startswith("#"):
            continue
        tally.comments_read += 1
        body = stripped.lstrip("#").strip()
        if len(body) < 15:
            continue
        if not _CLAIM.search(body) or _NOT_A_CLAIM.search(body):
            continue
        # Within three lines of the branch it describes, or it is prose.
        if not any(lineno < g <= lineno + 3 for g in guards):
            continue
        tally.claims_matched += 1
        symbol = _enclosing(symbols, lineno)
        # No resolvable symbol means there is nothing to look for in the
        # tests, so the question cannot be answered. Report it as uncovered
        # rather than dropping it: unknown is its own answer, not a pass.
        covered = bool(symbol) and (symbol in corpus)
        found.append(
            Claim(
                path=str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                line=lineno,
                symbol=symbol or "<module-level>",
                text=body[:110],
                covered=covered,
            )
        )
    return found


def collect(roots: list[str]) -> tuple[list[Claim], Tally]:
    tally = Tally()
    corpus = _test_corpus()
    claims: list[Claim] = []
    for root in roots:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for suffix in ("*.py", "*.sh"):
            for path in sorted(base.rglob(suffix)):
                if "/tests/" in str(path).replace("\\", "/"):
                    continue
                claims.extend(scan_file(path, corpus, tally))
    return claims, tally


def _printable(text: str) -> str:
    """Survive a console that cannot encode what the repo contains.

    Second instance today. A sibling checker crashed mid-list on a cp1252
    console after printing six findings, and the crash looked exactly like
    completion -- output stopped at a plausible place with no error visible
    above the fold. The fix existed in that script and was not carried here,
    which is its own small instance of the class this whole file is about.
    """
    try:
        text.encode(sys.stdout.encoding or "utf-8")
    except (UnicodeEncodeError, LookupError):
        return text.encode("ascii", "replace").decode("ascii")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report untested capability claims in comments.")
    parser.add_argument("--roots", nargs="*", default=["src", "scripts", ".claude/hooks"])
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)

    claims, tally = collect(args.roots)
    unverified = [claim for claim in claims if not claim.covered]

    # The subject, first and unconditionally. A scanner that opened nothing
    # and a house with nothing to find print the same finding count.
    print(
        f"[examined] files={tally.files_opened} unparsed={tally.files_unparsed} "
        f"comments={tally.comments_read} claims={tally.claims_matched}"
    )
    if tally.files_opened == 0:
        print("[examined] NOTHING OPENED -- this result says nothing about the repo.")
        return 1

    print(
        f"[claims] {len(claims)} capability claims, "
        f"{len(unverified)} whose symbol is named in no test"
    )
    for claim in unverified[: args.limit]:
        print(_printable(f"  {claim.path}:{claim.line}  [{claim.symbol}]  {claim.text}"))
    if len(unverified) > args.limit:
        print(f"  ... and {len(unverified) - args.limit} more (raise --limit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
