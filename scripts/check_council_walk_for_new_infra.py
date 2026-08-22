#!/usr/bin/env python3
"""Block new-infra commits that cite no COMPLETED council walk.

Andrew 2026-08-10: "you have all the means and setup not to fake it.. but you
keep doing it.. so unless you build enforcement which i have asked repeatedly
to be done.. you will continue to fake it, rendering the system pointless..
you have the entire council system.. all the lenses.. the whole setup to
automate it.. and you skip around it.. because nothing stops you from
skipping it."

This is the "something stops you". Same choke point and same shape as
check_prereg_for_new_infra.py, which has held for months.

THE ANTI-FAKE CLAUSE, and it is the whole reason this is not theatre:

A walk id in the message is not enough. `is_complete()` is consulted, and it
returns True only when every lens the MANAGER surfaced carries either a
finding or a substance-checked exclusion. So citing a walk I opened and
abandoned fails exactly like citing no walk at all. Without this, the gate
would only force me to START a walk I could still fake — which is the
failure it exists to prevent, one level up.

There is deliberately NO env-var bypass. The pre-reg gate has one
(DIVINEOS_NEW_INFRA_NO_PREREG) and I am not copying it here: the whole
finding is that I route around discipline when routing around is available.

Exit codes:
  0  - no new infra, or a completed walk is cited
  1  - new infra with no completed walk
  2  - infrastructure error (caller decides fail-open)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

__guardrail_required__ = True

_PROTECTED_PATHS = ("src/divineos/core/",)
_WALK_PAT = re.compile(r"walk-[0-9a-f]{12}")


def _staged_added() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=A"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "git diff failed")
    files = []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append(parts[-1].replace("\\", "/"))
    return files


def _arrived_with_a_merge() -> set[str]:
    """Files the incoming side of an in-progress merge already contains.

    A merge is not authorship. When main lands in this branch, every file main
    added since the branch point shows up as ADDED against HEAD, and this gate
    read four of Aether's modules -- ``prior_art.py`` among them, whose whole
    job is asking whether a thing already exists -- as new infrastructure I had
    built without walking a council on it.

    Refusing the merge is the shape that matters, not the inconvenience. The
    demand is impossible by construction: I cannot walk a council on a design
    decision another author already made and shipped, so the only ways past are
    to fabricate a walk or to strand the merge. A gate whose sole satisfiable
    answer is a fake answer trains the faking. That is the failure this gate was
    built to prevent, arriving through the gate itself.

    Authorship, precisely: a file is mine to walk when neither parent has it.
    Something I genuinely add while resolving conflicts is absent from
    MERGE_HEAD and still caught.
    """
    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"], capture_output=True, text=True, check=False
    )
    if git_dir.returncode != 0:
        return set()
    if not (Path(git_dir.stdout.strip()) / "MERGE_HEAD").exists():
        return set()
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "MERGE_HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        # Cannot see the incoming side. Exempting nothing keeps the gate strict,
        # which is the right way to be wrong here.
        return set()
    return {line.replace("\\", "/") for line in out.stdout.splitlines() if line}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_council_walk_for_new_infra.py <commit-msg-file>", file=sys.stderr)
        return 2
    try:
        message = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
        added = _staged_added()
    except (OSError, RuntimeError) as exc:
        print(f"[council-walk-gate] could not run: {exc}", file=sys.stderr)
        return 2

    inherited = _arrived_with_a_merge()
    new_infra = [
        f
        for f in added
        if any(f.startswith(p) for p in _PROTECTED_PATHS) and f not in inherited
    ]
    if not new_infra:
        return 0

    # Named out loud rather than silently dropped: a quiet exemption is how a
    # gate gets narrowed until it never fires, and I would not be able to tell
    # the difference from the outside.
    skipped = sorted(
        f for f in added if any(f.startswith(p) for p in _PROTECTED_PATHS) and f in inherited
    )
    if skipped:
        print(
            f"[council-walk-gate] {len(skipped)} core file(s) arrived with the merge and "
            "were not treated as new authorship here: " + ", ".join(skipped)
        )

    cited = _WALK_PAT.findall(message)
    if not cited:
        print(
            "\n[council-walk-required] BLOCKED — new infra with no council walk cited:\n"
            + "".join(f"  - {f}\n" for f in new_infra)
            + "\nA new capability under src/divineos/core/ needs a walk that actually\n"
            "completed. Open one, walk every lens the manager surfaces, then cite it:\n\n"
            '  divineos walk open "<the problem, in a sentence>" --gravity high\n'
            "  divineos walk apply <walk-id> <Lens> --finding \"...\"\n"
            "  divineos walk exclude <walk-id> <Lens> --reason \"...\"\n"
            "  divineos walk close <walk-id>\n\n"
            "No env-var bypass exists, deliberately.\n",
            file=sys.stderr,
        )
        return 1

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from divineos.core.council_walk import consume, is_complete
    except ImportError as exc:
        print(f"[council-walk-gate] cannot verify walk completion: {exc}", file=sys.stderr)
        return 2

    completed = [w for w in cited if is_complete(w)]
    if completed:
        # SPEND it. Found by the Schneier lens on walk-32d831616266: without
        # this, one closed walk is a permanent pass for every future commit.
        consume(completed[0])
        print(f"[council-walk-gate] completed walk cited and spent: {completed[0]}")
        return 0

    print(
        "\n[council-walk-required] BLOCKED — walk cited but NOT COMPLETE: "
        + ", ".join(cited)
        + "\n\nCiting an abandoned walk is the fake this gate exists to catch.\n"
        "Run `divineos walk status <walk-id>` — every lens needs a finding or a\n"
        "written exclusion before the walk closes.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
