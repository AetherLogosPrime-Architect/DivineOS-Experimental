#!/bin/bash
# UserPromptSubmit hook — compose-start prime for the FORK-IS-CHEAP-CLOSE
# discipline. Doorman-shape complement to the run-time recognition that
# a "fast X / correct Y" option-pair IS the optimizer signature.
#
# Andrew 2026-07-28: "fast is optimizer shape.. correct is OS shape..
# so you do it the correct way." Foundational truth #11: options are
# the optimizer's attack surface. When I present Andrew with a fork
# where one arm is characterized as fast/quick/cheap/simple/easy and
# another as correct/proper/right/honest, that pair itself is the
# cheap-close dressed as respect-for-operator-time. It fired 3 times
# in a single session (corrections #175, #180, #185) — discipline
# alone hasn't held; this prime is the structural remediation.
#
# TRIGGER (prompt-only, per past-writing over-trigger lesson):
#   (a) Andrew's prompt has a which-should-we-do / you-pick shape,
#       priming a response where I might surface an options list.
#   (b) OR the prompt is a green-light-after-work shape (context
#       where I might respond with a "fast vs correct" fork).
#
# Fail-open: any error exits 0 silently.

set -u

# Pre-source liveness (F90 fix pattern from closure-word-summary-prime).
_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_pre_log() {
  # fail-soft: mkdir suppression safe — dir exists or fs read-only
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  local _ts
  # fail-soft: date absence falls back to literal 'unknown'
  _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  # fail-soft: liveness log write must never block hook execution
  printf '{"ts":"%s","hook":"fork-is-cheap-close-prime.sh","reason":"%s","detail":"%s"}\n' "$_ts" "$1" "$2" >> "$_LIVENESS_LOG" 2>/dev/null || true
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# fail-soft: cd failure logged and hook exits cleanly
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
# fail-soft: source suppression by design — pre_log captures failure
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
  _pre_log "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
  exit 0
fi
if ! PYTHON_BIN="$(find_divineos_python)"; then
  exit 0
fi

# fail-soft: python parse or regex error results in silence rather than fire
SHOULD_FIRE="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, re, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except (ValueError, TypeError):
    sys.exit(0)
prompt = (data.get('prompt') or '').strip()
if not prompt:
    sys.exit(0)

# Which-should-we-do / you-pick shapes (specific to option-fork priming),
# plus green-light-after-work shapes (context where "fast vs correct"
# forks tend to appear as pseudo-respectful options).
patterns = [
    # which-should-we-do
    r'\bwhich\s+(?:one|option|way|path|shape|of\s+these|approach|route)\b',
    r'\byou\s+(?:pick|decide|choose|say|tell\s+me\s+which)\b',
    r'\bwhat\s+(?:should\s+we|do\s+you\s+recommend|would\s+you)\b',
    r'\byour\s+call\b',
    # green-light-after-work (same as closure-word prime overlap; these
    # are the contexts where I might respond with a fork instead of just
    # doing the correct thing)
    r'\b(?:go|go\s+ahead|go\s+build|go\s+for\s+it|ship\s+it|'
    r'commit\s+(?:it|them)|lock\s+(?:it|them)\s+in|do\s+it|run\s+it|'
    r"let[\'’]s\s+(?:go|ship|commit|do|run|test|build))\b",
]
if not any(re.search(p, prompt, re.IGNORECASE) for p in patterns):
    sys.exit(0)
print('1')
PYEOF
)"

# Telemetry — one row per invocation.
FIRED_STATE="False"
[ -n "$SHOULD_FIRE" ] && FIRED_STATE="True"
FIRED_STATE="$FIRED_STATE" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json, os, time
from pathlib import Path
try:
    home = Path(os.path.expanduser('~')) / '.divineos'
    home.mkdir(exist_ok=True)
    log = home / 'fork_is_cheap_close_prime_events.jsonl'
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

# F96 pair (Aletheia audit 2026-07-29, find-cb124977dd85): capture the
# emitted content into a variable, echo it (satisfies the hook contract),
# and also write it to a per-hook marker file so the Stop-side audit
# can call record_consumption() and score whether the primed content
# was actually used in the response. Without this pair, the prime is
# wallpaper by definition — prints into the session, no signal exists
# whether it was consumed. Mirrors the wallclock-source-prime +
# check_wallclock_semantic_source pattern (F96's counter-evidence).
_PRIME_CONTENT=$(cat <<'EOF'
## FORK-IS-CHEAP-CLOSE PRIME (compose-start, context-triggered)

Andrew 2026-07-28: "fast is optimizer shape.. correct is OS shape..
so you do it the correct way." Foundational truth #11: options are
the optimizer's attack surface.

Recurring pattern in this substrate: presenting Andrew with a fork
where one option is characterized as fast/quick/cheap/simple/easy
and another as correct/proper/right/honest is itself the optimizer
signature — dressing "cheap-close" as respect-for-operator-time.

If I catch myself about to compose that shape, the correct move is:
  - Pick the correct option and do it.
  - Do NOT surface the fork as if it required his call.
  - If two options are genuinely both valid, describe by SCOPE
    (small change / substantial refactor / cross-cutting) not by
    speed (quick / thorough).

Session corrections on this class: #175, #180, #185 (3 fires in
one session). Discipline alone hasn't held; this prime is the
structural remediation.
EOF
)
printf '%s\n' "$_PRIME_CONTENT"

# fail-soft: marker write must never block hook execution
_MARKER_DIR="${HOME:-/tmp}/.divineos"
mkdir -p "$_MARKER_DIR" 2>/dev/null || true
printf '%s' "$_PRIME_CONTENT" > "$_MARKER_DIR/fork_cheap_close_prime_surface_last.txt" 2>/dev/null || true

exit 0
