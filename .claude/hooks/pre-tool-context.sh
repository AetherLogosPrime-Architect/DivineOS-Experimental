#!/bin/bash
# PreToolUse hook — mid-turn substrate re-prime.
#
# Fires before Edit/Read/Write on source files. Surfaces the timeline
# of prior work on that specific file path (last edits, related
# corrections, decisions filed against the file) so the agent isn't
# operating from raw context window only when the work focus shifts
# mid-turn.
#
# Companion to UserPromptSubmit / pre-response-context.sh: that hook
# fires once per turn on user input; this one fires on every relevant
# tool call. Together: continuous memory-surfacing rather than session-
# boundary-only.
#
# Throttled: skips repeat fires on the same file within 60 seconds so
# a tight edit/read loop doesn't spam the surface file. Writes to
# ~/.divineos/mid_turn_context.md (separate from surfaced_context.md
# so the per-turn surface stays intact).
#
# Fail-open: any error exits 0 without blocking.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

if ! command -v python &>/dev/null; then
  exit 0
fi

echo "$INPUT" | python -c "
import json, sys, time
from pathlib import Path

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name', '')
if tool_name not in ('Edit', 'Read', 'Write', 'NotebookEdit'):
    sys.exit(0)

tool_input = data.get('tool_input', {}) or {}
file_path = (
    tool_input.get('file_path')
    or tool_input.get('notebook_path')
    or ''
)
if not file_path:
    sys.exit(0)

# Only surface for source-shaped files
if not any(file_path.lower().endswith(ext) for ext in (
    '.py', '.md', '.sh', '.json', '.yml', '.yaml', '.toml', '.sql', '.ipynb'
)):
    sys.exit(0)

# Throttle: skip if we already surfaced this file in the last 60s
state_dir = Path.home() / '.divineos'
state_dir.mkdir(exist_ok=True)
throttle_path = state_dir / 'mid_turn_throttle.json'

now = time.time()
throttle = {}
if throttle_path.exists():
    try:
        throttle = json.loads(throttle_path.read_text(encoding='utf-8'))
    except Exception:
        throttle = {}

last = throttle.get(file_path, 0)
if now - last < 60:
    sys.exit(0)

# Update throttle (best-effort)
throttle[file_path] = now
# Trim throttle to last 50 entries to keep the file small
if len(throttle) > 50:
    sorted_items = sorted(throttle.items(), key=lambda kv: -kv[1])[:50]
    throttle = dict(sorted_items)
try:
    throttle_path.write_text(json.dumps(throttle), encoding='utf-8')
except Exception:
    pass

# Run timeline recall
try:
    from divineos.core.memory_types import recall_timeline, format_timeline
except Exception:
    sys.exit(0)

# Use just the basename for the topic — file paths have repo prefixes
# that won't match historical references in ledger payloads.
file_basename = Path(file_path).name

try:
    events = recall_timeline(
        topic=file_basename,
        file_path=file_basename,
        per_source_limit=3,
        total_limit=8,
    )
except Exception:
    sys.exit(0)

surface_path = state_dir / 'mid_turn_context.md'

if not events:
    # Quiet: clear any prior mid-turn surface so it doesn't leak
    if surface_path.exists():
        try:
            surface_path.unlink()
        except Exception:
            pass
    sys.exit(0)

header = (
    f'# Mid-turn re-prime — prior work on \`{file_basename}\`\n\n'
    f'_Auto-surfaced by PreToolUse on {tool_name}. Read before deciding '
    f'how to handle this file._\n\n'
)
try:
    surface_path.write_text(header + format_timeline(events), encoding='utf-8')
except Exception:
    pass
" 2>/dev/null

exit 0
