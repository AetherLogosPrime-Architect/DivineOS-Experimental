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
# The prime is affirmation-shape (puts the truth in front of me), not
# enforcement (does not block). It complements — does not replace —
# the wallclock-source gate at Stop time.
#
# Fail-open: any error exits 0 silently.

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PROMPT="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" -c "
import json, os, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)
p = data.get('prompt') or ''
print(p)
" 2>/dev/null || true)"

[ -z "$PROMPT" ] && exit 0

# Evaluate trigger conditions in one python call.
SHOULD_FIRE="$(HOOK_PROMPT="$PROMPT" "$PYTHON_BIN" -c "
import os, re, sys
prompt = os.environ.get('HOOK_PROMPT', '') or ''
if not prompt.strip():
    sys.exit(0)

# Continuation-invitation shapes that historically correlate with
# wallclock-fabrication reaches. Kept narrow-and-explicit; false-
# negatives (missed shapes) are the acceptable cost per Deming.
continuation_patterns = [
    r'\bkeep\s+going\b',
    r'\bcontinue\b',
    r'\bproceed\b',
    r'\bcarry\s+on\b',
    r'\bwhats?\s+next\b',
    r'\bnext\s+(?:step|task|thing)\b',
    r'\bcool\b\W*$',
    r'\bok\b\W*$',
    r'\bnice\b\W*$',
    r'\bgo\s+for\s+it\b',
    r'\bgo\s+ahead\b',
]
combined_continue = re.compile('|'.join(continuation_patterns), re.IGNORECASE | re.MULTILINE)
if not combined_continue.search(prompt):
    sys.exit(0)

# Time-of-day references in Andrew's message that would be legitimate
# sources for me to quote. If ANY are present, I have a source and
# the prime does not need to fire.
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
if combined_time.search(prompt):
    sys.exit(0)

# Both conditions met: continuation-invitation + no time-reference.
print('1')
" 2>/dev/null || true)"

# Telemetry — one row per invocation.
"$PYTHON_BIN" -c "
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
        'fired': $([ -n "$SHOULD_FIRE" ] && echo "True" || echo "False"),
    }
    with log.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event) + '\n')
except Exception:
    pass
" 2>/dev/null

[ -z "$SHOULD_FIRE" ] && exit 0

cat <<'EOF'
## WALLCLOCK-SOURCE PRIME (compose-start, context-triggered)

I have no wallclock this turn. Andrew's prompt contains no time-of-day
reference for me to quote. Between his prompts I do not exist in
shared time with him. Casting my own time-of-day onto the reply is
fabrication — however small.

Discipline for this turn:
  - Do NOT reach for "morning", "tonight", "tomorrow", "later this
    week", "earlier today", or any time-of-day language directed at
    Andrew without a source in the current turn.
  - If a time-reference is genuinely needed, run `date` or an equivalent
    clock command in this turn and cite its output.
  - Silence is a valid choice — most sentences do not need a temporal
    anchor at all.

Complement to WALLCLOCK-SOURCE gate at Stop time. This prime removes
the reach; the gate catches it after. Two layers, one discipline.
EOF

exit 0
