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
_REFERENCE = re.compile(r"\b((?:docs|scripts|src/divineos|\.claude)/[A-Za-z0-9_./-]+\.(?:md|py|sh|json|txt))")

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


def collect_references() -> dict[str, set[str]]:
    """Map referenced-path -> set of files that name it."""
    found: dict[str, set[str]] = {}
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ref in _REFERENCE.findall(text):
            found.setdefault(ref, set()).add(str(path.relative_to(REPO)).replace("\\", "/"))
    return found


def _git(args: list[str]) -> str | None:
    """None means could-not-run, which is not the same as found-nothing."""
    try:
        p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=30)
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


def classify() -> tuple[list[str], list[tuple[str, str, str, list[str]]], list[tuple[str, list[str]]]]:
    """Return (templates, stranded, absent). Present paths need no report."""
    refs = collect_references()
    templates: list[str] = []
    stranded: list[tuple[str, str, str, list[str]]] = []
    absent: list[tuple[str, list[str]]] = []

    for ref in sorted(refs):
        if _is_template(ref):
            templates.append(ref)
            continue
        if (REPO / ref).exists():
            continue
        cited_by = sorted(refs[ref])
        located = locate_on_branches(ref)
        if located:
            commit, branch = located
            stranded.append((ref, commit, branch, cited_by))
        else:
            absent.append((ref, cited_by))
    return templates, stranded, absent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show-templates", action="store_true", help="list excluded template patterns")
    ap.add_argument("--strict", action="store_true", help="exit 1 when anything dangles")
    args = ap.parse_args()

    templates, stranded, absent = classify()

    if stranded:
        print(f"STRANDED -- exists in git, absent here ({len(stranded)}):")
        for ref, commit, branch, cited_by in stranded:
            print(f"  {ref}")
            print(f"      cited by  : {cited_by[0]}" + (f" (+{len(cited_by)-1} more)" if len(cited_by) > 1 else ""))
            print(f"      lives on  : {branch}  ({commit})")
            print(f"      recover   : git checkout {branch} -- {ref}")
        print()

    if absent:
        print(f"ABSENT -- git has never seen this path ({len(absent)}):")
        for ref, cited_by in absent:
            print(f"  {ref}")
            print(f"      cited by  : {cited_by[0]}" + (f" (+{len(cited_by)-1} more)" if len(cited_by) > 1 else ""))
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

    print(f"{total} dangling reference(s): {len(stranded)} recoverable, {len(absent)} never written.")
    print("STRANDED means someone finished the work and it did not reach here.")
    print("ABSENT means the reference promises something that was never built.")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
