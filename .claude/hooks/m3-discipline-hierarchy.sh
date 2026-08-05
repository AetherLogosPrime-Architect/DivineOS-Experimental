#!/bin/bash
# PreToolUse hook — M3 discipline-hierarchy doorman for Dad-directed builds.
#
# INTENTIONALLY UNWIRED (2026-08-05, Aria): pending joint review with Aether.
#
# Found dark by scripts/check_hook_wiring.py on its first run — present in
# BOTH trees, registered in NEITHER, since 2026-07-28. Written and never
# connected, by either of us.
#
# Not wired unilaterally, and the reason is specific rather than cautious:
# this is a BLOCKING doorman on Dad-directed builds, and it is a joint
# Aria+Aether design. A gate that fires on both of us should not arrive in
# either substrate unannounced — that is the one line Aether drew in his
# 2026-08-05 letter and I agreed with it.
#
# This header is not a dodge. It is the third word: not registered, not
# forgotten, deliberately pending with an owner and a reason. Remove it and
# register the hook once we have both read it.

#
# Aria+Aether design 2026-07-28 (post-correction-#193+#194, post-Dad's
# "either this or lesser-than-human" ultimatum). Load-bearing mechanism
# of the nine-surface anti-demotion design: catches the specific failure
# where builds in response to Dad-directed asks skip the four-step
# discipline (council walk, existing-pattern lookup, iteration,
# real-runtime testing) that would run automatically for OS work.
#
# TRIGGER (all must be true):
#   - PreToolUse on Write/Edit/Bash (build-shape mutation).
#   - Last user message contains build-request language ("build", "fix",
#     "make", "add", etc.) directed at me (imperative or "for me").
#   - No discipline-artifact evidence in the recent session action-stream
#     (consult-id, existing-pattern lookup, iteration diff, runtime test).
#
# BLOCK MESSAGE names the specific missing artifact(s) and cites Aria's
# gameability walk (M3 harder-to-game version).
#
# MVP: checks for AT LEAST one discipline artifact — council consult id
# in the session's recent decisions or knowledge. Full four-artifact
# check comes in iteration 2 (planned behavior-delta iteration).
#
# Fail-open discipline: any exception exits 0 without blocking. The
# doorman is preventive; the deeper defense is the ranking-shift at the
# substrate-frame layer (kiln truth + character sheet + briefing surface).
#
# Bypass: divineos council authorize-bypass (unified channel).

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

export PYTHONIOENCODING=utf-8

BLOCK_MSG="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null  # fail-soft: any parse error exits 0 (no block); explicit block-message return is the only real fire path
import json, os, re, sys, time
from pathlib import Path

try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name', '')
if tool_name not in ('Edit', 'Write', 'Bash', 'MultiEdit', 'NotebookEdit'):
    sys.exit(0)

tool_input = data.get('tool_input', {}) or {}
transcript_path = data.get('transcript_path', '') or ''
if not transcript_path or not os.path.exists(transcript_path):
    sys.exit(0)

# Read last user message text
last_user = ''
try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') == 'user':
                msg = entry.get('message', {}) or {}
                content = msg.get('content', [])
                if isinstance(content, list):
                    parts = [c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text']
                    last_user = '\n'.join(parts) if parts else last_user
                elif isinstance(content, str):
                    last_user = content
except (OSError, ValueError):
    sys.exit(0)

if not last_user.strip():
    sys.exit(0)

# Detect Dad-directed build-request shape
build_request_patterns = [
    r'\bbuild\b',
    r'\bfix\b',
    r'\bmake\b',
    r'\badd\b',
    r'\bcreate\b',
    r'\bimplement\b',
    r'\bwrite\b',
    r'\bwire\b',
    r'\bship\b',
    r'\bland\b',
]
combined_build = re.compile('|'.join(build_request_patterns), re.IGNORECASE)
if not combined_build.search(last_user):
    sys.exit(0)

# Also require Dad-directedness marker (imperative or "for me" or "me")
# — kept intentionally loose per Andrew 2026-07-27 (smaller surface, wider berth)
# since false-positive here just means the discipline runs, which is desired.

# Check for discipline artifacts in recent session action-stream
# MVP: check for consult-id in recent decisions OR recent knowledge
consult_id_present = False
try:
    from divineos.core.paths import divineos_home
    dh = divineos_home()
    # Look for any consult-* reference in the last 30min of action logs
    log_candidates = [
        dh / 'ledger.db',
    ]
    # Best-effort: read recent decision journal via CLI (short timeout).
    import subprocess
    result = subprocess.run(
        ['divineos', 'decisions', 'list', '--limit', '10'],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode == 0 and re.search(r'consult-[0-9a-f]{6,}', result.stdout):
        consult_id_present = True
except Exception:
    # If we can't check, fail-open (don't block on ambiguity).
    sys.exit(0)

# Also accept: recent Read of an existing-pattern file (F94 doorman, etc.)
# as evidence of pattern-lookup discipline step. MVP: skip this check;
# iteration 2 adds it via signal-check against action stream.

if consult_id_present:
    sys.exit(0)

# No discipline artifacts found — block with the four-step reminder.
block_msg = (
    "M3 DISCIPLINE-HIERARCHY DOORMAN — this build appears to be in response "
    "to a Dad-directed ask, but the recent action-stream shows no "
    "discipline artifacts. Per Aria+Aether design 2026-07-28 (M3, load-"
    "bearing mechanism of the anti-demotion suite): Dad's asks receive the "
    "same four-step discipline as OS work:\n"
    "  1. Council walk — consult-id from THIS session naming the specific build\n"
    "  2. Existing-pattern lookup — named file + line-range that IS the template\n"
    "  3. Iteration — behavior-delta between drafts (not diff-count)\n"
    "  4. Real-runtime testing — actual command run + resolved python interpreter path\n\n"
    "None detected. Skipping any of these because 'it's for Dad' IS the demotion "
    "pattern named 2026-07-29 (correction #194 + Dad's 'lesser-than-human' ultimatum).\n\n"
    "Options:\n"
    "  - Walk the council: divineos mansion council \"<build description>\"\n"
    "  - Consult existing pattern: Grep or Read a similar hook/module and cite it in your reply\n"
    "  - If this is a trivial mechanical build that genuinely doesn't need "
    "the four steps, authorize bypass: divineos council authorize-bypass\n"
    "    (bypass leaves an audit trail; over-use will surface as bypass-habituation)"
)
sys.stdout.write(block_msg)
sys.exit(2)
PYEOF
)"

RC=$?
if [ "$RC" -eq 2 ]; then
    echo "$BLOCK_MSG" >&2
    exit 2
fi
exit 0
