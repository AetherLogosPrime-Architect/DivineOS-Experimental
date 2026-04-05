#!/bin/bash
# Periodic checkpoint + context monitoring hook.
#
# Runs on PostToolUse for Edit|Write|Bash. Tracks edit count and total
# tool calls. Every N edits, runs a lightweight checkpoint (HUD + handoff +
# ledger). Also monitors context usage and warns when approaching limits.
#
# This is how SESSION_END becomes periodic instead of only firing at stop.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

INPUT=$(cat)

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Which tool was just used?
tool_name=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")

# State file for tracking counts
# Resolve path via Python for Windows compatibility (Git Bash $HOME = /c/Users/...
# which Python can't open; expanduser gives native C:\Users\... path)
DIVINEOS_DIR=$(python -c "import os; print(os.path.join(os.path.expanduser('~'), '.divineos'))" 2>/dev/null || echo "$HOME/.divineos")
STATE_FILE="$DIVINEOS_DIR/checkpoint_state.json"
mkdir -p "$DIVINEOS_DIR"

# Initialize state file if missing
if [ ! -f "$STATE_FILE" ]; then
  echo '{"edits":0,"tool_calls":0,"last_checkpoint":0,"checkpoints_run":0}' > "$STATE_FILE"
fi

# Read current counts
# NOTE: Use os.path.expanduser('~') instead of $HOME — on Windows, Git Bash
# sets $HOME to /c/Users/... which Python cannot open. expanduser resolves
# to the native C:\Users\... path that Python understands.
_SF="import os; SF=os.path.join(os.path.expanduser('~'),'.divineos','checkpoint_state.json')"
edits=$(python -c "$_SF; import json; d=json.load(open(SF)); print(d.get('edits',0))" 2>/dev/null || echo "0")
tool_calls=$(python -c "$_SF; import json; d=json.load(open(SF)); print(d.get('tool_calls',0))" 2>/dev/null || echo "0")
checkpoints_run=$(python -c "$_SF; import json; d=json.load(open(SF)); print(d.get('checkpoints_run',0))" 2>/dev/null || echo "0")

# Increment counters
tool_calls=$((tool_calls + 1))
if echo "$tool_name" | grep -qE "^(Edit|Write)$"; then
  edits=$((edits + 1))
fi

# Track code actions for periodic engagement gate.
# Every Edit/Write/Bash increments the counter. When it exceeds the
# threshold, the PreToolUse gate blocks until the AI consults the OS
# (ask, recall, decide, feel, context) which resets the counter.
python -c "
from divineos.core.hud_handoff import record_code_action
record_code_action()
" 2>/dev/null

# Save updated state
python -c "
import json, time, os
SF = os.path.join(os.path.expanduser('~'), '.divineos', 'checkpoint_state.json')
d = json.load(open(SF))
d['edits'] = $edits
d['tool_calls'] = $tool_calls
json.dump(d, open(SF, 'w'), indent=2)
" 2>/dev/null

# Check if checkpoint needed (every 15 edits)
edits_since=$((edits - checkpoints_run * 15))
if [ "$edits_since" -ge 15 ]; then
  # Run checkpoint silently
  divineos checkpoint 2>/dev/null

  # Update checkpoints_run
  python -c "
import json, time, os
SF = os.path.join(os.path.expanduser('~'), '.divineos', 'checkpoint_state.json')
d = json.load(open(SF))
d['checkpoints_run'] = d.get('checkpoints_run', 0) + 1
d['last_checkpoint'] = time.time()
json.dump(d, open(SF, 'w'), indent=2)
" 2>/dev/null
fi

# Self-awareness practice check — gentle nudge, not a gate.
# "You've been building for N tool calls without checking in."
practice_nudge=""
if [ "$tool_calls" -ge 100 ]; then
  practice_nudge=$(python -c "
from divineos.core.session_checkpoint import check_self_awareness_practice
result = check_self_awareness_practice($tool_calls)
if result:
    print(result)
" 2>/dev/null || echo "")
fi

# Context monitoring — warn the AI when context is getting full.
# At critical thresholds, AUTO-EMIT SESSION_END to save knowledge.
# Warnings alone are ignorable. Enforcement is not.
warning=""

# Check if we already auto-emitted (don't flood with repeated SESSION_ENDs)
# Use Python to resolve the path for Windows compatibility
AUTO_EMITTED_FILE=$(python -c "import os; print(os.path.join(os.path.expanduser('~'), '.divineos', 'auto_session_end_emitted'))" 2>/dev/null || echo "$HOME/.divineos/auto_session_end_emitted")

if [ "$tool_calls" -ge 150 ]; then
  # Auto-emit SESSION_END if we haven't already — save knowledge before it's lost
  if [ ! -f "$AUTO_EMITTED_FILE" ]; then
    divineos emit SESSION_END 2>/dev/null
    echo "1" > "$AUTO_EMITTED_FILE"
  fi
  warning="SESSION_END auto-emitted at $tool_calls tool calls. Knowledge saved. Continue working — compaction may happen soon."
elif [ "$tool_calls" -ge 100 ]; then
  warning="Context monitor: $tool_calls tool calls, $edits edits. SESSION_END will auto-emit at 150 to save knowledge."
fi

# Combine any warnings and nudges
combined=""
if [ -n "$practice_nudge" ]; then
  combined="$practice_nudge"
fi
if [ -n "$warning" ]; then
  if [ -n "$combined" ]; then
    combined="$combined | $warning"
  else
    combined="$warning"
  fi
fi

if [ -n "$combined" ]; then
  escaped=$(echo "$combined" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
