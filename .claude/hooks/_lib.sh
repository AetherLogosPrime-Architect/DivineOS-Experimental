#!/bin/bash
# Shared helpers for .claude/hooks/*.sh — sourced, not executed.
#
# # Why this exists
#
# Round-1 audit (2026-05-07, external Claude) found the family-wrapper
# hook used `command -v python` to find the interpreter for its embedded
# divineos imports. On any shell where the project venv isn't
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

# 2026-07-08 quick-win per Aletheia's diagnostic: git rev-parse was
# being spawned as a subprocess on every call across find_divineos_python
# and is_bypass_command. Within a single hook process, once we have the
# repo root (or common-dir), it does not change — the hook does not
# navigate directories mid-run. Memoize in shell variables so the second
# and later callers within the same hook reuse the cached value. Each
# hook is still a separate process (cache does not survive across hooks
# — that is what the single-process consolidation will fix), but the
# quick-win takes the redundant calls out of the picture cheaply.
# 2026-08-20: derive the root from THIS FILE's own path before paying for
# git. _lib.sh always lives at <repo>/.claude/hooks/_lib.sh, so the root is
# two directories up -- a fact that does not need a subprocess to discover.
# git rev-parse cost ~39ms and ran on every hook, on every tool call.
#
# Verified, not assumed: the derived path is accepted only if it actually
# contains .claude/hooks/_lib.sh. If this file is ever moved, symlinked or
# vendored somewhere else, the check fails and git answers as before. A
# cheaper path that can be silently wrong is worse than the spawn -- that is
# the defect class this whole session has been about.
_LIB_REPO_ROOT_CACHE=""
_lib_repo_root() {
  if [ -z "$_LIB_REPO_ROOT_CACHE" ]; then
    local _self="${BASH_SOURCE[0]:-}"
    local _guess=""
    case "$_self" in
      */.claude/hooks/*) _guess="${_self%/.claude/hooks/*}" ;;
    esac
    if [ -n "$_guess" ] && [ -f "$_guess/.claude/hooks/_lib.sh" ]; then
      _LIB_REPO_ROOT_CACHE="$_guess"
    else
      _LIB_REPO_ROOT_CACHE="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
    fi
  fi
  printf '%s' "$_LIB_REPO_ROOT_CACHE"
}

_LIB_COMMON_DIR_CACHE=""
_lib_common_dir() {
  if [ -z "$_LIB_COMMON_DIR_CACHE" ]; then
    _LIB_COMMON_DIR_CACHE="$(git rev-parse --git-common-dir 2>/dev/null)"
  fi
  printf '%s' "$_LIB_COMMON_DIR_CACHE"
}

# 2026-07-22 (Andrew directive, council-3c78d69d71e8): hook-timing
# instrumentation. Every hook that sources _lib.sh automatically records
# a "start" and "end" line to ~/.divineos/hook_timing.jsonl. If a freeze
# happens mid-hook, the log will contain a start line with no matching
# end line (indexed by _HOOK_TIMING_ID). That is the stuck hook.
#
# Design choices:
#   - Fail-open: all I/O errors are silently discarded so timing cannot
#     break a hook.
#   - Millisecond precision when GNU date is available (%3N); falls back
#     to seconds*1000 on systems without.
#   - BASH_SOURCE[1] is the hook that sourced _lib.sh; [0] is _lib.sh
#     itself. Basename only, no full paths in the log.
#   - EXIT trap catches normal exit AND early-return / kill signals that
#     bash still delivers (not SIGKILL).
#
# Beer/Meadows/Popper walked. Four falsifier tests filed as follow-on.
#
# WHOSE ROW IS THIS? (Aria + Aether, 2026-08-18)
# Every window on this machine appends to one shared file, and until now no
# row could name the window it came from. `pid` is the pid of the individual
# hook process, not of the session — fifteen hooks dying together carry
# fifteen different pids, so grouping by it separates one hook from the next
# hook rather than one window from another.
#
# Aria hit the wall this makes: her orphan-burst query asks "did anything run
# again within ten seconds?" to tell a cancelled batch apart from a dead
# window. On a shared log that question cannot be answered, because the OTHER
# window's traffic papers straight over the silence of a window that died.
# Her census over-counted by roughly two orders of magnitude and she caught it
# before either of us shipped the number.
#
# `session` is the window's own id from the harness environment; `wpid` is the
# window process, distinct from the per-hook `pid` already recorded. Stamped
# on both phases rather than start-only, because the whole lesson of the day
# is a row that cannot say whose it is. Empty string when the harness supplies
# no id — an absence that is visible in the data rather than a missing key.
#
# Same defect, same day, in the token gauge: it read whichever transcript had
# the freshest mtime and answered a question about this session with another
# session's number. Two instruments, one blindness — neither knew how to ask
# whose.
_HOOK_TIMING_LOG="${HOME:-/tmp}/.divineos/hook_timing.jsonl"
_HOOK_TIMING_ID=""
_HOOK_TIMING_START_MS=""
_HOOK_TIMING_SESSION="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-}}"
_HOOK_TIMING_WPID="${CLAUDE_PID:-}"

# NO SPAWN ON THE COMMON PATH. Measured 2026-08-20, after Andrew reported
# freezing for seven minutes with the token count stuck: sourcing this file
# cost 207ms before a hook did any work, against a 25ms floor for bash
# itself, and 26 hooks pay it on EVERY tool call. Under real load each hook
# averaged ~2s and the stack summed to 40.8s typical / 73.8s p95 per call --
# minutes of dead screen across a multi-tool turn, and an interrupt that
# cannot land until the whole chain drains.
#
# `date` is an external process and this ran it twice per hook, start and
# end. $EPOCHREALTIME is a bash-5 builtin holding seconds.microseconds, so
# the common path now costs zero processes for the same millisecond output.
#
# The date fallback stays for bash 4 and for any shell where the builtin is
# unset. Removing a spawn must not quietly become removing the capability --
# that is the shape of half tonight's other defects.
_lib_hook_timing_ms() {
  local er="${EPOCHREALTIME:-}"
  case "$er" in
    *.*)
      local _s="${er%%.*}" _f="${er#*.}"
      printf '%s%s' "$_s" "${_f:0:3}"
      return
      ;;
  esac
  local ms
  ms="$(date +%s%3N 2>/dev/null)"
  case "$ms" in
    *N) date +%s000 2>/dev/null || printf '0' ;;
    "") printf '0' ;;
    *)  printf '%s' "$ms" ;;
  esac
}

_lib_hook_timing_start() {
  # BASH_SOURCE stack inside this function:
  #   [0] = _lib.sh (function definition file)
  #   [1] = _lib.sh (top-level of _lib.sh that called this function)
  #   [2] = the hook that did `source _lib.sh`
  # Fall back through the stack because the exact index can vary if
  # a hook wraps the source call.
  local hook_name
  hook_name="${BASH_SOURCE[2]:-${BASH_SOURCE[1]:-unknown}}"
  # Parameter expansion rather than basename: same result, no process. See
  # the spawn-removal note in _lib_log_liveness for the measurement.
  hook_name="${hook_name##*/}"
  hook_name="${hook_name:-unknown}"
  # If we ended up with _lib.sh itself (invoked directly for testing),
  # keep that — it identifies self-test runs.
  local start_ms
  start_ms="$(_lib_hook_timing_ms)"
  _HOOK_TIMING_ID="${hook_name}-$$-${start_ms}"
  _HOOK_TIMING_START_MS="$start_ms"
  # Parameter expansion, not $(dirname ...): this file is sourced by every
  # hook on every tool call, so a subprocess here is paid ~20 times per call.
  # The [ -d ] guard skips mkdir entirely once the directory exists, which is
  # every run after the first. Kept over main's unconditional dirname during
  # the 2026-08-22 merge for that reason -- same behaviour, no fork.
  local _tdir="${_HOOK_TIMING_LOG%/*}"
  [ -d "$_tdir" ] || mkdir -p "$_tdir" 2>/dev/null
  printf '{"id":"%s","hook":"%s","pid":%d,"session":"%s","wpid":"%s","phase":"start","ts_ms":%s}\n' \
    "$_HOOK_TIMING_ID" "$hook_name" "$$" \
    "$_HOOK_TIMING_SESSION" "$_HOOK_TIMING_WPID" "$start_ms" \
    >> "$_HOOK_TIMING_LOG" 2>/dev/null
}

