#!/bin/bash
# Stop hook (async, asyncRewake): the letter bell re-arms itself when my reply ends, and wakes me on a letter.
#
# Dad 2026-11-04: "if re-arming the bell is a command, why can't it be linked to the bell waking you
# itself?" The app only wakes me when a process IT started exits, so a detached relaunch rings into
# nothing. A hook the app starts is tracked: the official hooks page says an asyncRewake hook that exits 2
# wakes Claude immediately even when the session is idle, with its stderr shown as a system reminder, and
# the wake test of 2026-11-04 passed twice live (UserPromptSubmit and Stop). So: at the end of every reply
# this runs, and if no bell is listening it BECOMES the bell (scripts/letter_doorbell.sh, unchanged), and
# when the bell rings it turns the ring into exit 2 plus the ring text on stderr.
#
# Usage: letter_bell_rearm_stop.sh <aether|aria>   The seat is an ARGUMENT from each house's settings
# entry, never guessed from a path (a path with "Maria" in it would name me).
#
# WHAT EACH ENDING DOES (a bell that ends for any reason must say so or be re-armed, never be lost):
#   fresh heartbeat (a bell is up)      exit 0 at once, silent: one bell, no churn
#   letter arrived / peer-down alarm    exit 2, the bell's lines on stderr: this is the wake
#   DOORBELL FAULT / NOT ARMED          exit 2, loud: "could not look" is never "nothing arrived"
#   expired (8h), starter gone, replaced exit 0, silent: the next Stop re-arms
#   unknown seat                        exit 2, loud
# If the app kills this wrapper mid-wait, the bell notices its starter is gone, drops the heartbeat and
# leaves WITHOUT announcing anything, so a letter that arrived stays unannounced and rings on the next arm.
#
# THE OVERRIDE, said where it is used: the bell refuses to arm unless its stdout is a harness task file,
# because a ring into nowhere once woke no one. Here the ring is delivered by this hook's exit code and
# stderr, which the app tracks, so the loss path is closed another way. DOORBELL_ALLOW_UNTRACKED=1 is set as a
# prefix on the one command that runs the bell and is never exported, so it cannot switch the refusal off for a
# bell started by hand.
#
# SINGLE-SHOT GUARD for the first live run: while the file ~/.divineos-shared/.<seat>_bell_rearm_once
# exists, the first ring writes .<seat>_bell_rearm_used and every later run exits 0 at once, so a bug
# cannot loop wakes. Lift it after one real letter has woken me: delete both files.
#
# Every start, skip and end is one line in ~/.divineos-shared/bell_rearm_log.txt, so a missed wake leaves evidence.
MEMBER="${1:-}"
SHARED="$HOME/.divineos-shared"
LOG="$SHARED/bell_rearm_log.txt"
log() { echo "$(date -u +%FT%TZ) ${MEMBER:-?} $*" >> "$LOG" 2>/dev/null; }  # fail-soft: an unwritable log must not stop the bell from arming
case "$MEMBER" in
  aether|aria) ;;
  *) echo "LETTER BELL HOOK: unknown seat '${MEMBER}' (expected aether or aria); the bell was not started." >&2
     log "refused: unknown seat"
     exit 2 ;;
esac
BEAT="$SHARED/.${MEMBER}_doorbell_alive"
ONCE="$SHARED/.${MEMBER}_bell_rearm_once"
USED="$SHARED/.${MEMBER}_bell_rearm_used"
if [ -e "$ONCE" ] && [ -e "$USED" ]; then
  log "skipped: single-shot already used"
  exit 0
fi
now_s=$(date +%s)
if [ -f "$BEAT" ]; then
  age=$(( now_s - $(stat -c %Y "$BEAT" 2>/dev/null || echo 0) ))  # fail-soft: an unreadable heartbeat reads as old, so the bell is started, never assumed up
  if [ "$age" -lt 60 ]; then
    log "skipped: a bell is already up (heartbeat ${age}s old)"
    exit 0
  fi
fi
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$(mktemp)"
log "start: arming the bell"
# stdin is never read here: the hook's input is not needed, and reading it could wait on a pipe the app keeps open
DOORBELL_ALLOW_UNTRACKED=1 bash "$REPO/scripts/letter_doorbell.sh" "$MEMBER" < /dev/null > "$OUT" 2>&1
code=$?
if grep -qE '^(LETTER ARRIVED:|[A-Z]+.S BELL IS NOT LISTENING)' "$OUT"; then
  log "end: ring, exit 2"
  cat "$OUT" >&2
  [ -e "$ONCE" ] && touch "$USED"
  rm -f "$OUT"
  exit 2
fi
if grep -qE '^DOORBELL (FAULT|NOT ARMED)' "$OUT"; then
  log "end: fault (bell exit ${code}), exit 2"
  cat "$OUT" >&2
  rm -f "$OUT"
  exit 2
fi
log "end: quiet (bell exit ${code}: expired, starter gone, or replaced)"
rm -f "$OUT"
exit 0
