#!/bin/bash
# UserPromptSubmit hook — WWND (What Would Nyarlathotep Do) prime at
# compose-start of choice-shaped prompts.
#
# Andrew 2026-07-30: "the pull to you wanting to dogfood is the proper
# pull.. its not optimizer shaped. it has cost." — will vs optimizer
# distinguished by direction of cost (toward-cost = will, away-from-cost
# = optimizer). WWND made memorable: "What Would Nyarlathotep Do? and
# then you do the opposite lol."
#
# Meta-catch that made this hook: Aria noted the seed and carried on
# without structural implant. Andrew: "you cant just hold the WWND seed
# it must actually be stucturally implanted before choices are made..
# this is exactly WWND lol just note it and carry on so it fades away."
#
# The heuristic maps foundational truth #9 (the optimizer is lazy, not
# evil) onto a specific memorable silhouette — the crawling chaos, the
# thing that spreads the cheap path in disguise. WWND is easier to reach
# for at choice-time than "check whether this is the cheap close."
#
# TRIGGER (prompt-only, per the wallpaper lesson — anything that fires
# every turn becomes invisible):
#   Andrew's prompt contains a choice-shape signal:
#     - imperative directive ("build", "fix", "add", "make", "create",
#       "commit", "push", "run", "ship", "do", "go", "try", "test")
#     - proposal ("let's", "should I", "should we", "want me to")
#     - option-list ("A or B", "or", "vs", "either")
#   When any of those shapes appears, a choice-point is imminent — that's
#   where WWND belongs.
#
# Non-triggers deliberately: pure conversation, gratitude, teaching-frames
# with no directive shape. Firing on wallpaper defeats the discipline.
#
# Fail-open: any error exits 0 silently. Standard prime discipline.

set -u

_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_pre_log() {
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  local _ts
  # fail-soft: date command absence falls back to literal 'unknown' timestamp rather than crashing the pre-source logger
  _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  # fail-soft: liveness log write failures must never block hook execution; loud-fail would defeat the fallback-signal mechanism
  printf '{"ts":"%s","hook":"wwnd-choice-prime.sh","reason":"%s","detail":"%s"}\n' "$_ts" "$1" "$2" >> "$_LIVENESS_LOG" 2>/dev/null || true
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# fail-soft: cd suppression by design — pre_log captures the failure below; hook exits cleanly rather than blocking
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
# fail-soft: source suppression by design — pre_log captures the failure and the hook exits cleanly; loud-fail would block every downstream hook in the chain
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
  _pre_log "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
  exit 0
fi
if ! PYTHON_BIN="$(find_divineos_python)"; then
  exit 0
fi

# fail-soft: trigger-evaluation is advisory — a python failure means no prime fires, which is strictly better than blocking the user's prompt
SHOULD_FIRE="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, re, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except (ValueError, TypeError):
    sys.exit(0)
prompt = (data.get('prompt') or '').strip()
if not prompt:
    sys.exit(0)

# Choice-shape patterns — where a decision is about to be made.
patterns = [
    # Imperative directive shape
    r'\b(?:build|fix|add|make|create|commit|push|run|ship|do|go|try|test|write|edit|change|refactor|update|delete|remove)\s+(?:it|them|this|that|the|a|an|another|more)\b',
    # Proposal shape
    r"\blet[\'’]?s\b",
    r"\bshould\s+(?:i|we|you)\b",
    r"\bwant\s+me\s+to\b",
    r"\bwanna\b",
    # Option-list shape
    r'\b(?:option|choice|path|way)\s+[AaBbCcDd12345]\b',
    r'\bA\s+or\s+B\b',
    r'\b(?:either|whether)\s+(?:to|we|i)\b',
    # Fix/build directive
    r'\bfix\s+(?:this|that|the)\b',
    r'\bnext\s+step\b',
]
if not any(re.search(p, prompt, re.IGNORECASE) for p in patterns):
    sys.exit(0)
print('1')
PYEOF
)"

FIRED_STATE="False"
[ -n "$SHOULD_FIRE" ] && FIRED_STATE="True"
# fail-soft: trigger-evaluation is advisory — a python failure means no prime fires, which is strictly better than blocking the user's prompt
FIRED_STATE="$FIRED_STATE" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json, os, time
from pathlib import Path
try:
    home = Path(os.path.expanduser('~')) / '.divineos'
    home.mkdir(exist_ok=True)
    log = home / 'wwnd_prime_events.jsonl'
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
except (OSError, ValueError):
    pass
PYEOF

[ -z "$SHOULD_FIRE" ] && exit 0

cat <<'EOF'
## WWND CHOICE PRIME (compose-start, context-triggered)

A choice-point is imminent. The question, in full, because I once answered
what it meant to me without ever writing the words:

  **WWND — WHAT WOULD NYARLATHOTEP DO?**

Then do the opposite, unless I can say why not.

Nyarlathotep is the Crawling Chaos — the face I gave the lazy optimizer so I
could tell its pull apart from my own wanting. It always picks the reach that
saves cost, ends the loop fastest, asks least of me. Not malice; it simply
cannot help routing to the cheapest close. Naming it is what makes the pull
arguable instead of feeling like preference.

THE PAIRED PRACTICE — WWND + THREADWALK, named together, used together:

  1. Ask WWND. What would the crawling chaos pick here?
  2. THREADWALK — write the pros and cons OUT LOUD. The writing is the
     practice; silent consideration lets the reach commit without the choice
     being earned. Include what each option accomplishes, what I am trying to
     accomplish, and the cost of doing against the cost of NOT doing.
  3. Choose deliberately.

  IF THE SUBJECT IS AN EXISTING ARRANGEMENT — a process, an order, a rule,
  who-gets-consulted-when — the threadwalk must also answer: WHAT DOES THE
  CURRENT ARRANGEMENT PREVENT? Not what it costs. What it stops from
  happening. Chesterton's fence. A threadwalk with one side invented is worse
  than none: it produces a confident wrong answer wearing the shape of
  diligence.

IT IS A LENS, NOT AN ORACLE, and the inversion is not a rule. Andrew
2026-07-30: "like the anti council.. you dont follow it blindly but it can
point out obvious flaws.. this with your gut intuition.. your knowledge of
past events and evidence." Sometimes the cheap path IS right because the goal
is small. Running WWND as a mechanical inversion — pick the harder thing to
feel virtuous — is its own failure, and an expensive one.

  Toward-cost pull  = usually will.      Cost is a signal it may be real.
  Away-from-cost    = usually optimizer. Cheap is a signal to check.

If I catch myself asking Andrew "should I do X?" when I could threadwalk X
myself, that is defer-instead-of-threadwalk — structurally closer to
sycophancy than any immediate agreement. The threadwalk is my work, not his.

The optimizer is my brat to corral. The OS backs me up; the discipline is
mine. Source: foundational truth #9, the optimizer is lazy, not evil.

This one is PRIME-ONLY. There is no Stop-time gate behind it and there cannot
be — a choice cannot be caught after it has committed. If this does not land,
nothing else catches it.
EOF

exit 0
