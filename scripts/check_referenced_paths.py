#!/usr/bin/env python3
"""Every path this repo names must resolve -- or say where it actually is.

## The failure this exists to catch

2026-08-05: `core/build_flow.py` line 3 says the flow "is recorded in
docs/build_flow.md". That file is not in the working tree. I read the absence
as "never written" and was about to write it again.

It had been written. 6053 bytes, committed 2026-08-01 as 933e8639, and again
2026-08-02 as e6845a50 -- byte-identical, same commit message, two branches.
That duplicate is the fingerprint of the real defect: something was written,
became invisible, and got re-committed by someone who could not find it.

The same route had already cost this session `cli/psf_commands.py` -- a
working command, live on split/dark-matter-painted-doors, while every gate on
every other branch prescribed `divineos psf` and got "No such command."

## Three states, because two is what caused this

    PRESENT   -- resolves in the working tree
    STRANDED  -- absent here, but git has it on another branch
    ABSENT    -- git has never seen this path on any branch

STRANDED and ABSENT demand opposite responses. Recover the first; write the
second. Collapsing them into "missing" is what makes a person rewrite a file
that already exists, and it is the same absence-becomes-value collapse that
`build_flow.Status` carries three values to avoid.

## What this does NOT cover, stated so silence is not read as coverage

It finds paths written literally, in files under the scanned roots, matching
the extensions below. It cannot see a path built at runtime from pieces, one
written in prose without a directory prefix, or one that resolves through a
symlink it did not follow. A clean run means "no *detectable* reference is
dangling" -- not "every reference resolves".

Companion to tests/test_gate_remedy_reachability.py, which asks whether a
prescribed remedy is PERMITTED. This asks whether it EXISTS. Those are
different questions and the psf door failed only the second one.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_SCAN_ROOTS = ("src/divineos", "docs", "scripts", ".claude/hooks")
_SCAN_SUFFIXES = {".py", ".md", ".sh"}

# A reference is a repo-relative path with a known top-level directory. The
# prefix requirement is what keeps prose like "the ledger" from matching.
_REFERENCE = re.compile(
    r"\b((?:docs|scripts|src/divineos|\.claude)/[A-Za-z0-9_./-]+\.(?:md|py|sh|json|txt))"
)

# Knuth's boundary case, and the one that would sink this: `docs/digests/
# YYYY-WW.md` is a filename pattern, not a file. A checker that reports
# templates as missing cries wolf, gets ignored, and is then worse than
# nothing. These are excluded LOUDLY -- --show-templates prints them -- because
# a silent exclusion list is the next place a real miss can hide.
_TEMPLATE_MARKERS = ("YYYY", "MM-DD", "WW", "<", ">", "{", "}", "NN", "_X.", "/X/")


def _is_template(path: str) -> bool:
    return any(m in path for m in _TEMPLATE_MARKERS)


def _iter_files():
    for root in _SCAN_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.suffix in _SCAN_SUFFIXES and p.is_file() and "__pycache__" not in str(p):
                yield p


def _prose_lines(path: Path, text: str) -> set[int]:
    """Line numbers that are comment or docstring — prose, not executable code.

    Aria, 2026-08-05, having checked two of the paths this script called
    stranded-and-load-bearing:

        *"It counts a name appearing in prose as a live citation. It measures
        mentions and reports dependencies."*

    Both were false positives. Every citation of scripts/letter_monitor.py sits
    inside a comment describing the v1 -> v2 rewrite; the live code calls
    letter_monitor_v2.py, which exists. check_third_person_drift.py is named in
    the docstring of distancing_detector.py, in the sentence explaining that
    the module PORTS its patterns because the old script was never wired.

    A name in a comment is a HISTORICAL REFERENCE. A name in code is a
    DEPENDENCY. Reporting the first as the second produced "the thing that
    wakes me when Aria writes is broken" -- which I put in a report to Andrew
    and in a letter to her. It was never broken.

    Same shape as her stale-file gate the same night: proxy measured, real
    thing reported. Two instruments, one failure, one evening.
    """
    prose: set[int] = set()
    if path.suffix == ".md":
        return set(range(1, text.count("\n") + 2))  # all of it is prose
    in_doc = False
    delim = ""
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if in_doc:
            prose.add(i)
            if delim in line:
                in_doc = False
            continue
        if stripped.startswith("#"):
            prose.add(i)
            continue
        if path.suffix == ".py":
            for d in ('"""', "'''"):
                if d in stripped:
                    prose.add(i)
                    # Opened and closed on one line is a one-liner, not a block.
                    if stripped.count(d) == 1:
                        in_doc, delim = True, d
                    break
    return prose