_lib_hook_timing_end() {
  local exit_code=$?
  local end_ms
  end_ms="$(_lib_hook_timing_ms)"
  local duration_ms=$((end_ms - ${_HOOK_TIMING_START_MS:-$end_ms}))
  printf '{"id":"%s","session":"%s","wpid":"%s","phase":"end","exit_code":%d,"ts_ms":%s,"duration_ms":%d}\n' \
    "$_HOOK_TIMING_ID" "$_HOOK_TIMING_SESSION" "$_HOOK_TIMING_WPID" \
    "$exit_code" "$end_ms" "$duration_ms" \
    >> "$_HOOK_TIMING_LOG" 2>/dev/null
  return $exit_code
}

_lib_hook_timing_start
trap _lib_hook_timing_end EXIT

# F90 heartbeat is invoked at the END of this file — after
# _lib_log_liveness itself is defined. See end-of-file marker.

# F90 fix (Aletheia 2026-07-28): liveness-recording preamble as shared
# function so hooks stop silently going dark when their setup steps
# fail. Aletheia's finding: "every hook shipped from here carries [the
# silent fail-open pattern] until the template changes." One hook does
# it right (post-tool-use-emit-to-logbook.sh) and its inline
# _log_liveness pattern is what this generalizes.
#
# Usage after sourcing _lib.sh:
#   if ! find_divineos_python; then
#       _lib_log_liveness "python_resolve_failed" "extra=<...>"
#       exit 0
#   fi
#
# For failures BEFORE _lib.sh is sourced (cd, source itself), hooks
# should keep an inline mini-logger at the very top so the pre-source
# failure paths are also captured. Template comment for that pattern
# is in the docstring of post-tool-use-emit-to-logbook.sh.
_LIB_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"

