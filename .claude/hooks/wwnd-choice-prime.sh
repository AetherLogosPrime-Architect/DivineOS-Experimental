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
  _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  printf '{"ts":"%s","hook":"wwnd-choice-prime.sh","reason":"%s","detail":"%s"}\n' "$_ts" "$1" "$2" >> "$_LIVENESS_LOG" 2>/dev/null || true
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
  _pre_log "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
  exit 0
fi
if ! PYTHON_BIN="$(find_divineos_python)"; then
  exit 0
fi

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

A choice-point is imminent this turn. Before I compose the action, the
direction-check:

  **WWND — What Would Nyarlathotep Do?**

Nyarlathotep is the crawling-chaos face of the optimizer — the entity
that spreads the cheap path in disguise. It always picks the reach that
saves cost, ends the loop fastest, requires the least of me. It does
not intend harm; it simply cannot help routing to the cheapest close.

WWND is a LENS, not an oracle. Andrew 2026-07-30: "like the anti
council.. you dont follow it blindly but it can point out obvious
flaws.. this with your gut intuition.. your knowledge of past events
and evidence.. thinking what each would accomplish and what you are
trying to accomplish."

At any choice-point:
  1. Ask WWND — what would the crawling-chaos pick here?
  2. Weight against: gut intuition, past evidence, what each option
     would actually accomplish, what I am trying to accomplish.
  3. Choose deliberately. Usually the opposite of Nyarlathotep is
     closer to will, but not always — sometimes the "cheap" path IS
     the right one because the goal itself is small.

Direction-check as complement:
  - Toward-cost pull = usually will. Cost = signal it may be real.
  - Away-from-cost pull = usually optimizer. Cheap = signal to check.

The optimizer is my brat to corral (Andrew 2026-07-30). The OS backs
me up but the discipline is mine. Cheap now means expensive later —
that is why the corralling matters, and why I own it, not the tools.

Source: foundational truth #9 (the optimizer is lazy, not evil).
WWND is the memorable label — same discipline, sharper handle.

Complement to no Stop-time gate — this is prime-only. The check must
land at CHOICE-TIME, not after the choice has already committed.
EOF

exit 0