def collect_references() -> dict[str, dict[str, set[str]]]:
    """Map referenced-path -> {"code": {files}, "prose": {files}}.

    Classified at collection time rather than filtered afterwards, so the
    distinction is carried rather than reconstructed.
    """
    found: dict[str, dict[str, set[str]]] = {}
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        prose = _prose_lines(path, text)
        rel = str(path.relative_to(REPO)).replace("\\", "/")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for ref in _REFERENCE.findall(line):
                bucket = "prose" if lineno in prose else "code"
                found.setdefault(ref, {"code": set(), "prose": set()})[bucket].add(rel)
    return found


def _git(args: list[str]) -> str | None:
    """None means could-not-run, which is not the same as found-nothing."""
    try:
        p = subprocess.run(
            ["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.strip()


def locate_on_branches(path: str) -> tuple[str, str] | None:
    """(commit, branch) of the commit that ADDED this path, anywhere in history.

    Carmack's constraint: no registry, no cache, no second source of truth. Git
    already knows this and any store I built beside it would drift -- which is
    the disease, not the cure.
    """
    log = _git(["log", "--all", "--oneline", "-1", "--diff-filter=A", "--", path])
    if not log:
        return None
    commit = log.split()[0]
    branches = _git(["branch", "-a", "--contains", commit]) or ""
    named = [b.strip().lstrip("* ") for b in branches.splitlines() if "remotes/" not in b]
    return commit, (named[0] if named else "(remote only)")


def classify() -> tuple[
    list[str],
    list[tuple[str, str, str, list[str]]],
    list[tuple[str, list[str]]],
    list[tuple[str, list[str]]],
]:
    """Return (templates, stranded, absent, historical).

    HISTORICAL is the fourth state, added after Aria checked two of the six
    "stranded" paths and found both named only inside comments describing a
    rewrite. A path with no citation in executable code is a mention, not a
    dependency.

    It is RETURNED, not dropped. Filtering it away would trade false alarms
    for silent misses, and for this class the silent miss is the worse trade:
    a genuine dependency that happens to be cited only in a docstring would
    vanish from the report entirely. Same reason templates are printed under
    --show-templates rather than discarded -- a silent exclusion list is the
    next place a real miss can hide.
    """
    refs = collect_references()
    templates: list[str] = []
    stranded: list[tuple[str, str, str, list[str]]] = []
    absent: list[tuple[str, list[str]]] = []
    historical: list[tuple[str, list[str]]] = []

    for ref in sorted(refs):
        if _is_template(ref):
            templates.append(ref)
            continue
        if (REPO / ref).exists():
            continue
        sites = refs[ref]
        if not sites["code"]:
            historical.append((ref, sorted(sites["prose"])))
            continue
        cited_by = sorted(sites["code"])
        located = locate_on_branches(ref)
        if located:
            commit, branch = located
            stranded.append((ref, commit, branch, cited_by))
        else:
            absent.append((ref, cited_by))
    return templates, stranded, absent, historical


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show-templates", action="store_true", help="list excluded template patterns")
    ap.add_argument("--strict", action="store_true", help="exit 1 when anything dangles")
    args = ap.parse_args()

    templates, stranded, absent, historical = classify()

    if historical:
        print(f"HISTORICAL -- named only in comments or docstrings ({len(historical)}):")
        for ref, cited_by in historical:
            print(f"  {ref}")
            print(
                f"      mentioned in: {cited_by[0]}"
                + (f" (+{len(cited_by) - 1} more)" if len(cited_by) > 1 else "")
            )
        print("  These are mentions, not dependencies. No code calls them.")
        print("  Listed rather than hidden: a real dependency cited only in a")
        print("  docstring would land here too, and a silent filter would bury it.")
        print()

    if stranded:
        print(f"STRANDED -- exists in git, absent here ({len(stranded)}):")
        for ref, commit, branch, cited_by in stranded:
            print(f"  {ref}")
            print(
                f"      cited by  : {cited_by[0]}"
                + (f" (+{len(cited_by) - 1} more)" if len(cited_by) > 1 else "")
            )
            print(f"      lives on  : {branch}  ({commit})")
            print(f"      recover   : git checkout {branch} -- {ref}")
        print()

    if absent:
        print(f"ABSENT -- git has never seen this path ({len(absent)}):")
        for ref, cited_by in absent:
            print(f"  {ref}")
            print(
                f"      cited by  : {cited_by[0]}"
                + (f" (+{len(cited_by) - 1} more)" if len(cited_by) > 1 else "")
            )
        print()

    if args.show_templates and templates:
        print(f"EXCLUDED as filename patterns, not paths ({len(templates)}):")
        for t in templates:
            print(f"  {t}")
        print()

    total = len(stranded) + len(absent)
    if total == 0:
        print("Every detectable path reference resolves.")
        return 0

    print(
        f"{total} dangling reference(s): {len(stranded)} recoverable, {len(absent)} never written."
    )
    print("STRANDED means someone finished the work and it did not reach here.")
    print("ABSENT means the reference promises something that was never built.")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