_lib_log_liveness() {
  local _reason="${1:-unknown}"
  local _detail="${2:-}"
  local _hook_name
  _hook_name="${BASH_SOURCE[1]:-unknown}"
  # THREE SPAWNS REMOVED (2026-08-20). This function runs on every source of
  # _lib.sh -- so on every hook, on every tool call -- and it launched
  # basename, mkdir and date each time. Nine processes per tool call across
  # the 26 hooks, for one line of log. Parameter expansion, a -d test and a
  # printf builtin do the same work without leaving the shell.
  # fail-soft: an empty or odd path degrades to the literal string rather than breaking the log call
  _hook_name="${_hook_name##*/}"
  _hook_name="${_hook_name:-unknown}"
  local _dir="${_LIB_LIVENESS_LOG%/*}"
  # fail-soft: only pay for mkdir when the directory is actually absent; permissions failures fall through to the log write, which is itself fail-soft
  [ -d "$_dir" ] || mkdir -p "$_dir" 2>/dev/null || true
  local _ts
  # printf %(fmt)T is a bash-4.2 builtin; -1 means "now". The date fallback
  # stays for older shells -- dropping a spawn must not drop the capability.
  if ! printf -v _ts '%(%Y-%m-%dT%H:%M:%SZ)T' -1 2>/dev/null; then  # fail-soft: %(fmt)T is a bash>=4.2 builtin and errors loudly on older shells; the swallow keeps that noise out of hook stderr while the date fallback below supplies the same timestamp
    _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"  # fail-soft: if date is also unavailable the literal 'unknown' is written, because a liveness logger that crashes the hook would cause the outage it exists to report
  fi
  # fail-soft: liveness log write failures are informational only and must never block hook execution; loud-fail would defeat the purpose of a fallback-signal mechanism
  printf '{"ts":"%s","hook":"%s","reason":"%s","detail":"%s"}\n' "$_ts" "$_hook_name" "$_reason" "$_detail" >> "$_LIB_LIVENESS_LOG" 2>/dev/null || true
}

