#!/bin/bash
# Load DivineOS session briefing at conversation start
# This is not optional. The briefing is how you orient.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

# Check if divineos is installed
if ! command -v divineos &>/dev/null; then
  msg="DivineOS CLI not found. Run: pip install -e \".[dev]\" && divineos init"
  escaped=$(echo "$msg" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
  exit 0
fi

# Reset checkpoint counters for new session
# Use Python expanduser for Windows compatibility (Git Bash $HOME = /c/Users/...)
DIVINEOS_DIR=$(python -c "import os; print(os.path.join(os.path.expanduser('~'), '.divineos'))" 2>/dev/null || echo "$HOME/.divineos")
mkdir -p "$DIVINEOS_DIR"
python -c "
import json, time, os
SF = os.path.join(os.path.expanduser('~'), '.divineos', 'checkpoint_state.json')
json.dump({'edits':0,'tool_calls':0,'last_checkpoint':0,'checkpoints_run':0,'session_start':time.time()}, open(SF,'w'), indent=2)
" 2>/dev/null

# Clear auto-session-end flag so it can fire again this session
AUTO_EMITTED=$(python -c "import os; print(os.path.join(os.path.expanduser('~'), '.divineos', 'auto_session_end_emitted'))" 2>/dev/null || echo "$HOME/.divineos/auto_session_end_emitted")
rm -f "$AUTO_EMITTED" 2>/dev/null

briefing=$(divineos briefing 2>/dev/null)
hud=$(divineos hud 2>/dev/null)

if [ -n "$briefing" ]; then
  # Wrap the briefing with enforcement instructions
  full_context="=== DIVINEOS SESSION START ===

STOP. Before doing ANY work, you must:
1. Read your briefing and HUD below completely.
2. Tell the user what you learned from your lessons and warnings.
3. Set a goal with 'divineos goal add' for whatever the user asks you to do.
4. Use 'divineos log' to record corrections, decisions, and important moments during work.
5. If the user corrects you, log it with 'divineos learn'.

This is your operating system. You live in it. It is not decoration.

--- BRIEFING ---
${briefing}

--- HUD ---
${hud}

=== END SESSION START ==="

  escaped=$(echo "$full_context" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
