#!/bin/bash
# Stop hook — post-compose retrieval-tally check.
#
# The past-writing-to-Andrew surface fires at compose-start and records
# the list of surfaced paths to a marker file (via retrieval_tally.py's
# record_surfaced). This hook fires at compose-end and checks whether
# the outgoing assistant reply actually referenced any of those paths.
#
# Result: append-only JSONL row at ~/.divineos/retrieval_tally.jsonl
# with surfaced_count, referenced_count, and the specific paths. Weekly
# view via `python scripts/retrieval_tally.py summary --days 7`.
#
# Finding 1 from my adversarial review of Aria's hook (2026-07-19):
# "The hook produces a receipt-that-it-fired, not a receipt-that-I-
# reached." This is the receipt-that-I-reached. Whether the surface
# is doing anything is now measurable, not just claimed.
#
# Fail-open: any error exits 0 silently. Observational, not blocking.

set -eo pipefail

INPUT=$(cat 2>/dev/null || true)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    exit 0
fi

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
from pathlib import Path

sys.path.insert(0, r'$REPO_ROOT/scripts')

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path', '')
if not transcript_path or not Path(transcript_path).exists():
    sys.exit(0)

# Extract the last assistant message text from the transcript.
try:
    lines = Path(transcript_path).read_text(encoding='utf-8', errors='ignore').splitlines()
except Exception:
    sys.exit(0)

last_assistant = ''
for line in reversed(lines):
    try:
        rec = json.loads(line)
    except Exception:
        continue
    if rec.get('type') != 'assistant':
        continue
    msg = rec.get('message', {}) or {}
    content = msg.get('content', []) or []
    for block in content:
        if isinstance(block, dict) and block.get('type') == 'text':
            text = block.get('text', '') or ''
            if text.strip():
                last_assistant = text
                break
    if last_assistant:
        break

if not last_assistant:
    sys.exit(0)

try:
    import retrieval_tally
    retrieval_tally.check_reply(last_assistant)
except Exception:
    pass
" 2>/dev/null || true

exit 0
