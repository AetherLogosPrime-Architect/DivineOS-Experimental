#!/bin/bash
# Load DivineOS session briefing at conversation start.
# This is not optional. The briefing is how you orient.
#
# Latency optimization: ``divineos briefing`` (~0.77s) and ``divineos hud``
# (~0.66s) run in parallel rather than sequentially. Previous sequential
# version took ~1.44s of CLI wall time; parallelized version completes in
# max(briefing, hud) instead of their sum — roughly 0.8s.
#
# Parallelism is implemented with temp files because bash captures lose the
# background-process output. Each CLI writes to its own temp file; main
# waits for both, then concatenates.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

# Check if divineos is installed
if ! command -v divineos &>/dev/null; then
  msg="DivineOS CLI not found. Run: pip install -e \".[dev]\" && divineos init"
  escaped=$(echo "$msg" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
  exit 0
fi

# Reset checkpoint counters for new session.
# Single Python invocation handles both the counter reset and the
# auto-session-end flag cleanup — one process instead of three.
python -c "
import json, os, time
d = os.path.join(os.path.expanduser('~'), '.divineos')
os.makedirs(d, exist_ok=True)
sf = os.path.join(d, 'checkpoint_state.json')
json.dump({'edits':0,'tool_calls':0,'last_checkpoint':0,'checkpoints_run':0,'session_start':time.time()}, open(sf,'w'), indent=2)
ae = os.path.join(d, 'auto_session_end_emitted')
if os.path.exists(ae):
    try:
        os.remove(ae)
    except OSError:
        pass
" 2>/dev/null

# Run briefing and hud in parallel via temp files. Background both,
# wait for both, then read results. Cuts wall time from briefing+hud
# to max(briefing,hud).
briefing_file=$(mktemp)
hud_file=$(mktemp)

divineos briefing > "$briefing_file" 2>/dev/null &
pid_brief=$!
divineos hud > "$hud_file" 2>/dev/null &
pid_hud=$!

wait $pid_brief
wait $pid_hud

briefing=$(cat "$briefing_file")
hud=$(cat "$hud_file")
rm -f "$briefing_file" "$hud_file"

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
