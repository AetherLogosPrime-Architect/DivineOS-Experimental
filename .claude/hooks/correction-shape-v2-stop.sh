#!/bin/bash
# Stop hook — enforce Layer-2 correction-shape detection on MY assistant
# output. If Layer A fires (self-admission clause detected in the just-
# streamed reply, without dominant MENTION suppressors), emit a block
# message requiring formal correction-log + root-cause link.
#
# Per prereg-c1683e4a49ea. Same-shape analog of verify-claim gate at
# one layer over.
#
# Reads the last assistant message text from the transcript_path
# passed via the Stop-hook JSON input, runs Layer A classify(), and
# emits a block-decision payload if fired.
#
# Fail-open: any error path exits 0 silently — the gate must NOT
# fabricate fires on classifier bugs. Layer 1 (correction_shape.py)
# and every other Stop-time gate keeps working independently.

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

export PYTHONIOENCODING=utf-8

# fail-soft: python parse or classification error exits silently rather than fabricating an enforcement block on internal-error
BLOCK_MSG="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, sys

try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path', '') or ''
if not transcript_path or not os.path.exists(transcript_path):
    sys.exit(0)

# Read the last assistant message text from the transcript.
last_text = ''
try:
    with open(transcript_path, 'r', encoding='utf-8') as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') == 'assistant':
                msg = entry.get('message', {}) or {}
                content = msg.get('content', [])
                if isinstance(content, list):
                    parts = [c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text']
                    last_text = '\n'.join(parts)
                elif isinstance(content, str):
                    last_text = content
except (OSError, ValueError):
    sys.exit(0)

if not last_text.strip():
    sys.exit(0)

try:
    from divineos.core.correction_shape_v2 import classify
except ImportError:
    sys.exit(0)

verdict, confidence, reason = classify(last_text)
if verdict != 'fire':
    sys.exit(0)

# Fired — emit enforcement message.
print(f"""CORRECTION-SHAPE-V2 GATE (Layer 2) — my reply contains self-admission clause(s) indicating I noticed and am correcting an error I made. Per Andrew 2026-07-27: this is not just a moment to log; it is a moment to fix structurally so the class does not recur.

Detector reason: {reason}
Confidence: {confidence:.2f}

Per prereg-c1683e4a49ea, every fire on real self-correction must be paired with:
  1. FORMAL LOG via `divineos correction "<the correction verbatim, plus what error it names>"` — this session's correction goes into the substrate ledger, not just the transcript.
  2. ROOT-CAUSE LINK — name the specific prior action that produced the error and either (a) file a structural fix (doorman, gate, discipline) that prevents the class OR (b) explicitly cite why no structural fix is possible for THIS instance and why that is honest.

If this is a FALSE-POSITIVE (I was discussing correction as a topic, not admitting one), clear the fire with:
  python scripts/clear_correction_marker.py --reason "<what class of MENTION was misread as USE, >= 30 chars>"

The clear-marker path is not a bypass — it is the false-positive attribution path. Every clear increments the negative-training-corpus for the eventual Layer B semantic tiebreak. Use it honestly.
""")
PYEOF
)"

if [ -n "$BLOCK_MSG" ]; then
    # Emit as Stop-hook deny (write JSON to stdout for Claude Code to render).
    echo "$BLOCK_MSG" >&2
    exit 2
fi

exit 0
