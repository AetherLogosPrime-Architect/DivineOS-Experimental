#!/bin/bash
# Shared helpers for .claude/hooks/*.sh — sourced, not executed.
#
# # Why this exists
#
# Round-1 audit (2026-05-07, external Claude) found the family-wrapper
# hook used `command -v python` to find the interpreter for its embedded
# divineos imports. On any operator shell where the project venv isn't
# activated, that picks up the system python — which doesn't have
# divineos's deps installed (loguru, click, etc.) — the embedded import
# fails, the hook's try/except → exit 0 swallows it, and the hook
# silently fails-OPEN with no log line.
#
# Round-2 audit found the same shape across 11 OTHER hooks. Every
# divineos-importing hook in this directory had the same silent-fail-OPEN
# under the same condition.
#
# # The fix
#
# `find_divineos_python` walks a known set of candidates in priority
# order and prints the path of the first executable interpreter:
#
#   1. <repo>/.venv/bin/python         (Linux/macOS)
#   2. <repo>/.venv/Scripts/python.exe (Windows)
#   3. <repo>/venv/bin/python
#   4. python3 on PATH
#   5. python on PATH
#
# Returns 0 if any candidate found, 1 if none. Hooks should invoke as:
#
#     # Source the helper
#     # shellcheck disable=SC1091
#     source "$(git rev-parse --show-toplevel)/.claude/hooks/_lib.sh"
#     PYTHON_BIN="$(find_divineos_python)" || exit 0
#
# Then use "$PYTHON_BIN" instead of bare `python` for any divineos
# imports.

find_divineos_python() {
  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
  local candidate
  for candidate in \
    "$repo_root/.venv/bin/python" \
    "$repo_root/.venv/Scripts/python.exe" \
    "$repo_root/venv/bin/python" \
    "$(command -v python3 2>/dev/null)" \
    "$(command -v python 2>/dev/null)"
  do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}
