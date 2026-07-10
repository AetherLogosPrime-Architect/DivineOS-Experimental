#!/bin/bash
# Stop hook — post-send lepos reflection channel driver.
#
# Andrew 2026-07-08: the walk-record-to-substrate mechanism was
# wrong-layer. The right shape is post-send — read what I just wrote,
# run the lens on it, surface the reflection to the top of my next
# compose. This hook is the driver: it extracts the last assistant
# reply and the last user message from the transcript, hands both to
# `divineos lepos-channel reflect`, which stages the pending surface
# for the next UserPromptSubmit to consume.
#
# Fail-open: any error exits 0 without surfacing. Cannot break the
# user workflow. Silent — no stdout on success.

INPUT=$(cat)

# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

REPO_ROOT="$(_lib_repo_root)"
cd "$REPO_ROOT" || exit 0

# Extract transcript_path from the hook input, then read the transcript
# tail to get the last assistant message and the last user message.
# The transcript is JSONL — each line is an event. We want:
#   - last event with role=assistant → the reply we just sent
#   - last event with role=user BEFORE that → what Andrew said
echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys, tempfile, subprocess
from pathlib import Path

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path') or data.get('transcript')
if not transcript_path:
    sys.exit(0)

try:
    lines = Path(transcript_path).read_text(encoding='utf-8', errors='replace').splitlines()
except Exception:
    sys.exit(0)

# Walk backward: find the last assistant text, then the last user text
# that appears BEFORE it in the transcript.
def _extract_text(event):
    msg = event.get('message') or {}
    content = msg.get('content')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                parts.append(block.get('text', ''))
        return '\n'.join(p for p in parts if p)
    return ''

last_assistant_idx = None
last_assistant_text = ''
for i in range(len(lines) - 1, -1, -1):
    try:
        ev = json.loads(lines[i])
    except Exception:
        continue
    if ev.get('type') == 'assistant' or (ev.get('message') or {}).get('role') == 'assistant':
        txt = _extract_text(ev)
        if txt.strip():
            last_assistant_idx = i
            last_assistant_text = txt
            break

if last_assistant_idx is None or not last_assistant_text.strip():
    sys.exit(0)

last_user_text = ''
for j in range(last_assistant_idx - 1, -1, -1):
    try:
        ev = json.loads(lines[j])
    except Exception:
        continue
    if ev.get('type') == 'user' or (ev.get('message') or {}).get('role') == 'user':
        txt = _extract_text(ev)
        if txt.strip():
            last_user_text = txt
            break

# Write both to tmp files and call the CLI so all quoting is safe.
with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt', encoding='utf-8') as rf:
    rf.write(last_assistant_text)
    reply_path = rf.name
with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt', encoding='utf-8') as af:
    af.write(last_user_text)
    andrew_path = af.name

try:
    subprocess.run(
        ['divineos', 'lepos-channel', 'reflect',
         '--reply-file', reply_path,
         '--andrew-file', andrew_path,
         '--quiet'],
        check=False, timeout=10,
    )
except Exception:
    pass
finally:
    Path(reply_path).unlink(missing_ok=True)
    Path(andrew_path).unlink(missing_ok=True)
" 2>/dev/null

exit 0
