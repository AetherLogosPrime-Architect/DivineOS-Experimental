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
#
# ## Side effect: PYTHONPATH prepend
#
# Aether 2026-05-19: silent-stale-substrate bug — when `pip install -e`
# was last run from a DIFFERENT worktree, every hook in every other
# worktree silently imports the egg-link'd stale source. Changes made
# in the active worktree are invisible to its own hooks until someone
# remembers to manually re-install. The lepos-channel gate (commit
# 5951593) sat inert for an entire session because of this.
#
# Fix: `find_divineos_python` also exports PYTHONPATH=$repo_root/src:
# $PYTHONPATH as a side effect. The active worktree's src/ takes
# precedence over any installed copy. Each worktree's hooks now reflect
# its own state. Prevents the entire class.

find_divineos_python() {
  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
  # Side effect: prepend active worktree's src/ to PYTHONPATH so the
  # active source-of-truth wins over any stale editable install. See
  # the docstring's "Side effect" section for the bug this prevents.
  if [ -d "$repo_root/src" ]; then
    export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"
  fi
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


# is_bypass_command — return 0 if the given command matches a
# documented bypass prefix in scripts/hook_bypass_commands.txt.
# Closes the locked-box gate trap (task #98) by giving every
# PreToolUse Bash hook the same view of which commands are the
# gate-system's documented escape routes.
#
# Before this helper, the bypass-list lived only inside
# pre_tool_use_gate.py. Outer hooks (require-ear-armed.sh,
# require-briefing.sh, etc.) didn't share that list, so a turn that
# ran a documented bypass command got past pre_tool_use_gate.py but
# got blocked by an outer hook that didn't know the command was
# supposed to be unblockable. Operator had to grant env-var bypass
# tonight to escape that trap.
#
# Council walk consult-ba0fc4337e51 (Dekker + Lamport): the trap
# emerged from accretion. Bypass-list-sharing wasn't a pattern at
# the time the earlier hooks shipped. Single source of truth fixes
# the drift-into-failure shape.
#
# Usage from a hook:
#   COMMAND=$(extract from stdin JSON)
#   if is_bypass_command "$COMMAND"; then exit 0; fi
#
# Splits the command on shell separators (&&, ;, |, newline) and
# returns 0 if ANY segment starts with a documented bypass prefix
# after trimming whitespace.
is_bypass_command() {
  local cmd="$1"
  [ -z "$cmd" ] && return 1
  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
  local bypass_file="$repo_root/scripts/hook_bypass_commands.txt"
  [ -f "$bypass_file" ] || return 1
  # Split the command on shell separators into segments.
  # IFS-based split would mangle the command; use sed for predictable
  # multi-separator splitting.
  local segments
  segments=$(printf '%s' "$cmd" | sed -e 's/&&/\n/g; s/;/\n/g; s/|/\n/g')
  local seg trimmed prefix
  while IFS= read -r seg; do
    trimmed="${seg#"${seg%%[![:space:]]*}"}"
    [ -z "$trimmed" ] && continue
    while IFS= read -r prefix; do
      # Skip comments and empty lines
      case "$prefix" in
        ''|'#'*) continue ;;
      esac
      case "$trimmed" in
        "$prefix"|"$prefix "*) return 0 ;;
      esac
    done < "$bypass_file"
  done <<< "$segments"
  return 1
}


# extract_tool_command — read the Claude Code PreToolUse hook input
# JSON from stdin and print the tool's bash command (empty if not
# applicable). Hooks that need to inspect the about-to-run command
# can call this once instead of duplicating the json-parsing dance.
#
# Pipe pattern:
#   INPUT=$(cat)
#   COMMAND=$(printf '%s' "$INPUT" | extract_tool_command)
extract_tool_command() {
  local py
  py="$(find_divineos_python)" || return 1
  "$py" -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
    print((data.get('tool_input') or {}).get('command', ''))
except Exception:
    pass
" 2>/dev/null
}
