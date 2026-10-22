#!/usr/bin/env bash
# Link a git worktree's .venv to the main checkout's, and refuse to finish unless Python
# is reachable through the link.
#
# 2026-10-12, Aria: two worktrees were given a .venv junction typed by hand with a doubled
# drive (C:\C:\DIVINE OS\...). A dangling junction reads as an empty directory, so the merge's
# test step failed with "tests could not be run" and looked like a test problem. The check
# below is the point: a link nobody has resolved is not yet a link.
#
# Usage: bash scripts/link_worktree_venv.sh <worktree-dir>
set -euo pipefail

wt="${1:?usage: link_worktree_venv.sh <worktree-dir>}"
[ -d "$wt" ] || { echo "no such worktree folder: $wt" >&2; exit 2; }

common="$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir)"
main_root="$(cd "$common/.." && pwd)"
target="$main_root/.venv"
python_rel="Scripts/python.exe"
[ -f "$target/$python_rel" ] || python_rel="bin/python"
[ -f "$target/$python_rel" ] || { echo "the main checkout has no usable .venv at $target" >&2; exit 3; }

link="$wt/.venv"
if [ -e "$link" ] && [ -f "$link/$python_rel" ]; then
    echo "already linked and Python resolves: $link"
    exit 0
fi
if [ -e "$link" ] || [ -L "$link" ]; then
    # A broken junction is removed as a link only; rmdir never touches what it points at.
    # `//c` is the idiom that survives path conversion; with MSYS_NO_PATHCONV set in
    # the caller's environment it reaches cmd as `//c` and nothing happens (2026-10-19:
    # the push gate failed six tests that passed alone, for exactly this reason).
    env -u MSYS_NO_PATHCONV cmd //c rmdir "$(cygpath -w "$link")" >/dev/null 2>&1 || {
        echo "$link exists but is not a removable link; look at it by hand" >&2
        exit 4
    }
fi

if command -v cygpath >/dev/null 2>&1; then
    env -u MSYS_NO_PATHCONV cmd //c mklink //J "$(cygpath -w "$link")" "$(cygpath -w "$target")" >/dev/null
else
    ln -s "$target" "$link"
fi

[ -f "$link/$python_rel" ] || { echo "linked, but Python does not resolve through $link" >&2; exit 5; }
echo "linked $link -> $target (Python resolves)"
