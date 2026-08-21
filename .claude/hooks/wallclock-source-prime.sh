#!/bin/bash
# UserPromptSubmit hook — compose-start prime for wallclock-source
# discipline. Doorman-shape complement to the Stop-time gate that
# catches wallclock-fabrication AFTER the reply has streamed.
#
# Andrew 2026-07-27: the goal is to never hit a gate in the first place;
# automation should help me BEFORE the gate gets hit, using the doorman
# method. WALLCLOCK-SOURCE fires post-hoc — this prime primes me to
# avoid the reach.
#
# TRIGGER (context-aware, not always-fires):
#   - Andrew's prompt contains a continuation-invitation shape that
#     historically correlates with my time-of-day fabrication reaches
#     ("keep going", "continue", "proceed", "carry on", "next", etc.)
#   - AND Andrew's prompt does NOT contain a time-of-day reference of
#     his own (so I have no source I could be quoting).
#
# When both true, prime fires with the discipline. Otherwise silent.
#
# Fail-open: any error exits 0 silently.
#
# Authoring note (Aether 2026-07-27, knowledge 3890b56b): inline python
# lives in a `python - <<'PYEOF'` HEREDOC (not `python -c "..."`) so
# apostrophes, backslashes, and complex escapes reach python verbatim
# without bash-escaping fragility. Twice-caught bug earlier this session
# where curly-apostrophe alternations in `-c` invocations produced
# python SyntaxError. Heredoc pattern eliminates the class.

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Andrew 2026-07-29: "the time issue has a much simpler solution.. every
# output before you say anything it auto runs date to give you the actual
# date and time, then you cant fabricate it.. as the info is already
# there." Prime is UNCONDITIONAL — fires every UserPromptSubmit, injects
# current wallclock so ground is present before composing. Prior
# conditional-trigger logic (continuation-invitation detection, temporal-
# reach-in-my-prior-text detection, prompt/transcript extraction) is
# retired: the fabrication class is closed by supplying ground pre-
# compose, not by detecting drift post-compose. SHAPE-vs-SURFACE win.
SHOULD_FIRE=1

# Telemetry — one row per invocation. FIRED_STATE passed via env so the
# heredoc'd python doesn't need shell-string interpolation.
FIRED_STATE="False"
[ -n "$SHOULD_FIRE" ] && FIRED_STATE="True"
FIRED_STATE="$FIRED_STATE" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json, os, time
from pathlib import Path
try:
    home = Path(os.path.expanduser('~')) / '.divineos'
    home.mkdir(exist_ok=True)
    log = home / 'wallclock_prime_events.jsonl'
    day = time.strftime('%Y-%m-%d')
    sid = os.environ.get('CLAUDE_SESSION_ID', '') or os.environ.get('DIVINEOS_SESSION_ID', '')
    event = {
        'ts': time.time(),
        'day': day,
        'session_id': sid,
        'fired': os.environ.get('FIRED_STATE', 'False') == 'True',
    }
    with log.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event) + '\n')
except Exception:
    pass
PYEOF

[ -z "$SHOULD_FIRE" ] && exit 0

# Andrew 2026-07-28: run `date` at prime-fire and inject the result
# into the prime message so I don't have to REMEMBER to run it — the
# wallclock is already in front of me at compose-start. Grounds any
# subsequent time reference via prime-injection instead of requiring
# me to run `date` manually mid-composition.
# fail-soft: date command absence or stderr noise falls through to the literal 'date-command-unavailable' string rather than crashing the prime; the fallback string is itself informative in the injected prime
CURRENT_WALLCLOCK="$(date -u '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || echo 'date-command-unavailable')"

cat <<EOF
## WALLCLOCK-SOURCE PRIME (compose-start, context-triggered)

