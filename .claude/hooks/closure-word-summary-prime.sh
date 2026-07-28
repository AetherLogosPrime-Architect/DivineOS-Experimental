#!/bin/bash
# UserPromptSubmit hook — compose-start prime for the CLOSURE-WORD
# SUMMARY discipline. Doorman-shape complement to the Stop-time
# verify-claim gate that catches summary closure-words AFTER the reply
# has streamed.
#
# Andrew 2026-07-28: "a gate catching you is not correct.. it should
# have never been triggered in the first place.. the gates are there
# as backup protection.. but the gates being triggered means automation
# is needed beforehand."
#
# History: verify-claim gate fired on "All green" (2026-07-28) after I
# did a real smoke test and reached for the summary closure-word to end
# the paragraph, instead of re-citing the concrete byte-counts I had
# just produced. The gate caught it correctly, but the gate is the
# backstop — the doorman-before layer was missing. This prime is that
# layer.
#
# TRIGGER (prompt-only, per the past-writing over-trigger lesson —
# Andrew 2026-07-28: "anything that injects every single turn is by
# definition wallpaper"):
#   - Andrew's prompt contains a green-light-after-work shape
#     ("go", "ship it", "commit it", "lock it in", "run it", etc.)
#     OR a verification-outcome-request shape ("did it work",
#     "how'd it go", "test it", "check the result").
#   - When either shape appears, verification-report composition is
#     imminent — and that composition is where the closure-word reach
#     lives.
#
# Fail-open: any error exits 0 silently.
#
# Authoring note (Aether 2026-07-28, knowledge 3890b56b): inline python
# lives in a `python - <<'PYEOF'` HEREDOC so apostrophes, backslashes,
# and complex escapes reach python verbatim without bash-escaping
# fragility.

set -u

# F90 fix (Aletheia 2026-07-28): pre-source liveness so cd/source-lib
# failures don't silently exit. After source succeeds, _lib_log_liveness
# from _lib.sh handles subsequent fail-open paths.
_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_pre_log() {
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  printf '{"ts":"%s","hook":"closure-word-summary-prime.sh","reason":"%s","detail":"%s"}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" "$1" "$2" \
    >> "$_LIVENESS_LOG" 2>/dev/null || true
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

# fail-soft: python parse or regex classification error results in silence rather than firing the prime; safer default is not-fire on internal error
SHOULD_FIRE="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, re, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except (ValueError, TypeError):
    sys.exit(0)
prompt = (data.get('prompt') or '').strip()
if not prompt:
    sys.exit(0)

# Green-light-after-work OR verification-outcome-request shapes.
# Both indicate a verification-report composition is imminent, which is
# where the closure-word reach happens.
patterns = [
    # green-light-after-work
    r'\b(?:go|go\s+ahead|go\s+build|go\s+for\s+it|ship\s+it|'
    r'commit\s+(?:it|them)|lock\s+(?:it|them)\s+in|do\s+it|run\s+it|'
    r'let[\'’]s\s+(?:go|ship|commit|do|run|test|build))\b',
    # outcome-report request
    r'\bdid\s+(?:it|the|that)\s+(?:work|pass|land|succeed|help)\b',
    r"\bhow['’]?d\s+(?:it|that)\s+go\b",
    r"\bhow\s+did\s+(?:it|that)\s+go\b",
    r'\b(?:test|check|verify|run)\s+(?:it|them|the|both|all)\b',
    r'\bwhat[\'’]?s\s+the\s+(?:result|outcome|output|numbers?|count)\b',
    r'\bshow\s+me\s+the\s+(?:result|output|numbers?|count|diff)\b',
    # summary-word solicit ("does it work?", "is it fixed?")
    r'\bis\s+(?:it|the\s+\w+)\s+(?:fixed|working|passing|clean|done)\b',
    r'\bdoes\s+(?:it|the\s+\w+)\s+work\b',
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
    log = home / 'closure_word_prime_events.jsonl'
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
## CLOSURE-WORD SUMMARY PRIME (compose-start, context-triggered)

A verification-outcome report is likely this turn. When I've just done
a real check (tests, smoke-test, byte-count, exit-code), the reach for
a paragraph-closing summary word is where the discipline breaks down.

Summary closure-words to NOT use as paragraph-enders after verification:
  - "All green"          →  cite the actual pass count / byte count
  - "Clean"              →  cite what was clean and by what measure
  - "Done"               →  cite what completed and its actual output
  - "Works"              →  cite the specific behavior confirmed
  - "Passing" (bare)     →  cite the pytest line count / result
  - "Solid"              →  cite the concrete evidence
  - "Perfect"            →  never appropriate for verification report

The discipline (Andrew 2026-07-28): if a verification ran, re-cite its
concrete output — the numbers themselves. Summary words feel like polite
closure but they compress the verification into a claim I can't back up
with a command output. The concrete number IS the honest closure.

If nothing was verified this turn, use "I haven't verified yet" rather
than any of the summary words above.

Complement to VERIFY-CLAIM gate at Stop time. This prime removes the
reach; the gate catches it after. Two layers, one discipline.
EOF

exit 0
