#!/usr/bin/env python3
"""Every confirm for a branch, newest first, each marked BINDS or SPENT.

WHY THIS EXISTS. 2026-09-18: I reported a branch as unsigned and asked my
auditor to re-confirm it. She had signed it twice -- once on 09-05, and again
on 09-14 at exactly the tree sitting on origin. I searched the findings store
for whether a confirm existed, found the older one, measured that its tree had
moved, and stopped. The measurement was correct and it was about the wrong
signature.

Her line, and it is the rule this file encodes: *when a confirm is spent, ask
whether there is a later one before reporting the branch as unsigned. Two
signatures on one branch is not unusual -- it is what happens when a branch
moves and I re-read it.*

THE SAME FIX WAS ALREADY NAMED IN MY OWN STORE and never built, filed as
"branch-resolution should prefer the NEWEST round whose confirmed tree matches
the current head, and should REFUSE rather than silently substitute". It sat as
a design question. Hand-searching is what filled the gap, and hand-searching
stops at the first hit.

WHAT THIS DOES NOT DO. It does not decide whether a branch may merge -- that is
check_multi_party_review.py, which takes an explicit round and checks for a
user confirm alongside an external-AI one. This answers the question that comes
BEFORE that one: which round should I even be pointing at.

ABSENCE IS REPORTED AS ABSENCE, never as a clean no-signature verdict. A store
that cannot be read, or a branch whose tree cannot be resolved, says so.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# A tree or tip named in a confirm's prose. Matched loosely on purpose: these
# are written by hand across two stores and the abbreviation length varies.
_HEX = re.compile(r"\b([0-9a-f]{8,40})\b")


def _git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout.strip()


def _head_tree(branch: str) -> str | None:
    code, out = _git("rev-parse", f"{branch}^{{tree}}")
    return out if code == 0 and out else None


def _confirms_mentioning(needles: list[str]) -> list:
    from divineos.core.watchmen.store import list_findings

    out = []
    for f in list_findings():
        text = ((f.title or "") + " " + (f.description or "")).lower()
        if "confirm" not in text:
            continue
        if any(n.lower() in text for n in needles):
            out.append(f)
    return out


def _binds(finding, head_tree: str) -> bool:
    """True when the finding names the current head tree.

    Compares by PREFIX in both directions, because confirms are written with
    abbreviated hashes of varying length and a strict equality test reports a
    live signature as absent -- the failure this file exists to end.
    """
    text = (finding.title or "") + " " + (finding.description or "")
    for h in _HEX.findall(text):
        if head_tree.startswith(h) or h.startswith(head_tree):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("branch", help="branch or ref to resolve confirms for")
    ap.add_argument(
        "--needle",
        action="append",
        default=[],
        help="extra text to match confirms on (repeatable); the branch name is always used",
    )
    args = ap.parse_args()

    head_tree = _head_tree(args.branch)
    if head_tree is None:
        print(
            f"[confirms] CANNOT RESOLVE {args.branch} to a tree. That is could-not-look, "
            "not an unsigned branch. Fetch the ref and re-run."
        )
        return 2

    short = args.branch.rsplit("/", 1)[-1]
    needles = [args.branch, short, *args.needle]

    try:
        found = _confirms_mentioning(needles)
    except Exception as exc:  # store unreadable
        print(
            f"[confirms] CANNOT READ the findings store: {exc}. That is could-not-look, "
            "not an unsigned branch."
        )
        return 2

    print(f"[confirms] {args.branch}")
    print(f"  head tree: {head_tree}")

    if not found:
        print(
            "  NO CONFIRM MENTIONS THIS BRANCH. Note the matching is by text, so a confirm "
            "filed under another name will not appear -- pass --needle to widen before "
            "concluding it is unsigned."
        )
        return 1

    # Newest first. The whole point: a spent signature must never be the last
    # one anybody looks at.
    found.sort(key=lambda f: getattr(f, "created_at", 0) or 0, reverse=True)

    binding = 0
    for f in found:
        state = "BINDS" if _binds(f, head_tree) else "SPENT"
        if state == "BINDS":
            binding += 1
        print(f"  {state:<5} {f.actor:<10} {(f.title or '')[:80]}")

    print()
    if binding:
        print(
            f"  {binding} of {len(found)} confirm(s) name the current tree. The branch is "
            "signed at what is on origin now."
        )
        return 0
    print(
        f"  0 of {len(found)} confirm(s) name the current tree -- every signature found is "
        "SPENT. Ask for a re-read of the delta, not a re-review of the branch."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
