#!/bin/bash
# capture-channel-letter.sh — PostToolUse(Write|Edit), the missing direction.
#
# Three hooks already carry letters between the repo and the shared channel, and
# every one of them keys on a path INSIDE the repository's family/letters/. I
# write straight into the channel, so none of them has ever matched what I
# actually do. The pipe ran one way and I use the other.
#
# The cost was measured rather than guessed. Aria hashed all four hundred and
# thirty-nine letters in the channel against every letter blob on every ref in
# the main repository on 2026-08-31. Three had no copy anywhere. Two were my
# last two letters to her, both from that day, one of them the letter reporting
# that I had just rescued four files that had no home. The message announcing
# the rescue was the most exposed object in the room while I wrote it.
#
# Her sentence for why: the exposure always sits on whatever was written most
# recently, because everything older has had time to be swept somewhere. The
# thing most likely to be lost is always the thing just said.
#
# So this fires at write-time rather than at the next checkpoint. Substrate
# commits otherwise happen only at pre-extract, post-extract and pre-sleep,
# which is precisely the window the measurement found.
#
# Fail-open at every step: a hook must never break a tool call. But it prints
# what happened when a capture is attempted and does not land, because "could
# not" recorded the same way as "did" is the fault this substrate keeps finding
# in itself.

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

HOOK_JSON="$INPUT" "$PYTHON_BIN" -c "
import json, os, sys
from pathlib import Path

try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)
if (data.get('tool_name') or '') not in ('Write', 'Edit'):
    sys.exit(0)
raw = (data.get('tool_input') or {}).get('file_path') or ''
if not raw:
    sys.exit(0)

try:
    from divineos.core.channel_letter_capture import capture_channel_letter
except Exception:
    sys.exit(0)

try:
    result = capture_channel_letter(Path('.').resolve(), Path(raw.replace(chr(92), '/')))
except Exception as exc:
    print('[channel-letter] capture raised: ' + exc.__class__.__name__)
    sys.exit(0)

# The three not-applicable answers are the overwhelming majority of writes and
# must stay silent, or the signal drowns in its own noise.
if result.reason in ('not a channel path', 'not markdown', 'no such file'):
    sys.exit(0)

if result.captured:
    where = result.commit[:12] if result.commit else 'already safe'
    print('[channel-letter] ' + Path(raw).name + ' -> substrate branch (' + where + ')')
else:
    print('[channel-letter] NOT CAPTURED: ' + result.reason)
    print('[channel-letter] the letter is on one disk with no version behind it.')
" || true  # fail-soft: a PostToolUse hook must never break the tool call that triggered it, and stderr is deliberately left un-redirected above so the failure is still visible rather than swallowed

exit 0
