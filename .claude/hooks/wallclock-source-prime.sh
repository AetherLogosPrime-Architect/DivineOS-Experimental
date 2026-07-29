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

# Extract prompt AND last assistant text separately — wallclock has an
# asymmetry: Andrew's time-of-day words are legitimate SOURCES for me
# to quote; MY prior time-of-day words are fabrications-to-prevent.
# So the two texts feed different halves of the trigger check:
#   - Continuation-invitation: MATCH on EITHER (both signal composing
#     continues into a wallclock-drift zone).
#   - Time-source presence: MATCH on Andrew's prompt ONLY (his time
#     words silence the prime; mine reinforce it).
# Andrew 2026-07-27: "it cant just be my prompts that trigger it but
# also your own outputs."
# fail-soft: python parse or transcript read errors return empty string; hook then exits silently rather than blocking UserPromptSubmit
PROMPT_AND_ASSISTANT="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)
prompt = data.get('prompt') or ''
transcript_path = data.get('transcript_path', '') or ''
last_assistant_text = ''
if transcript_path and os.path.exists(transcript_path):
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                if entry.get('type') == 'assistant':
                    msg = entry.get('message', {}) or {}
                    content = msg.get('content', [])
                    if isinstance(content, list):
                        parts = [c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text']
                        last_assistant_text = '\n'.join(parts)
                    elif isinstance(content, str):
                        last_assistant_text = content
    except (OSError, ValueError):
        pass
# Emit prompt and assistant separated by unique sentinel that regex-scan
# can split on.
sys.stdout.write((prompt or '') + '\n<<<PROMPT_END>>>\n' + (last_assistant_text or ''))
PYEOF
)"

[ -z "$PROMPT_AND_ASSISTANT" ] && exit 0

# fail-soft: python regex or classification error results in silence rather than firing the prime; safer default is not-fire on internal error
SHOULD_FIRE="$(HOOK_PROMPT="$PROMPT_AND_ASSISTANT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import os, re, sys
raw = os.environ.get('HOOK_PROMPT', '') or ''
if not raw.strip():
    sys.exit(0)

# Split into (andrew_prompt, my_prior_assistant_text) on the sentinel.
if '<<<PROMPT_END>>>' in raw:
    andrew_prompt, my_assistant = raw.split('<<<PROMPT_END>>>', 1)
else:
    andrew_prompt, my_assistant = raw, ''
andrew_prompt = andrew_prompt.strip()
my_assistant = my_assistant.strip()

# Trigger: fire when EITHER (a) continuation-invitation shape appears
# in prompt OR my prior assistant text, OR (b) my prior assistant text
# already contains temporal-scope tokens (empirical signal I've been
# reaching for wallclock this session — keep priming me forward).
# Andrew 2026-07-28: continuation-invitation-only was too narrow;
# emotional/relational Andrew-prompts never triggered it, so I walked
# into the Stop-time gate three times in one session. Broaden trigger
# to catch the empirical reach-pattern regardless of prompt shape.
continuation_patterns = [
    r'\bkeep\s+going\b',
    r'\bcontinue\b',
    r'\bproceed\b',
    r'\bcarry\s+on\b',
    r"\bwhat['’]?s\s+next\b",
    r'\bnext\s+(?:step|task|thing)\b',
    r'\bcool\b\W*$',
    r'\bok\b\W*$',
    r'\bnice\b\W*$',
    r'\bgo\s+for\s+it\b',
    r'\bgo\s+ahead\b',
]
# Temporal-scope tokens: if my last message contained ANY of these
# directed at Andrew, the reach-pattern is live this session and the
# prime should fire on the next compose regardless of prompt shape.
my_reach_patterns = [
    r'\ball\s+(?:night|day|week|month|year|morning|afternoon|evening)\b',
    r'\b(?:this|last|next)\s+(?:week|month|year|hour|morning|afternoon|evening|night)\b',
    r'\b(?:tonight|tomorrow|yesterday|today)\b',
    r'\b(?:hours?|days?|weeks?|months?|years?)\s+(?:ago|of|from|since)\b',
    r'\bfour\s+months?\b',
    r'\bmoments?\s+ago\b',
    r'\bearlier\s+(?:today|this)\b',
    r'\blater\s+(?:today|this|tonight)\b',
]
combined_continue = re.compile('|'.join(continuation_patterns), re.IGNORECASE | re.MULTILINE)
combined_reach = re.compile('|'.join(my_reach_patterns), re.IGNORECASE | re.MULTILINE)
both_texts = andrew_prompt + '\n' + my_assistant
continuation_hit = combined_continue.search(both_texts)
reach_hit = combined_reach.search(my_assistant)  # only my prior text, not Andrew's
if not (continuation_hit or reach_hit):
    sys.exit(0)

# Time-of-day references — MATCH on Andrew's prompt ONLY. His time-of-
# day words are legitimate sources for me to quote; my prior wall-
# clock words are the exact fabrications this prime is trying to
# prevent, so they must not silence the prime.
time_patterns = [
    r'\b(?:morning|afternoon|evening|night|noon|midnight|tonight|today|yesterday|tomorrow)\b',
    r'\b(?:this|next|last)\s+(?:week|month|year|hour|minute)\b',
    r'\b\d{1,2}\s*(?:am|pm)\b',
    r'\b\d{1,2}:\d{2}\b',
    r'\b(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?\b',
    r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b',
    r'\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b',
]
combined_time = re.compile('|'.join(time_patterns), re.IGNORECASE)
if combined_time.search(andrew_prompt):
    sys.exit(0)

print('1')
PYEOF
)"

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

Complement to WALLCLOCK-SOURCE gate at Stop time. This prime removes
the reach; the gate catches it after. Two layers, one discipline.
EOF

exit 0