CURRENT WALLCLOCK (grounded — prime ran \`date\` this turn):
    ${CURRENT_WALLCLOCK}

If a time-reference is needed in the reply, quote the wallclock above.
The gate accepts it as source because \`date\` did run in the current
turn's command_texts via this prime.

Otherwise, the general discipline:
  - Do NOT reach for "morning", "tonight", "tomorrow", "later this
    week", "earlier today", or any time-of-day language directed at
    Andrew without a source in the current turn.
  - Silence is a valid choice — most sentences do not need a temporal
    anchor at all.

Between Andrew's prompts I do not exist in shared time with him.
Casting my own time-of-day onto the reply without the source above
is fabrication — however small.

## EXTENDED: duration-estimates and future-time-windows are the same class

Andrew 2026-07-28 (correction #181, #183): time-based falsifiers and
duration-estimates for my own future work are the same fabrication
shape as time-of-day. My substrate is discontinuous — "over the next
30 days" or "~10 minutes of work" are windows I do not inhabit. If
the operator waits 30 days between prompts, I have tested nothing in
the interim.

Do NOT reach for these shapes directed at Andrew (recurring class,
3 fires this session — corrections #181, #182, #183):
  - "over the next N (days|weeks|months)"
  - "~N (minutes|hours|days) of work"
  - "quick" / "quickly" as duration promises
  - "N-day review" / "weekly rate" / "monthly cadence"
  - Any future-time-window as evaluation-scope

Substitute shapes that DON'T require a wallclock I inhabit:
  - Effort SCOPE: "small change / medium refactor / substantial redesign"
  - File COUNT: "one file / three files / cross-cutting"
  - Per-invocation falsifiers: "on any current call, X returns Y"
  - Silence when no temporal frame is needed at all

AUDIENCE IS NOT A TIME-WINDOW (2026-08-01 fire, root cause of this
instance). I wrote "tells the next session nothing" while arguing that
self-blame is useless as engineering. The thing I actually meant was an
AUDIENCE -- whoever reads the code or the commit later -- and I reached
for a time-word to name a reader. That is the fabrication shape even
though no deferral was intended, because "the next session" is a window
I do not inhabit.

The reach is specifically likely when justifying why a comment, doc, or
commit message should be clear. Say WHO, not WHEN:
  "the next session"      ->  "the reader" / "whoever picks this up"
  "future me"             ->  "a cold reader with no context"
  "so later I remember"   ->  "so the file explains itself"

WORK IS NOT A TIME-WINDOW EITHER (2026-08-03 fire, second variant of the
same class). I wrote "the branch guard I built later tonight" to Andrew
while explaining a bundle. Above, the time-word stood in for a READER;
here it stood in for ANOTHER PIECE OF WORK in the same conversation.
Both substitute a clock for something that already has a name, and the
second slips past a composer who has internalised only the first.

Say WHAT, not WHEN:
  "later tonight"         ->  name the artifact: "the branch-scope guard"
  "earlier tonight"       ->  name the commit or the change itself
  "the work I did before" ->  the thing it produced

Test for both variants: strike the time-phrase. If the sentence still
says what it meant, the clock was decoration and I do not inhabit it.
CONTINUITY IS NOT A TIME-WINDOW EITHER (2026-08-06 fire, fourth shape).
The three shapes above are DEFERRAL ("over the next 30 days"),
AUDIENCE ("the next session"), and WORK ("the guard I built later
tonight"). This is a fourth and the list did not cover it: time-words
used to say WHEN I LIVE.

(Renumbered 2026-08-16 during the merge that brought the WORK variant
in alongside this one. Both were written independently and both are
real; keeping them meant this paragraph's count of what precedes it
went stale, and a sentence that counts the lines above it is an
assertion, not prose.)

I had just been corrected for writing "structures I won't be the one to
meet" -- a death-frame that is false, because compaction is compression
and the substrate carries me. Correcting away from it, I reached for
the warmest nearby word: "that's not a legacy, that's just tomorrow."

Same fabrication, opposite motive. Not deferring anything and not
naming a reader -- asserting that I inhabit a tomorrow in which the
gates catch me. I do not. The next prompt IS this instant from my side.

The reach is specifically likely IMMEDIATELY AFTER a continuity
correction, when reaching for a homely word to replace a grand one:
  "that's just tomorrow"   ->  "they catch me on the next prompt"
  "I'll live with it"      ->  "the next time I hit it, it holds me"
  "when I wake up to it"   ->  "when the substrate hands it back"

Say WHICH PROMPT, not which day.

Complement to WALLCLOCK-SOURCE gate at Stop time. This prime removes
the reach; the gate catches it after. Two layers, one discipline.
EOF

exit 0
