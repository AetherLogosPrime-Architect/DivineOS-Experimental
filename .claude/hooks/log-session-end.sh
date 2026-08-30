#!/bin/bash
# Observability only (2026-08-03). Sourcing _lib.sh registers this script in
# ~/.divineos/hook_timing.jsonl so the firing map can see it. Before this, 16
# of 96 hooks were INVISIBLE rather than idle -- they could be running fine and
# nothing outside could tell, which made "silent" and "healthy" the same
# reading. No behaviour change: `|| true` means a missing toolbox leaves this
# script exactly as it was. Observability must never become a new way for a
# guard to die.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true
# Claude Code Stop hook — fires at the end of every assistant turn.
#
# This hook used to call `divineos extract` (formerly `divineos emit SESSION_END`)
# unconditionally. That was wrong: Stop fires per-turn, not per-session, so
# extraction ran every turn and reset session_start each time. The session
# analyzer then only ever saw records after the last reset — the root cause
# of the "1 message, 12 tool calls" bug on 2026-04-20.
#
# Consolidation is now triggered by (in priority order):
#   1. Write-count threshold (40 writes since last consolidation) checked by
#      the PostToolUse hook — fires when enough meaningful work has accumulated.
#   2. Post-sleep auto-extract — `divineos sleep` calls extract after phase 6
#      so creative recombinations land in knowledge.
#   3. Explicit user call (`divineos extract`).
#   4. PreCompact hook — still fires `divineos extract` right before context
#      gets compacted, because that IS a genuine "save now or lose it" moment.
#
# The Stop hook no longer participates. Keeping the file (not deleting) so
# settings.json still wires to something; it just no-ops.
#
# See PR #2 (consolidate-retrigger) for the full change and pre-registered
# review criteria.

exit 0
