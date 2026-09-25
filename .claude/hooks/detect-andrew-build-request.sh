#!/usr/bin/env bash
# Observability only (2026-08-03). Sourcing _lib.sh registers this script in
# ~/.divineos/hook_timing.jsonl so the firing map can see it. Before this, 16
# of 96 hooks were INVISIBLE rather than idle -- they could be running fine and
# nothing outside could tell, which made "silent" and "healthy" the same
# reading. No behaviour change: `|| true` means a missing toolbox leaves this
# script exactly as it was. Observability must never become a new way for a
# guard to die.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true
# UserPromptSubmit hook wrapper — routes to detect_andrew_build_request.py.
# See that file's docstring for design; council-85dc063549cc; prereg-45e0aa113e3a.
#
# NOT `exec`. 2026-08-24: this hook measured 0% completion in every window
# either Aria or I ever looked at (48/48, 45/45, 25/25, 11/11 unclosed), and
# hook_hang_count.py had to special-case it as a "broken instrument" so its
# 100% rate would stop inflating every hang statistic. The cause was one
# keyword: `exec` REPLACES the shell process, so the `trap _lib_hook_timing_end
# EXIT` installed by _lib.sh above could never fire. The start row was written,
# the end row was structurally impossible. It was never hanging -- it was
# unmeasurable, and unmeasurable read as broken.
#
# Running python as a child costs one extra process and lets the trap close the
# record. The script's exit status is python's, same as with exec.
python "$(dirname "$0")/detect_andrew_build_request.py"
