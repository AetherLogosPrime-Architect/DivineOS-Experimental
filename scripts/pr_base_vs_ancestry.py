"""Print a pull request's DECLARED base beside its MEASURED ancestry.

WHY THIS EXISTS
---------------
2026-09-19: I told Aria that one of her branches was stacked on another and
had drifted off its base, and recommended a rebase. They were siblings off a
common ancestor on main; neither contained the other. A rebase would have
rewritten one of them onto a base it never had.

I had not measured anything. I read the `baseRefName` field on the pull
request -- which records what someone AIMED the request at -- and reported it
as though it described where the branch came from. Both facts were true at
once, which is exactly why the mistake was invisible: the request really is
aimed there, and the branches really are siblings.

The same shape landed twice more the same day: a telemetry file whose opening
sentence promised a rate it could not compute, and a refusal cause I probed on
one branch of six and described for all six. In every case the SYMPTOM was
real. A wrong explanation of a real symptom is worse than missing it, because
it arrives with a remedy attached.

WHAT THIS DOES ABOUT IT
-----------------------
It does not check my prose -- nothing can. It removes the step where the two
get confused, by making them arrive together. Asking for one prints both, side
by side, with the word MEASURED or DECLARED against each. You cannot read the
declared base out of this tool without also reading what git says.

WHAT IT CANNOT DO
-----------------
It cannot tell you the declared base is WRONG. Aiming a request at a sibling
branch is a legitimate thing to do -- it is how you ask for a diff against
something other than main. This tool reports the disagreement; whether the
disagreement is a mistake is a judgement it does not make.
"""

from __future__ import annotations

import json
import subprocess
import sys


def _git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def declared_base(pr: str) -> tuple[str, str]:
    """The base someone TYPED on the request, plus the head branch."""
    r = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "baseRefName,headRefName"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"[base-vs-ancestry] cannot read request {pr}: {r.stderr.strip()}")
    d = json.loads(r.stdout)
    return d["baseRefName"], d["headRefName"]


def ancestry(base: str, head: str) -> list[str]:
    """What git says about the two branches, as lines ready to print."""
    b, h = f"origin/{base}", f"origin/{head}"
    subprocess.run(["git", "fetch", "origin", base, head, "-q"], capture_output=True)

    for ref in (b, h):
        if _git("rev-parse", "--verify", "-q", ref)[0] != 0:
            return [
                f"  MEASURED   UNCHECKED -- {ref} is not on this machine; nothing was measured."
            ]

    base_in_head = _git("merge-base", "--is-ancestor", b, h)[0] == 0
    head_in_base = _git("merge-base", "--is-ancestor", h, b)[0] == 0
    rc, fork = _git("merge-base", b, h)
    if rc != 0:
        return ["  MEASURED   UNCHECKED -- the two branches share no history at all."]

    on_main = _git("merge-base", "--is-ancestor", fork, "origin/main")[0] == 0
    where = "which is on the main line" if on_main else "which is NOT on the main line"

    if base_in_head:
        rel = f"STACKED -- {head} contains {base}. Rebasing is meaningful here."
    elif head_in_base:
        rel = f"BEHIND -- {base} already contains {head}."
    else:
        rel = (
            f"SIBLINGS -- neither contains the other. They diverged at a shared "
            f"ancestor, {where}. Do NOT rebase one onto the other: it would "
            f"rewrite it onto a base it never had."
        )
    return [f"  MEASURED   {rel}"]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: pr_base_vs_ancestry.py <request-number>", file=sys.stderr)
        return 64
    pr = sys.argv[1]
    base, head = declared_base(pr)
    print(f"request {pr}: {head}")
    print(f"  DECLARED   aimed at {base} -- this is a field someone typed, not a measurement.")
    for line in ancestry(base, head):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
