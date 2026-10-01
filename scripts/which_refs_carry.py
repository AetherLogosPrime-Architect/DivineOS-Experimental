"""Which branches carry this file? Three honest answers, never two.

    python scripts/which_refs_carry.py <path> [<ref> ...]

With no refs, asks every remote branch plus HEAD. For each ref it prints one of:

    carries        the path exists at that ref
    does not       git read the ref and the path is not in it
    could not look git could not answer (the ref is unknown, the repo is
                   unreadable) -- which is NOT evidence the file is absent

WHY A TOOL AND NOT A ONE-LINER (prereg-2a5427d47ff8). The one-liner everyone
reaches for is ``git cat-file -e "origin/x:.claude/y"`` in a shell loop, and on
Windows the shell rewrites exactly that argument -- a slashed ref, a colon, a
dot-path -- into ``origin\\x;.claude\\y`` before git sees it. With stderr
discarded, the loop then reports every branch as missing the file. That happened
four times between 2026-08-31 and 2026-09-23. This asks git through a list of
arguments with no shell in between, so nothing can be rewritten, and it keeps
could-not-look apart from does-not.

THE CONTROL. Before any verdict it looks the path up at the first ref that
should have it, if one was named with --control; without one it proves only that
git answers at all, by asking for HEAD. A tool that cannot find a known positive
has no business printing negatives, so it stops instead.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

CARRIES = "carries"
DOES_NOT = "does not"
COULD_NOT = "could not look"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def verdict(ref: str, path: str) -> str:
    """One of the three answers for one ref.

    ``git cat-file -e`` exits non-zero both when the path is absent and when the
    ref cannot be read, so the ref is resolved first: a ref that does not
    resolve is could-not-look, and only a readable ref missing the path is
    does-not.
    """
    if _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        return COULD_NOT
    return CARRIES if _git("cat-file", "-e", f"{ref}:{path}").returncode == 0 else DOES_NOT


def remote_refs() -> list[str]:
    proc = _git("for-each-ref", "--format=%(refname:short)", "refs/remotes")
    if proc.returncode != 0:
        return []
    return [r for r in proc.stdout.split() if r and not r.endswith("/HEAD") and "/" in r]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Which branches carry this file?")
    parser.add_argument("path")
    parser.add_argument("refs", nargs="*")
    parser.add_argument("--control", help="a ref known to carry the path, checked first")
    args = parser.parse_args(argv)

    path = args.path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]

    if args.control:
        if verdict(args.control, path) != CARRIES:
            print(
                f"CONTROL FAILED: {args.control} was named as carrying {path} and this "
                "could not find it there. No verdicts printed -- an instrument that "
                "misses a known positive has nothing to say about the negatives.",
                file=sys.stderr,
            )
            return 2
    elif verdict("HEAD", ".") == COULD_NOT and _git("rev-parse", "HEAD").returncode != 0:
        print("CONTROL FAILED: git could not read HEAD here.", file=sys.stderr)
        return 2

    refs = args.refs or ["HEAD", *remote_refs()]
    width = max(len(r) for r in refs)
    counts = {CARRIES: 0, DOES_NOT: 0, COULD_NOT: 0}
    for ref in refs:
        v = verdict(ref, path)
        counts[v] += 1
        print(f"  {ref:<{width}}  {v}")
    print(
        f"\n{path}: carried by {counts[CARRIES]}, absent from {counts[DOES_NOT]}, "
        f"could not look at {counts[COULD_NOT]}"
        + ("" if args.control else "  (no --control given: only 'git answers' was proven)")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
