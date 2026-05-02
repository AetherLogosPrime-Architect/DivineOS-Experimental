#!/bin/bash
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
