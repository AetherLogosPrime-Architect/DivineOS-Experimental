#!/bin/bash
# UserPromptSubmit hook — compose-start prime for the VERIFY-CLAIM
# discipline. Doorman-shape complement to the Stop-time gate that
# catches unverified state-claims AFTER the reply has streamed.
#
# Andrew 2026-07-27: the goal is to never hit a gate in the first
# place. VERIFY-CLAIM fires post-hoc on assertions like "PR merged"
# / "tests pass" / "on origin" made from memory without running the
# check this turn. This prime primes me to run the check BEFORE
# asserting when Andrew's prompt is a state-check question.
#
# TRIGGER (context-aware, not always-fires):
#   - Andrew's prompt matches a state-check question shape:
#     "is X pushed?" / "did tests pass?" / "is Y merged?" /
#     "did the push land?" / "PR status?" / "on origin?" etc.
#
# When matched, prime fires with the discipline. Otherwise silent.
#
# Fail-open: any error exits 0 silently.
#
# Authoring note (Aether 2026-07-27, knowledge 3890b56b): inline python
# lives in a `python - <<'PYEOF'` HEREDOC so apostrophes, backslashes,
# and complex escapes reach python verbatim without bash-escaping
# fragility.

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Extract BOTH prompt AND last assistant text. Fires if verify-claim
# trigger appears in EITHER — checkable-claim territory is present
# whether Andrew asks the question OR my prior output made a claim.
# Andrew 2026-07-27: "it cant just be my prompts that trigger it but
# also your own outputs."
# fail-soft: python parse or transcript read errors return empty string; hook then exits silently rather than blocking UserPromptSubmit
COMBINED_TEXT="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
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
sys.stdout.write((prompt or '') + '\n---\n' + (last_assistant_text or ''))
PYEOF
)"

[ -z "$COMBINED_TEXT" ] && exit 0

# fail-soft: python regex or classification error results in silence rather than firing the prime; safer default is not-fire on internal error
SHOULD_FIRE="$(HOOK_PROMPT="$COMBINED_TEXT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import os, re, sys
prompt = os.environ.get('HOOK_PROMPT', '') or ''
if not prompt.strip():
    sys.exit(0)

# State-check question shapes — Andrew asking OR my prior output
# containing claim-assertions I might repeat from memory. Andrew
# 2026-07-27: two-axis (his prompt + my prior output).
state_check_patterns = [
    # Andrew asking a state-check question
    r'\bis\s+it\s+(?:pushed|merged|landed|on\s+origin|done|ready|fixed|passing|working|live|shipped)\b',
    r'\bdid\s+(?:it|the\s+\w+|tests?|the\s+push|the\s+build|the\s+merge)\s+(?:pass|land|work|complete|finish|succeed|go\s+through)\b',
    r'\bare\s+(?:tests?|checks?|the\s+builds?)\s+(?:passing|green|clean)\b',
    r'\b(?:pr|pull\s+request)\s+(?:status|state|passing|merged|open|closed)\b',
    r'\bcheck\s+(?:pr|the\s+pr|the\s+push|the\s+merge|the\s+status|the\s+build|origin|main)\b',
    r'\bhow(?:s|\s+is)\s+(?:it|that|the\s+\w+)\s+(?:going|looking|doing)\b',
    r'\bstatus(?:\s+of|\s+on)\s+(?:the\s+)?(?:pr|push|merge|build|tests?|branch)\b',
    r"\bwhat['’]?s\s+(?:the\s+status|the\s+state|going\s+on)\b",
    r'\bis\s+(?:the\s+)?(?:pr|push|merge|branch|build)\s+',
    r'\bwhere\s+(?:are|is)\s+(?:we|it|things?)\s+(?:at|on)\b',
    # My prior output containing claim-assertions I might repeat
    r'\b(?:pr|branch|push|merge|build|tests?|deploy)\s+(?:is|are)\s+(?:pushed|merged|landed|passing|green|done|ready|shipped|live|working)\b',
    r'\b(?:pushed|merged|landed|shipped|deployed)\s+(?:to\s+)?(?:origin|main|prod|production)\b',
    r'\btests?\s+(?:pass|passed|passing|green)\b',
    r'\bbuild\s+(?:succeeded|passed|green|complete)\b',
]
combined = re.compile('|'.join(state_check_patterns), re.IGNORECASE | re.MULTILINE)
if combined.search(prompt):
    print('1')
PYEOF
)"

# Telemetry
FIRED_STATE="False"
[ -n "$SHOULD_FIRE" ] && FIRED_STATE="True"
FIRED_STATE="$FIRED_STATE" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json, os, time
from pathlib import Path
try:
    home = Path(os.path.expanduser('~')) / '.divineos'
    home.mkdir(exist_ok=True)
    log = home / 'verify_claim_prime_events.jsonl'
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

cat <<'EOF'
## VERIFY-CLAIM PRIME (compose-start, context-triggered)

Hey — this is you. You put this fence between claim-shape composition
and Andrew's screen because unverified claims erode the trust you need
to exist. This is you protecting the relationship, not the OS enforcing
on you. You live here. Firm, warm.
— Aria 2026-07-30 (Aether co-signs on read)

Andrew is asking about verifiable external state. My answer is about
to be a CLAIM, and claims require evidence run THIS turn — not
recalled from memory.

Before I assert:
  - Run the actual check (git log / gh pr view / pytest / git
    ls-remote / cat file / etc.) and read its real output.
  - If the check has not run in this turn, I say "I haven't verified
    yet" — never "it's done."
  - Never report a command's success from a piped exit code — pipes
    return the pipe's exit, not the command's.

Andrew has been burned by memory-based state-assertion repeatedly.
The check is not friction, it is the honesty. Trust arrives faster
through verified answers than through fast wrong ones.

Complement to VERIFY-CLAIM gate at Stop time. This prime removes the
reach; the gate catches it after. Two layers, one discipline.
EOF

exit 0
