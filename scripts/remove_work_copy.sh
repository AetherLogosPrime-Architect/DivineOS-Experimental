#!/usr/bin/env bash
# Remove a git work copy safely. One implementation: src/divineos/core/work_copy_sweep.py
# (links are unlinked first, work that exists nowhere else is refused, --snapshot keeps it in
# refs/rescue/<name>, the main checkout is never removed). This wrapper only finds a working Python.
#
# 2026-10-20, Aria: `git worktree remove --force` on work copies whose .venv was a junction to the
# main checkout's real .venv emptied that real venv. Git walks the link. Aether's cold read of #698
# asked for one implementation, not a second copy in shell, and for the house's resolver rather than a
# bare `python`, which on Windows can be the Microsoft Store stub; see the resolver below.
#
# Usage: bash scripts/remove_work_copy.sh <work-copy-dir> [--snapshot]
# Exit: 0 removed; 2 anything else; 3 the main checkout; 4 holds work that exists nowhere else; 5 snapshot failed.
# No `set -e`: the resolver below tries candidates that are allowed to fail, and the one command that
# matters is the last, which is exec'd, so its exit status is this script's.

here="$(cd "$(dirname "$0")" && pwd)"
# The house resolver (find_divineos_python in .claude/hooks/_lib.sh) answered "none" for this call shape
# when run from the test suite, so this carries the part of it that matters, in order: this repository's
# .venv, the main checkout's .venv (a linked work copy has none of its own), then python3 and python.
# Every candidate must run, which is what skips the Windows Store stub that exists, is executable, and is
# not a Python.
main_repo="$(cd "$(git -C "$here" rev-parse --path-format=absolute --git-common-dir)/.." 2>/dev/null && pwd)"
PY=""
for candidate in "$here/../.venv/Scripts/python.exe" "$here/../.venv/bin/python" \
                 "$main_repo/.venv/Scripts/python.exe" "$main_repo/.venv/bin/python" \
                 "$(command -v python3 2>/dev/null)" "$(command -v python 2>/dev/null)"; do
    [ -n "$candidate" ] && [ -x "$candidate" ] || continue
    if "$candidate" -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then PY="$candidate"; break; fi
done
[ -n "$PY" ] || { echo "no working Python found" >&2; exit 2; }
# PYTHONPATH is written in the form the Python will read. A native Windows Python reads `;`-separated
# Windows paths, and a list that mixes an MSYS path with an inherited Windows-style entry (the push gate
# sets one) is mangled by the shell's conversion, so Python silently imported the OLD copy of the
# package from the main checkout: "No module named divineos.core.work_copy_sweep" (found 2026-10-20).
src="$here/../src"
sep=":"
if command -v cygpath >/dev/null 2>&1; then src="$(cygpath -w "$src")"; sep=";"; fi
PYTHONPATH="$src${PYTHONPATH:+$sep$PYTHONPATH}" exec "$PY" -m divineos.core.work_copy_sweep remove "$@"
