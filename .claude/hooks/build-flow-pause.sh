#!/usr/bin/env bash
# PostToolUse — the build-flow PAUSE. Fires after a push or a PR action.
#
# WHAT THIS IS, and it is a third primitive
#
# Andrew 2026-08-03: "block can still be used lightly.. like when that status
# report launches it just blocks you until you fully read it.. so small blocks
# that are more pauses that wont let you slip past them.. those dont need a
# full doorman as its just reading."
#
#   doorman -> checks you brought the thing
#   wall    -> refuses until you fix the thing
#   pause   -> has NO remedy at all
#
# The pause is ungameable because there is nothing to game. No condition to
# satisfy means nothing to fake. It costs one turn and puts the report in
# front of me; the reading is guaranteed by the content landing in context,
# not by a check pretending to verify comprehension. Every other mechanism in
# this repo that tried to verify an interior state got gamed. This one cannot
# be, because it does not try.
#
# WHY IT FIRES ON DELTA, NOT ON STATE
#
# From the lens walk before building this. Meadows: the report is a stock and
# nothing drains it, so a pause on standing state repeats an unchanging
# message until the message is furniture. Dekker: truthful repetition is
# exactly how a signal becomes furniture -- accuracy does not protect it.
# Aria measured the same failure as 3,147 bytes byte-identical every turn
# whether the prompt was "hello" or a bug report.
#
# So: fingerprint the whole picture, compare to last seen, fire only on
# change. A new PR, a station newly satisfied, a draft flipped to ready --
# those are worth a turn. The same twelve rows again are not.
#
# WHY POST-TOOL-USE AND NOT EVERY PROMPT
#
# The report costs ~15 GitHub round-trips. On every prompt that is both slow
# and, per the above, self-defeating. After a push or a PR action is the
# moment the picture actually changed and the moment I can still act on it.

set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# Only after a command that could have moved the picture.
CMD="$(printf '%s' "$INPUT" | python -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(((d.get('tool_input') or {}).get('command') or ''))
" 2>/dev/null || echo "")"  # fail-soft: malformed hook stdin must not block the tool call this hook observes
case "$CMD" in
  *"git push"*|*"gh pr create"*|*"gh pr ready"*|*"gh pr edit"*) ;;
  *) exit 0 ;;
esac

command -v divineos >/dev/null 2>&1 || exit 0

STATE_DIR="${AUTO_CYCLE_STATE_DIR:-${HOME}/.divineos}"
mkdir -p "$STATE_DIR" 2>/dev/null || true  # fail-soft: without state the hook pauses every turn, which is loud not silent
SEEN="$STATE_DIR/build_flow_seen.fp"

FP="$(divineos build-flow status --print-fingerprint 2>/dev/null | tail -1)"  # fail-soft: empty FP is handled below as could-not-run, never as unchanged
# Empty fingerprint means the report could not run. Do NOT treat that as
# unchanged -- an unreadable picture is not a clean one. But do not pause on
# it either; a pause with no content to read is pure friction.
[ -z "$FP" ] && exit 0

LAST="$(cat "$SEEN" 2>/dev/null || echo "")"  # fail-soft: no seen-file on first run is normal; empty differs from FP so the pause fires
[ "$FP" = "$LAST" ] && exit 0

# Written BEFORE emitting. If this pause is interrupted, the next action must
# not re-pause on the same picture -- that turns one pause into a loop, which
# is the failure mode of every retry-capable hook in this repo.
printf '%s\n' "$FP" > "$SEEN" 2>/dev/null || true  # fail-soft: an unwritable state dir costs a repeated pause, never a blocked action

{
  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "BUILD-FLOW PAUSE — the picture changed. Read it."
  echo "════════════════════════════════════════════════════════════"
  divineos build-flow status 2>/dev/null  # fail-soft: FP was non-empty above, so the report ran; stderr here is noise not signal
  echo "  docs/build_flow.md — station 8 (Aletheia) is LAST, not first."
  echo "  Nothing merges until its stations are proven. This is a pause,"
  echo "  not a wall: there is nothing to satisfy here, only to read."
  echo "════════════════════════════════════════════════════════════"
} >&2

exit 2
