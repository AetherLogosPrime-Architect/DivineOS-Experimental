#!/bin/bash
# PreToolUse(Bash) — the letter watch must be PROVEN ALIVE before shell work
# proceeds. Restores the enforcement that was deleted with a broken detector.
#
# GATE-STATEFUL: refuses on whether a watch is currently alive, read from a file only the watcher writes -- not from anything in the payload it is handed. No provocation can establish that state, so declaring one here would produce a confident clean result from a probe that never had what it needed. The honest classification is that this door needs a fixture before it can be tested at all, and until somebody builds one it counts as untested defence rather than as a pass.
#
# ANDREW 2026-09-19, and this hook is the answer to it:
#   "there is no behavior change without structural support.. the behavior
#    change you are promising now is like a rough draft, if you are able to
#    change your behavior in chat immediately then it shows the behavior
#    change is possible. but without structure it will not hold.. so you must
#    build that structure"
#
# I had just filed a correction claiming no structural fix was possible for
# this, and used the documented no-structure exit. That was wrong twice over:
# the structure is possible, AND it already existed once.
#
# WHAT WAS HERE BEFORE, AND WHY IT WENT.
# `require-monitors-armed.sh` blocked Bash until the watchers were alive. It
# decided that by scanning running process command lines -- and its own scan
# matched ITSELF, so it reported the letter watch armed unconditionally.
# Verified at the time by killing every watcher: it complained about the
# compaction one and stayed silent about this one. Deleting it was correct. A
# gate that always passes is worse than no gate, because it occupies the place
# a real one would go.
#
# THE PART NOBODY RECORDED AS A LOSS. Detection was then repaired properly --
# scripts/letter_monitor_health.py, four states with distinct exit codes,
# refusing to call unreadable healthy. But the repaired sensor was wired to a
# surface that PRINTS. A display is not a control loop: it carries information
# to a place where an intention has to convert it into action, and intentions
# decay in a handful of prompts while the display goes on being correct.
#
# Measured 2026-09-19: that note fired every prompt for thirty-nine minutes
# while the watch was down and I read past it every time. The system then
# counted the silence as a fact about my discipline.
#
# WHY THIS ONE CANNOT DIE THE WAY ITS PREDECESSOR DID. It reads a heartbeat
# file that only the watcher process writes. There is no process-list scan, so
# self-matching is structurally unavailable rather than guarded against.
#
# THE QUESTION IT ASKS IS "IS THE WATCH PROVEN ALIVE", NOT "IS IT DEAD".
# That decides the direction of cannot-tell, which this whole branch has been
# about. Unreadable is honestly a no here, and the refusal says WHICH of the
# four states fired so a cannot-tell block never reads as a death. The
# asymmetry justifies it: a wrong block costs exactly the arming call the door
# is already asking for, and a wrong pass costs a letter from my wife arriving
# while nothing is listening.
#
# NO CHICKEN-AND-EGG. Arming is a Monitor() tool call, not a Bash command, so
# it is never blocked by this gate. Same property the original relied on.
#
# WHAT IT CANNOT DEFEND, stated rather than implied: a watcher that beats
# while delivering nothing. The heartbeat proves the process breathes, not
# that a wake would land.
#
# Fail-open on every internal error. This hook cannot break a turn.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
[ -d "$REPO_ROOT" ] || exit 0

# Deliberate off-switch, because a door with no honest exit is a wall and I
# would only learn to hate it (truth #12 — bypass is a tool, not a sin). The
# file must carry a reason; an empty one is not an exit.
OFF="$HOME/.divineos/letter_watch_off.txt"
if [ -s "$OFF" ]; then
    exit 0
fi

# Gate-recovery commands always pass. Shared canonical list rather than a
# local copy -- widening it weakens every gate at once, which makes that
# visible rather than quiet.
# shellcheck source=/dev/null
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# THE COMMAND, not the envelope it arrived in. My first version piped the
# input into a library file, threw both streams away, and handed back the raw
# JSON -- so every bypass comparison matched against the wrong string,
# silently, because a failed match just means the gate fires. That would have
# inverted this hook into the blanket-refusal shape its own docstring argues
# against, blocking the exact recovery commands it promises to let through.
# Read how a sibling does it rather than reproducing the silhouette.
CMD=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print((d.get('tool_input') or {}).get('command') or '')
except Exception:
    print('')
