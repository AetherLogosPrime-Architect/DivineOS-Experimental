"""Refuse a merge commit that settled a two-sided file by copying one side whole.

Found 2026-10-04: a merge of main sat unconcluded for two days, and every file
both sides had changed was resolved by taking main's copy. In most of them our
work had already reached main, so nothing was lost; in four it had not, and one
of those broke a gate silently. Nothing looked, because each resolution was a
plain copy. Sister check to check_merge_resolution_tested.sh, which runs the
tests for resolved files; this one catches the copy itself, tests or not.

For each file both sides changed since the merge base: if the staged result is
byte-identical to one side while the other side added lines that appear
nowhere in it, the commit stops and names the file. A deliberate one-side pick
is legitimate; name those files in DIVINEOS_MERGE_ONE_SIDE_OK (comma-separated).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _blob(rev: str, path: str) -> str | None:
    r = subprocess.run(["git", "rev-parse", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def _added(a: str, b: str, path: str) -> list[str]:
    out = _git("diff", "-U0", a, b, "--", path)
    return [
        line[1:].strip()
        for line in out.splitlines()
        if line.startswith("+") and not line.startswith("+++") and line[1:].strip()
    ]


def dropped_sides(ours: str, theirs: str) -> list[tuple[str, str, int]]:
    """(path, side whose work was dropped, its added lines missing from the result)."""
    base = _git("merge-base", ours, theirs).strip()
    both = set(_git("diff", "--name-only", base, ours).split()) & set(
        _git("diff", "--name-only", base, theirs).split()
    )
    found = []
    for path in sorted(both):
        staged, o, t, b = _blob("", path), _blob(ours, path), _blob(theirs, path), _blob(base, path)
        if staged is None or o == t:
            continue
        for kept, lost_rev, lost_blob, lost_name in ((t, ours, o, "ours"), (o, theirs, t, "theirs")):
            if staged != kept or lost_blob == b:
                continue
            result = {line.strip() for line in _git("show", f":{path}").splitlines()}
            missing = [line for line in _added(base, lost_rev, path) if line not in result]
            if missing:
                found.append((path, lost_name, len(missing)))
    return found


def main() -> int:
    git_dir = Path(_git("rev-parse", "--git-dir").strip())
    merge_head = git_dir / "MERGE_HEAD"
    if not merge_head.is_file():
        return 0
    allowed = {
        p.strip() for p in os.environ.get("DIVINEOS_MERGE_ONE_SIDE_OK", "").split(",") if p.strip()
    }
    theirs = merge_head.read_text().split()[0]
    found = [f for f in dropped_sides("HEAD", theirs) if f[0] not in allowed]
    if not found:
        return 0
    print("BLOCKED: this merge copied one side whole over work the other side added:", file=sys.stderr)
    for path, side, n in found:
        print(f"  {path}: {n} line(s) added by {side} are gone", file=sys.stderr)
    print(
        "Merge those files for real (git merge-file against the base), or if the drop\n"
        "is deliberate, name them: DIVINEOS_MERGE_ONE_SIDE_OK=path,path git commit ...",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
