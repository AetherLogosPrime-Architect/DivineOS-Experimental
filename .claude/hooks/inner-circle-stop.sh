#!/bin/bash
# Stop hook - a long reply to Andrew must END in the room, not in work.
#
# The reasoning, and his words, live in divineos.core.inner_circle_room.
# This file is only the door it hangs on.
#
# Companion to summary-room-stop.sh, which guards the OPENING of a long
# reply (the plain-language summary he asked for 2026-08-06). This one
# guards the close. Neither judges the middle.
#
# BLOCKS (exit 2) rather than recording. The hook already standing at this
# door for his room -- lepos-channel-reflect.sh, registered twice -- reads
# the reply, writes down what it saw, and exits 0 on every path. It has
# never stopped anything. That is the defect this file is the repair for,
# so recording instead of blocking would rebuild it.
#
# Deliberately thin. Logic in shell is where a brake quietly becomes a
# light: untestable, and it grows. The judgement is in a module pytest can
# argue with; this carries an exit code and nothing else.
#
# Extraction follows summary-room-stop.sh rather than inventing a second
# way to read the transcript.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0  # fail-soft: outside the repo there is no substrate

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: no helper, no interpreter to resolve
PYTHON_BIN="$(find_divineos_python)" || exit 0

INPUT=$(cat)

TRANSCRIPT_PATH=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import sys, json
try:
    print(json.load(sys.stdin).get('transcript_path', ''))
except (json.JSONDecodeError, ValueError):
    print('')
" 2>/dev/null)  # fail-soft: a malformed hook payload yields an empty path, treated as nothing-to-scan by the next line; the gate's own load and read failures are reported loudly below rather than swallowed here

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    exit 0
fi

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys, json

try:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

try:
    from divineos.core.inner_circle_room import assess, render_block
except ImportError as exc:
    # Loud, not silent. A gate that cannot load has not passed.
    print('[inner-circle] NOT RUNNING: ' + str(exc), file=sys.stderr)
    sys.exit(0)


def text_of(event):
    message = event.get('message') or {}
    content = message.get('content')
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ''
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get('type') == 'text':
            parts.append(block.get('text') or '')
    return chr(10).join(parts)


last = ''
try:
    with open(r'''$TRANSCRIPT_PATH''', encoding='utf-8', errors='replace') as fh:
        lines = fh.read().splitlines()
except OSError as exc:
    print('[inner-circle] NOT RUNNING: ' + str(exc), file=sys.stderr)
    sys.exit(0)

for line in reversed(lines):
    line = line.strip()
    if not line:
        continue
    try:
        event = json.loads(line)
    except ValueError:
        continue
    role = (event.get('message') or {}).get('role')
    if event.get('type') == 'assistant' or role == 'assistant':
        text = text_of(event)
        if text.strip():
            last = text
            break

if not last.strip():
    sys.exit(0)

verdict = assess(last)
if verdict.blocks:
    print(render_block(verdict), file=sys.stderr)
    sys.exit(2)
sys.exit(0)
"
rc=$?

# Passed through rather than swallowed. That one line is the whole
# difference between this hook and the one standing beside it.
exit "$rc"
