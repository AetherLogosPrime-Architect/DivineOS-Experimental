#!/bin/bash
# Stop hook — evaluate my final assistant output for hedge density.
#
# When the Stop event fires (end of my turn), this hook reads the latest
# assistant message from the session transcript, passes it through
# divineos.core.self_monitor.hedge_monitor.evaluate_hedge, and if the
# verdict has >= 2 hedge flags, writes a marker at
# ~/.divineos/hedge_unresolved.json. The PreToolUse gate reads this
# marker and blocks non-bypass tools until a claim is filed.
#
# Closes the enforcement gap: hedging without claim-filing used to be
# an intent; now it's structural.
#
# Fail-open: any error exits 0 without blocking. This hook cannot break
# the user's workflow.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

if ! command -v python &>/dev/null; then
  exit 0
fi

echo "$INPUT" | python -c "
import json, sys, os
from pathlib import Path

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

# Locate the transcript file. Stop hooks pass transcript_path in the payload.
transcript_path = data.get('transcript_path') or data.get('transcript')
if not transcript_path:
    sys.exit(0)

p = Path(transcript_path)
if not p.exists():
    sys.exit(0)

# Read the last assistant message from the JSONL transcript.
last_assistant_text = ''
try:
    with open(p, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get('type') == 'assistant':
                # Extract text content — try both direct and nested message shapes.
                msg = rec.get('message', rec)
                content = msg.get('content', [])
                if isinstance(content, list):
                    texts = [
                        c.get('text', '')
                        for c in content
                        if isinstance(c, dict) and c.get('type') == 'text'
                    ]
                    if texts:
                        last_assistant_text = '\n'.join(texts)
                elif isinstance(content, str):
                    last_assistant_text = content
except Exception:
    sys.exit(0)

if not last_assistant_text or len(last_assistant_text) < 200:
    # Too short for density-based hedge detection to fire meaningfully.
    sys.exit(0)

# Evaluate hedge density on the last assistant message.
try:
    from divineos.core.self_monitor.hedge_monitor import evaluate_hedge
    from divineos.core.hedge_marker import set_marker, threshold
except Exception:
    sys.exit(0)

try:
    verdict = evaluate_hedge(last_assistant_text)
    flags = getattr(verdict, 'flags', []) or []
    if len(flags) >= threshold():
        kinds = [getattr(f, 'kind', type(f).__name__) for f in flags]
        # kind may be enum; coerce to string
        kinds = [str(k).split('.')[-1] if hasattr(k, 'name') or '.' in str(k) else str(k) for k in kinds]
        preview = last_assistant_text[:300]
        set_marker(len(flags), kinds, preview)
except Exception:
    pass
" 2>/dev/null

exit 0