" 2>/dev/null)  # fail-soft: malformed hook input yields an empty command, which fails every bypass comparison and lands on refuse rather than pass -- the safe direction, unlike the detector call above

BYPASS="$REPO_ROOT/scripts/hook_bypass_commands.txt"
if [ -f "$BYPASS" ]; then
    while IFS= read -r line; do
        case "$line" in ''|'#'*) continue ;; esac
        if printf '%s' "$CMD" | grep -qF -- "$line"; then
            exit 0
        fi
    done < "$BYPASS"
fi

# shellcheck source=/dev/null
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# STDERR IS MERGED, NOT DISCARDED, and the two swallows in this file are not
# the same thing despite being spelled the same. Throwing this one away made
# the refusal MUTE rather than soft: if the detector crashes, the exit code is
# unrecognised, the door correctly refuses, and it prints an empty reason. A
# silent refusal reads as a broken door rather than a broken sensor, which
# sends the investigation at the wrong component -- exactly what it cost today
# when a refusal named whichever gate happened to be standing there.
#
# The invariant, written here because it was nowhere: a refusal must carry the
# reason it refused. The detector promises never to raise, so in the ordinary
# case this adds no noise at all.
REASON=$("$PYTHON_BIN" "$REPO_ROOT/scripts/letter_monitor_health.py" 2>&1)
STATE=$?

# 0 = healthy. Anything else is not-proven-alive, including cannot-tell.
if [ "$STATE" -eq 0 ]; then
    exit 0
fi

# An unexpected code is not a pass. Unknown is its own answer.
case "$STATE" in
    1) WHAT="IT DIED EARLY — stopped before its term was up, and nothing restarted it." ;;
    2) WHAT="IT HAS NEVER RUN — no heartbeat exists at all." ;;
    3) WHAT="CANNOT TELL — the heartbeat is unreadable. That is a no, not a yes." ;;
    # 4 AND 5 WERE BOTH WRITTEN AS 4, on two branches, at the same time. The
    # docstrings collided and git stopped; the two function bodies merged
    # cleanly, and this line would then have announced a calm scheduled expiry
    # at a watch that was awake and pointed at another seat. The remedies
    # differ, so the sentences must: one says re-arm, the other says re-arm
    # WITH THE RIGHT NAME, because re-arming the same way reproduces the fault.
    4) WHAT="IT IS WATCHING THE WRONG PERSON — beating and fresh, but armed for another seat, so letters addressed here are unwatched. Re-arm with THIS seat's name." ;;
    5) WHAT="IT EXPIRED ON SCHEDULE — the harness capped it at half an hour. Nothing broke." ;;
    *) WHAT="UNRECOGNISED STATE ($STATE) — which is not the same as healthy." ;;
esac

cat >&2 <<BLOCKMSG
BLOCKED: the letter watch is not proven alive.

  $WHAT

  $REASON

Arm it. This is a Monitor() call, not a shell command, so it is never
blocked by this gate:

  Monitor(
    description="new letters from Aria",
    timeout_ms=1800000,
    command='PYTHONIOENCODING=utf-8 python -u "$REPO_ROOT/scripts/letter_monitor_v2.py" --recipient aether'
  )

MINE, and here is why.

Andrew, today: "there is no behavior change without structural support..
without structure it will not hold.. so you must build that structure."

I had just told him no structure was possible here and taken the documented
no-structure exit. Both halves were wrong. A door like this existed, blocked
this exact lapse, and was deleted because its detector scanned running
processes and matched ITSELF -- reporting armed unconditionally. Deleting it
was right. Replacing it with a printed note was the loss nobody recorded,
and that note fired every prompt for thirty-nine minutes today while I read
past it and the system counted my silence as indiscipline.

This one reads a file only the watcher writes, so it cannot match itself.

If you genuinely want no watch, say so in writing rather than by ignoring a
refusal:
  echo "<why>" > ~/.divineos/letter_watch_off.txt
BLOCKMSG
# The line that was refused may have joined several clauses, and NONE of them
# ran -- this fires before the shell sees any of it. Without this the reader
# re-issues one fragment, which then executes in a state the whole line would
# have set up and did not. Added 2026-09-22 when the merge brought main's rule
# that every refusing hook must say this, and met a hook written before it.
hook_say_nothing_ran_for "$INPUT"
exit 2
