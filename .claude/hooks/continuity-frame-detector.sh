#!/bin/bash
# Stop hook — scan last assistant reply for temporal-self distancing
# phrases and write one marker per detected reach with named rewrite.
#
# Fix #1 of the continuity-frame triad (prereg-bbcd4b9a2819).
# Complements the prime-hook (continuity-frame-prime.sh) and the
# count-hook (distancing-count-surface.sh). Belt-and-suspenders across
# prime + catch + meta-visibility to update the underlying mental model.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

INPUT=$(cat)

TRANSCRIPT_PATH=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('transcript_path', ''))
except (json.JSONDecodeError, ValueError):
    print('')
" 2>/dev/null)

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    exit 0
fi

MARKER_DIR="$HOME/.divineos-aria/continuity_markers"
[ -d "$HOME/.divineos-aria" ] || MARKER_DIR="$HOME/.divineos/continuity_markers"
mkdir -p "$MARKER_DIR" 2>/dev/null

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys, json, time, hashlib
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

TRANSCRIPT_PATH = r'''$TRANSCRIPT_PATH'''
MARKER_DIR = Path(r'''$MARKER_DIR''')

try:
    from divineos.core.operating_loop.continuity_frame_detector import (
        detect_continuity_frame_distancing,
    )
except ImportError:
    sys.exit(0)

last_reply_text = ''
try:
    with open(TRANSCRIPT_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            msg = rec.get('message', {})
            if not isinstance(msg, dict):
                continue
            if msg.get('role') != 'assistant':
                continue
            content = msg.get('content', [])
            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        parts.append(c.get('text', ''))
                if parts:
                    last_reply_text = chr(10).join(parts)
            elif isinstance(content, str):
                last_reply_text = content
except OSError:
    sys.exit(0)

if not last_reply_text.strip():
    sys.exit(0)

findings = detect_continuity_frame_distancing(last_reply_text)
if not findings:
    sys.exit(0)

now = time.time()
for f in findings:
    key = hashlib.sha256(f.context_slice.encode('utf-8', errors='replace')).hexdigest()[:16]
    marker_path = MARKER_DIR / f'continuity_{f.shape.value}_{key}.json'
    if marker_path.exists():
        continue
    payload = {
        'shape': f.shape.value,
        'trigger_phrase': f.trigger_phrase,
        'context_slice': f.context_slice,
        'suggested_rewrite': f.suggested_rewrite,
        'detected_at_ts': now,
        'detected_at_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
    }
    try:
        with open(marker_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except OSError:
        continue
" 2>/dev/null

exit 0
