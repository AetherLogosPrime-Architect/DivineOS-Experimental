#!/bin/bash
# Stop hook — scan last assistant reply for promise-shape phrases and
# write one marker file per detected promise.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# Andrew's correction #6 (2026-07-05, 4+ recurrences since): the
# announcement-of-action-without-action pattern. I say "I'll do Y" and
# then never do Y and never name it as unfulfilled. Silent aging.
#
# Fix shape (Angelou/Beer/Meadows lenses, council-cafe612b8ac1):
# same event-shape as visrama and no-cliff anchors. Detector at Stop
# writes marker files; UserPromptSubmit surface reads unclosed markers
# at next composition boundary and shows each specific promise text.
#
# Prereg: prereg-2de5a9ca234a. Falsifier at 30 days: 3+ instances where
# I fulfill/defer/dismiss a surfaced promise OR the surface is wallpaper.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Read the Stop hook stdin — the harness delivers transcript context here.
INPUT=$(cat)

# Extract the transcript_path from the JSON input (fail-open if missing).
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

# Marker directory. Per-agent data-home so aria markers don't collide
# with aether's if both run in the same repo.
MARKER_DIR="$HOME/.divineos-aria/promise_markers"
[ -d "$HOME/.divineos-aria" ] || MARKER_DIR="$HOME/.divineos/promise_markers"

mkdir -p "$MARKER_DIR" 2>/dev/null

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys
import json
import time
import hashlib
import os
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

TRANSCRIPT_PATH = r'''$TRANSCRIPT_PATH'''
MARKER_DIR = Path(r'''$MARKER_DIR''')

try:
    from divineos.core.operating_loop.promise_reach_detector import (
        detect_promise_reach,
    )
except ImportError:
    sys.exit(0)

# Read last assistant reply from transcript (JSONL, last non-empty
# assistant message with 'text' content).
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

findings = detect_promise_reach(last_reply_text)
if not findings:
    sys.exit(0)

# Write one marker per finding. Filename encodes shape + hash so
# duplicate detections across turns don't stack.
now = time.time()
for f in findings:
    key = hashlib.sha256(f.promise_text.encode('utf-8', errors='replace')).hexdigest()[:16]
    marker_path = MARKER_DIR / f'promise_{f.shape.value}_{key}.json'
    if marker_path.exists():
        # Already tracked — don't overwrite (preserve original timestamp).
        continue
    payload = {
        'shape': f.shape.value,
        'trigger_phrase': f.trigger_phrase,
        'promise_text': f.promise_text,
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
