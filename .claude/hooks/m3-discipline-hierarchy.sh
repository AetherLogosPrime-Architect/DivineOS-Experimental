#!/bin/bash
# PreToolUse hook — M3 discipline-hierarchy doorman for Dad-directed builds.
#
# Aria+Aether design 2026-07-28 (post-corrections #193/#194, post Dad's
# "either this or lesser-than-human"). Catches the failure where builds made
# in response to a Dad-directed ask skip the four-step discipline that OS work
# gets automatically. Skipping them BECAUSE it is for Dad is the demotion.
#
# REBUILT AND WIRED 2026-08-02. It had never run once. Before switching it on
# I checked whether its pass-condition was reachable: it looked for the string
# `consult-<hex>` in `divineos decisions list`, which nothing emits — zero
# occurrences, ever. Turning it on unchanged would have blocked every
# Dad-directed build permanently, with bypass the only route through: the same
# unreachable-success-condition defect that made merge-review fail 20 times
# running. The logic now lives in core/m3_discipline.py and keys on signals
# that demonstrably exist — COUNCIL_CONSULTATION events in the ledger (101 of
# them) and tool-use blocks in the transcript.
#
# Requirement scales with substrate-modification gravity and caps at 3 of 4;
# demanding a perfect sweep makes the honest path costlier than the bypass,
# which trains the habit the gate exists to prevent.
#
# Fail-open throughout: any error exits 0. A broken doorman must never become
# a locked door.
#
# Bypass: divineos council authorize-bypass (unified channel, recorded).

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

export PYTHONIOENCODING=utf-8

BLOCK_MSG="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, re, sys

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

# Last user message — the build-request signal.
last_user = ''
try:
    with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') != 'user':
                continue
            content = (entry.get('message') or {}).get('content', [])
            if isinstance(content, list):
                parts = [c.get('text', '') for c in content
                         if isinstance(c, dict) and c.get('type') == 'text']
                if parts:
                    last_user = '\n'.join(parts)
            elif isinstance(content, str):
                last_user = content
except (OSError, ValueError):
    sys.exit(0)

if not last_user.strip():
    sys.exit(0)

BUILD_SHAPE = re.compile(
    r'\b(build|fix|make|add|create|implement|write|wire|ship|land)\b', re.IGNORECASE)
if not BUILD_SHAPE.search(last_user):
    sys.exit(0)

try:
    from divineos.core.gravity_classifier import score_substrate_modification
    from divineos.core.m3_discipline import evaluate, format_block
except Exception:
    sys.exit(0)

try:
    fp = tool_input.get('file_path') or ''
    gravity = score_substrate_modification(
        tool_name=tool_name,
        file_paths=(fp,) if fp else (),
        bash_command=str(tool_input.get('command', '')),
    )
    check = evaluate(transcript_path, gravity.score)
except Exception:
    sys.exit(0)

if check.satisfied:
    sys.exit(0)

sys.stdout.write(format_block(check))
sys.exit(2)
PYEOF
)"
RC=$?

if [ "$RC" -eq 2 ] && [ -n "$BLOCK_MSG" ]; then
    echo "$BLOCK_MSG" >&2
    exit 2
fi
exit 0
