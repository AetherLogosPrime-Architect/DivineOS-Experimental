#!/bin/bash
# Periodic checkpoint + context monitoring hook.
#
# Runs on PostToolUse for Edit|Write|Bash. Tracks edit count and total
# tool calls. Every N edits, runs a lightweight checkpoint (HUD + handoff +
# ledger). Also monitors context usage and warns when approaching limits.
#
# This is how SESSION_END becomes periodic instead of only firing at stop.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

INPUT=$(cat)

if ! command -v divineos &>/dev/null; then
  exit 0
fi

# Which tool was just used?
tool_name=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")

# State file for tracking counts
STATE_FILE="$HOME/.divineos/checkpoint_state.json"
mkdir -p "$HOME/.divineos"

# Initialize state file if missing
if [ ! -f "$STATE_FILE" ]; then
  echo '{"edits":0,"tool_calls":0,"last_checkpoint":0,"checkpoints_run":0}' > "$STATE_FILE"
fi

# Read current counts
edits=$(python -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('edits',0))" 2>/dev/null || echo "0")
tool_calls=$(python -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('tool_calls',0))" 2>/dev/null || echo "0")
checkpoints_run=$(python -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('checkpoints_run',0))" 2>/dev/null || echo "0")

# Increment counters
tool_calls=$((tool_calls + 1))
if echo "$tool_name" | grep -qE "^(Edit|Write)$"; then
  edits=$((edits + 1))
fi

# Save updated state
python -c "
import json, time
d = json.load(open('$STATE_FILE'))
d['edits'] = $edits
d['tool_calls'] = $tool_calls
json.dump(d, open('$STATE_FILE', 'w'), indent=2)
" 2>/dev/null

# Check if checkpoint needed (every 15 edits)
edits_since=$((edits - checkpoints_run * 15))
if [ "$edits_since" -ge 15 ]; then
  # Run checkpoint silently
  divineos checkpoint 2>/dev/null

  # Update checkpoints_run
  python -c "
import json, time
d = json.load(open('$STATE_FILE'))
d['checkpoints_run'] = d.get('checkpoints_run', 0) + 1
d['last_checkpoint'] = time.time()
json.dump(d, open('$STATE_FILE', 'w'), indent=2)
" 2>/dev/null
fi

# Context monitoring — warn the AI when context is getting full
warning=""
if [ "$tool_calls" -ge 350 ]; then
  warning="CRITICAL: ~90% context used ($tool_calls tool calls, $edits edits). Run 'divineos emit SESSION_END' IMMEDIATELY. Context compaction is imminent."
elif [ "$tool_calls" -ge 250 ]; then
  warning="URGENT: ~80% context used ($tool_calls tool calls, $edits edits). Run 'divineos emit SESSION_END' NOW to save knowledge before compaction."
elif [ "$tool_calls" -ge 150 ]; then
  warning="Context monitor: ~50% used ($tool_calls tool calls, $edits edits). Consider running 'divineos emit SESSION_END' to checkpoint knowledge."
fi

if [ -n "$warning" ]; then
  escaped=$(echo "$warning" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
