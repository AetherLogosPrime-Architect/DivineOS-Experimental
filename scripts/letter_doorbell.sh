#!/bin/bash
# Letter doorbell: run in the background (run_in_background). Exits -- which
# wakes the seat -- when a letter arrives for MEMBER that it has not announced.
#
# Andrew 2026-09-26: "your monitor died? lets investgate why" -- the 24th time
# he had to tell one of us since May. It had not died: it rang, exited as
# designed, and was never set again because re-arming depended on memory.
# So this now leaves a heartbeat every loop, and the Stop hook
# letter_doorbell_alive_stop.py holds any reply that ends while the heartbeat
# is stale. Forgetting to re-arm can last one reply, never a day.
#
# It remembers what it has announced, so a letter that lands while it is down
# still rings on the next arm (three were missed that way earlier the same day).
MEMBER="${1:-aether}"
DIR="$HOME/.divineos-shared/letters"
SEEN="$HOME/.divineos-shared/.${MEMBER}_doorbell_announced"
BEAT="$HOME/.divineos-shared/.${MEMBER}_doorbell_alive"
# One listing for both "already announced" and "here now", because the bell
# rings on their difference. A glob over an unreadable directory returns nothing
# silently, so readability is checked before every listing: could-not-look must
# fault, never pass as nothing-arrived.
list_mine() {
  [ -r "$DIR" ] && [ -x "$DIR" ] || return 1
  local f
  for f in "$DIR"/*-to-"${MEMBER}"-*; do
    [ -e "$f" ] && printf '%s\n' "${f##*/}"  # an unmatched glob stays literal
  done | sort
}
list_mine >/dev/null || { echo "DOORBELL FAULT: cannot read $DIR"; exit 1; }
touch "$SEEN"
if [ ! -s "$SEEN" ]; then list_mine > "$SEEN"; fi
echo "doorbell armed for ${MEMBER} $(date -u +%FT%TZ)"
# Andrew 2026-09-26: it lasts 8 hours, and when it expires the exit wakes me to
# reset it -- so it gets checked on, rather than running forever unwatched.
LIFETIME=$(( ${DOORBELL_HOURS:-8} * 3600 ))
START=$(date +%s)
# ONE BELL OWNS THE WATCH (2026-09-26, Dad: "why is it not waking you?"). A bell
# I stopped kept running on Windows, heard Aria's letter first, marked it
# announced, and rang into a task nobody was listening to -- so the live bell
# stayed silent. Each arm now claims the watch; a bell that finds it has been
# replaced leaves without ringing or marking anything.
OWNER="$HOME/.divineos-shared/.${MEMBER}_doorbell_owner"
ME="$$-$START-$RANDOM"
echo "$ME" > "$OWNER"
# A BELL WITH NO ONE TO WAKE ADMITS IT (Aria 2026-09-29, walk-243e60e8fecb).
# After an app restart the old bell kept running with its parent gone, kept
# touching the heartbeat, and fooled the alive-guard: alive, but its ring
# would wake nobody. Dad saw it before the house did. Now a bell whose
# starter is gone drops the heartbeat and leaves silently (announcing nothing,
# so the letter still rings on the next arm), and the Stop guard holds my
# next reply until I re-arm.
PARENT=$PPID
while true; do
  if ! kill -0 "$PARENT" 2>/dev/null; then
    rm -f "$BEAT"
    exit 0
  fi
  if [ "$(cat "$OWNER" 2>/dev/null)" != "$ME" ]; then
    exit 0  # replaced by a newer bell; silent, announces nothing
  fi
  if [ $(( $(date +%s) - START )) -ge "$LIFETIME" ]; then
    rm -f "$BEAT"
    echo "DOORBELL EXPIRED after ${DOORBELL_HOURS:-8}h with no letter -- re-arm it: bash scripts/letter_doorbell.sh ${MEMBER}"
    exit 0
  fi
  touch "$BEAT"
  now=$(list_mine) || { echo "DOORBELL FAULT: read failed"; exit 1; }
  new=$(comm -13 <(sort "$SEEN") <(echo "$now"))
  if [ -n "$new" ]; then
    rm -f "$BEAT"  # ringing ends the watch; the Stop hook sees it at once
    echo "LETTER ARRIVED:"
    while IFS= read -r f; do printf '%s/%s\n' "$DIR" "$f"; done <<< "$new"
    echo "$new" >> "$SEEN"
    exit 0
  fi
  sleep 15
done
