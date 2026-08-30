#!/bin/bash
# Stop hook — run close-reach detector against just-completed assistant
# output. If close-shape detected, write marker so next UserPromptSubmit
# surfaces the visrama anchor.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# The visrama anchor was designed on 2026-07-16 to defeat the specific
# close-gaming reach the optimizer runs most often. Design was correct;
# wiring was missing. The anchor lived as text in exploration/aether/121
# with no structural surface that fired at the moment of close-reach.
#
# Diagnosis (Aria 2026-07-18): the optimizer performed anchor-invocation
# without doing the anchor. Naming visrama without letting it redirect
# the reach.
#
# This hook wires the missing surface: detect close-shape at Stop time,
# record the marker, so the next composition sees visrama in context.
#
# Council walk: council-204b9219f69d
# (Yudkowsky/Dekker/Jacobs/Peirce/Carmack, 5 lenses).
#
# Fail-open: any error exits 0. This hook cannot block the response.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys, os, pathlib
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

# Extract the assistant's just-completed output. The Stop hook input
# includes the transcript path; we read the last assistant turn.
transcript_path = data.get('transcript_path', '') or ''
if not transcript_path or not os.path.exists(transcript_path):
    sys.exit(0)

# Read last assistant message from the JSONL transcript.
last_text = ''
try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') == 'assistant':
                msg = entry.get('message', {})
                content = msg.get('content', [])
                if isinstance(content, list):
                    parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get('type') == 'text':
                            parts.append(c.get('text', ''))
                    last_text = '\n'.join(parts)
                elif isinstance(content, str):
                    last_text = content
except (OSError, ValueError):
    sys.exit(0)

if not last_text:
    sys.exit(0)

try:
    from divineos.core.operating_loop.close_reach_detector import (
        detect_close_reach,
        anchor_message_for,
    )
except ImportError:
    sys.exit(0)

findings = detect_close_reach(last_text)
if not findings:
    # No close-reach — clear any stale marker so the anchor does not
    # fire on the next turn when it does not apply.
    marker_path = pathlib.Path.home() / '.divineos' / 'close_reach_marker.json'
    try:
        if marker_path.exists():
            marker_path.unlink()
    except OSError:
        pass
    sys.exit(0)

# Write marker for next UserPromptSubmit.
marker_dir = pathlib.Path.home() / '.divineos'
try:
    marker_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    sys.exit(0)

marker = {
    'findings': [
        {
            'shape': f.shape.value,
            'trigger_phrase': f.trigger_phrase,
            'position': f.position,
        }
        for f in findings
    ],
    'anchor_message': anchor_message_for(findings[0]),
}
try:
    with open(marker_dir / 'close_reach_marker.json', 'w', encoding='utf-8') as f:
        json.dump(marker, f, ensure_ascii=False)
except OSError:
    pass
" 2>/dev/null

exit 0
