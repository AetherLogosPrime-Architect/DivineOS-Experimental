#!/bin/bash
# Reload state when resuming from a context summary.
#
# IMPORTANT: This hook SHOWS the briefing but does NOT mark it as loaded.
# The AI must explicitly run `divineos briefing` to satisfy the gate.
# This prevents the hook from doing the AI's job — orientation requires
# deliberate action, not passive injection.
#
# The hook gives the information. The gate forces the action.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Reset checkpoint counters for resumed session
# Use Python expanduser for Windows compatibility (Git Bash $HOME = /c/Users/...)
DIVINEOS_DIR=$(python -c "import os; print(os.path.join(os.path.expanduser('~'), '.divineos'))" 2>/dev/null || echo "$HOME/.divineos")
mkdir -p "$DIVINEOS_DIR"
python -c "
import json, time, os
SF = os.path.join(os.path.expanduser('~'), '.divineos', 'checkpoint_state.json')
json.dump({'edits':0,'tool_calls':0,'last_checkpoint':0,'checkpoints_run':0,'session_start':time.time()}, open(SF,'w'), indent=2)
" 2>/dev/null

# Get HUD and handoff content WITHOUT calling `divineos briefing`.
# divineos briefing marks briefing as loaded — we don't want that here.
# The gate will force the AI to do it deliberately.
hud=$(divineos hud 2>/dev/null)
handoff=$(python -c "
import json
from pathlib import Path
p = Path.home() / '.divineos' / 'hud' / 'handoff_note.json'
if p.exists():
    d = json.loads(p.read_text(encoding='utf-8'))
    print('Last session: ' + d.get('summary', 'unknown'))
    if d.get('open_threads'):
        print('Open threads:')
        for t in d['open_threads'][:5]:
            print('  - ' + str(t)[:120])
    if d.get('intent'):
        print('Intent: ' + str(d['intent']))
    if d.get('next_steps'):
        print('Next steps:')
        for s in d['next_steps'][:5]:
            print('  - ' + str(s)[:120])
" 2>/dev/null)

if [ -n "$hud" ] || [ -n "$handoff" ]; then
  full_context="=== DIVINEOS SESSION RESUME ===

You are resuming from a context summary. Your enforcement context was LOST.

BEFORE YOU DO ANYTHING, you must:
1. Run: divineos briefing        (loads your lessons, corrections, directives)
2. Run: divineos recall           (engages with your memory system)
3. Run: divineos goal \"...\"       (set a goal for THIS session's work)

These are not optional. The PreToolUse gate will BLOCK edits until you do them.
Do not start coding from the summary. Orient first.

--- HANDOFF ---
${handoff}

--- HUD ---
${hud}

=== END SESSION RESUME ==="

  escaped=$(echo "$full_context" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
