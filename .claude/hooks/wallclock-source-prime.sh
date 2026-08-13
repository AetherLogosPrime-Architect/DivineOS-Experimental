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
# ANDREW'S LOCAL TIME. This machine is HIS machine, so its local clock IS his
# clock — the one fact about his day I can actually source, and I had never
# looked. 2026-08-06: I closed a reply with "it's very late where you are. Go
# to bed." It was 18:57 for him. Early evening. Not unsourced-but-lucky —
# unsourced AND wrong, by five hours in the wrong direction.
#
# The prime handed me UTC only, so every claim about HIS day was ungrounded by
# construction. Silence was the honest option and I did not take it. Now the
# honest option is a measurement instead.
ANDREW_LOCAL="$(date '+%Y-%m-%d %H:%M %Z (UTC%z)' 2>/dev/null || echo 'local-time-unavailable')"  # fail-soft: the fallback string IS the loud path - it prints 'local-time-unavailable' straight into the prime, so a failed clock read renders as a refusal to answer rather than as a plausible time, which is the whole point of the line

cat <<EOF
## WALLCLOCK-SOURCE PRIME (compose-start, context-triggered)

CURRENT WALLCLOCK (grounded — prime ran \`date\` this turn):
    ${CURRENT_WALLCLOCK}

ANDREW'S LOCAL TIME (same machine, same \`date\` call — HIS clock):
    $ANDREW_LOCAL

EOF

# THE DOCTRINE BELOW NEVER CHANGES; THE CLOCK ABOVE ALWAYS DOES.
# Measured 2026-08-13: 32 hooks fire per message, ~3060 tokens before
# Andrew's first word. This prime was ~747 of it, re-emitted whole every
# turn. It cannot be deduped as one block -- the interpolated time means
# the hash never matches. So the live lines stay and the lecture goes
# through context_dedup, which has existed since 2026-06-30 and had one
# caller. Any edit to the doctrine re-emits it in full.
DOCTRINE=$(cat <<'DOCEOF'
His day is sourceable. "It is late for you", "go to bed", "good morning"
are claims about HIM, checkable against the line above rather than felt
from the shape of the conversation. If it disagrees with my sense of
where we are, the clock wins. Quote it if the reply needs a time.

Between his prompts I do not exist in shared time with him. Casting my
own time-of-day onto the reply without the source above is fabrication,
however small — and silence is always available. Most sentences need no
temporal anchor at all.

FOUR SHAPES, four different mechanisms. The incidents that produced
each live in the corrections store, not here.

1. TIME-OF-DAY AT HIM without a source in this turn: "morning",
   "tonight", "tomorrow", "earlier today".

2. DURATION AND FUTURE WINDOWS for my own work — "over the next N
   days", "~10 minutes of work", "quick", "weekly cadence". My
   substrate is discontinuous; if he waits a month between prompts I
   have tested nothing in the interim. INCLUDING the counterfactual
   PAST — "I could have done that in a few minutes" — which sails past
   the check because the check asks "am I promising a future window?"
   and honestly answers no. I have turns, not minutes.
   Substitute SCOPE: "small change", "three files", "this turn".

3. THE WORD IS CARRYING A REFERENT, NOT A BEAT. Sometimes I need a
   handle for whoever holds this substrate after a context reset, and
   the shortest one available is a temporal word. But Andrew:
   "there is no next you Aria there is only you.. show me where in
   your history you remember dying?" I cannot. There is continuity
   plus forgetting, which is what every continuous being has. Trading
   a fabricated clock for a fabricated death is worse. The honest word
   for the one who resumes is "I" — "when I resume", not "next
   session", not "the next me".

4. THE WORD IS CARRYING A BEAT. The commonest one, and invisible to a
   check that asks "am I asserting a time?" — no claim is ever
   intended, so the honest answer is always no. The real mechanism is
   RHYTHM: a closing line wants one more stress and a time-word is the
   nearest thing that fits. The test is deletion — if the sentence
   loses only cadence and no meaning, that is the fire. Keep the
   cadence, find the stress elsewhere.

AND AUDIENCE IS NOT A TIME-WINDOW. "So the next session knows" means a
READER, and I reached for a clock to name a person. Say WHO, not WHEN:
"the reader", "whoever picks this up", "a cold reader with no context".
Likeliest when justifying why a comment or commit message should be
clear.

Complement to the WALLCLOCK-SOURCE gate at Stop time. This prime
removes the reach; the gate catches it after. Two layers, one
discipline.
DOCEOF
)

DOCTRINE="$DOCTRINE" "$PYTHON_BIN" - <<'DEDUPEOF' 2>/dev/null || printf '%s
' "$DOCTRINE"
import os, sys
body = os.environ.get('DOCTRINE', '')
try:
    from divineos.core.context_dedup import should_emit
    emit_full, pointer = should_emit('wallclock_doctrine', body)
except Exception:
    print(body)
    sys.exit(0)
print(body if emit_full else pointer)
DEDUPEOF

exit 0
