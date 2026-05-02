#!/bin/bash
# UserPromptSubmit hook — auto-surface relevant prior content from the
# substrate based on markers in the user's latest message.
#
# Hook 1 of the operating loop (docs/operating-loop-design-brief.md).
# Closes the failure-shape Andrew caught 2026-05-01: substrate had the
# April 29 lunkhead-shape principle, agent never queried, operator had
# to remind. Now the substrate auto-queries on relational markers and
# writes the top-5 surfaced entries to ~/.divineos/surfaced_context.md
# for the agent to read at the start of its response.
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

# UserPromptSubmit payload includes 'prompt' field with the user's input.
prompt = data.get('prompt', '')
if not prompt or len(prompt) < 5:
    sys.exit(0)

# Run the context surfacer
try:
    from divineos.core.operating_loop.context_surfacer import (
        surface_context,
        format_surface,
    )
except Exception:
    sys.exit(0)

try:
    entries = surface_context(prompt, max_total_hits=5)
except Exception:
    sys.exit(0)

if not entries:
    # Nothing relevant — clear any prior surface so it doesn't leak forward.
    surface_path = Path.home() / '.divineos' / 'surfaced_context.md'
    if surface_path.exists():
        try:
            surface_path.unlink()
        except Exception:
            pass
    sys.exit(0)

# Write to ~/.divineos/surfaced_context.md
surface_dir = Path.home() / '.divineos'
surface_dir.mkdir(exist_ok=True)
surface_path = surface_dir / 'surfaced_context.md'
try:
    surface_path.write_text(format_surface(entries), encoding='utf-8')
except Exception:
    pass
" 2>/dev/null

exit 0