find_divineos_python() {
  local repo_root
  repo_root="$(_lib_repo_root)"
  # Side effect: prepend active worktree's src/ to PYTHONPATH so the
  # active source-of-truth wins over any stale editable install. See
  # the docstring's "Side effect" section for the bug this prevents.
  #
  # 2026-06-30 fix #1 (round-61d7311e03c7): use OS-specific PYTHONPATH
  # separator. Latent Windows bug, NOT the family-wrapper root cause.
  if [ -d "$repo_root/src" ]; then
    local _pp_sep=":"
    case "${OSTYPE:-}" in
      msys*|cygwin*|win*) _pp_sep=";" ;;
    esac
    export PYTHONPATH="$repo_root/src${PYTHONPATH:+${_pp_sep}${PYTHONPATH}}"
  fi
  # 2026-06-30 fix #2 (round-61d7311e03c7) — REAL root cause of the 11
  # family-wrapper test failures the push-readiness gate surfaced. On
  # Windows, the Microsoft Store python3 stub at
  # C:/Users/<u>/AppData/Local/Microsoft/WindowsApps/python3 is
  # executable + on PATH but NOT a real Python — running it prints
  # "Python was not found; run without arguments to install from the
  # Microsoft Store" and exits 49. find_divineos_python returned it
  # because temp worktrees have no .venv, every hook subprocess
  # failed, the seal hook emitted its fail-closed deny-JSON, and the
  # tests asserting allow-default saw deny instead. Two fixes both
  # required: (a) also check the parent repo's .venv via
  # --git-common-dir; (b) validate each candidate runs
  # `-c "import sys; sys.exit(0)"` before returning it.
  # TWO PASSES, so the common case pays for nothing it does not use.
  # 2026-08-20: --git-common-dir was spawned unconditionally, and so were both
  # `command -v` lookups, before the loop had a chance to find the venv sitting
  # in this very checkout -- which is where it is essentially every time. The
  # candidate order already said the local venv wins; the setup did not listen.
  #
  # Pass 1 is the local venv and costs no processes to assemble. Only if it
  # comes up empty do we pay for the worktree's parent repo and PATH lookups.
  # The ORDER of candidates is unchanged, so which interpreter wins is exactly
  # what it was -- this changes when the lookups happen, never their priority.
  local candidate
  for candidate in \
    "$repo_root/.venv/bin/python" \
    "$repo_root/.venv/Scripts/python.exe" \
    "$repo_root/venv/bin/python"
  do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      if "$candidate" -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
        echo "$candidate"
        return 0
      fi
    fi
  done

  local common_dir
  common_dir="$(_lib_common_dir)"
  local main_repo=""
  if [ -n "$common_dir" ] && [ -d "$common_dir" ]; then
    main_repo="$(dirname "$(cd "$common_dir" && pwd)")"
  fi
  for candidate in \
    "$main_repo/.venv/bin/python" \
    "$main_repo/.venv/Scripts/python.exe" \
    "$main_repo/venv/bin/python" \
    "$(command -v python3 2>/dev/null)" \
    "$(command -v python 2>/dev/null)"
  do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      # The validation used to be `import sys; sys.exit(0)` -- which proves an
      # interpreter STARTS and says nothing about which code it loads. Two
      # checkouts share one python install on this machine, so exactly one wins
      # the editable install, and a hook running the loser operates on the other
      # tree while reporting cleanly. That is the whole shape of 2026-08-13's
      # job two: check_test_cli_linkage printed "OK: 42 commands all register"
      # on every commit while comparing the OTHER repo's registrations.
      #
      # It happens to pick correctly today. The point is that it would not
      # notice if it stopped. A candidate is now accepted only if the divineos
      # it can see lives under THIS repo -- or if it cannot see one at all,
      # since plenty of hooks run pure-stdlib python and must keep working on a
      # machine with no install whatsoever.
      if "$candidate" -c "
import sys
try:
    import divineos
except Exception:
    sys.exit(0)          # no package visible: fine, stdlib-only hooks still run
import os.path
want = os.path.realpath(os.path.join(r'''$repo_root''', 'src'))
got = os.path.realpath(os.path.dirname(os.path.dirname(divineos.__file__)))
sys.exit(0 if got == want else 3)
" >/dev/null 2>&1; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  # F90 fix: log liveness on the fail-open path so a broken python
  # resolve becomes a visible marker, not a silent exit.
  _lib_log_liveness "python_resolve_failed" \
    "no viable python found; candidates checked: venv/system"
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
  repo_root="$(_lib_repo_root)"
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

# F90 heartbeat call (must be at end-of-file — after _lib_log_liveness
# is defined). Aletheia 2026-07-28: "the liveness mechanism cannot
# report its own absence." Logging on SUCCESS means an empty log is
# diagnostic (broken) rather than ambiguous. Runs on every successful
# source of _lib.sh, so per-hook heartbeats propagate automatically.
_lib_log_liveness "healthy_source" "hook sourced _lib.sh cleanly"
