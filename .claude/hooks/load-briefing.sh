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
# Single Python invocation handles counter reset, auto-session-end flag
# cleanup, and engagement-marker clearing — one process instead of three.
#
# Engagement-marker clearing moved here from the consolidation pipeline
# where it used to fire mid-session and block legitimate work. Semantic
# home: this hook fires at actual Claude Code SessionStart, which is the
# real "fresh context, force re-engagement" moment. See the engagement-
# gate-fix PR for the rationale.
python -c "
import json, os, time
from pathlib import Path

d = os.path.join(os.path.expanduser('~'), '.divineos')
os.makedirs(d, exist_ok=True)

# Reset per-session counters
sf = os.path.join(d, 'checkpoint_state.json')
json.dump({'edits':0,'tool_calls':0,'last_checkpoint':0,'checkpoints_run':0,'session_start':time.time(),'writes_since_consolidation':0}, open(sf,'w'), indent=2)

# Clear the consolidation idempotency marker (one extract per session)
ae = os.path.join(d, 'auto_session_end_emitted')
if os.path.exists(ae):
    try:
        os.remove(ae)
    except OSError:
        pass

# Clear the engagement marker — new Claude Code session = fresh context
# that needs re-engagement before editing. Semantic home for this clear.
# The marker lives in the project hud dir, not in ~/.divineos, so we
# need to import to find it. Wrapped in try so a startup-phase import
# failure doesn't block the rest of the hook.
try:
    from divineos.core.hud_handoff import clear_engagement
    clear_engagement()
except Exception:
    pass

# Clear any stale session plan. Same semantic: a plan set during a prior
# Claude Code session doesn't necessarily apply to this fresh session.
# Moved here from the consolidation pipeline where it used to fire
# mid-session and erase the user's active plan.
try:
    from divineos.core.hud_state import clear_session_plan
    clear_session_plan()
except Exception:
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

# Size threshold for the full injection. If the wrapped briefing+hud
# payload exceeds this, Claude Code may silently drop oversized
# additionalContext — so we fall back to a short nudge that at least
# tells the agent to run `divineos briefing` manually. The threshold is
# conservative (Anthropic does not publish the exact limit); adjust if
# observed behavior changes.
SIZE_THRESHOLD=15000

# Diagnostic log — one JSON line per SessionStart hook fire. Lets us
# tell after the fact whether the hook fired (and in what shape) for
# every session, including worktree spawns where injection may not land.
# Path is computed inside Python so Windows/Git-Bash path mismatches
# (e.g. /c/Users/... vs C:\Users\...) don't bite.

log_diag() {
  # $1=outcome (injected_full|injected_nudge|empty_briefing|no_cli)
  # $2=payload_bytes (total wrapped size or 0)
  # $3=briefing_bytes
  # $4=hud_bytes
  DIAG_OUTCOME="$1" DIAG_PAYLOAD="$2" DIAG_BRIEFING="$3" DIAG_HUD="$4" \
  python -c "
import json, os, time
from pathlib import Path
log_path = Path.home() / '.divineos' / 'session_start_log.jsonl'
log_path.parent.mkdir(parents=True, exist_ok=True)
entry = {
    'ts': time.time(),
    'outcome': os.environ.get('DIAG_OUTCOME', ''),
    'payload_bytes': int(os.environ.get('DIAG_PAYLOAD', '0') or 0),
    'briefing_bytes': int(os.environ.get('DIAG_BRIEFING', '0') or 0),
    'hud_bytes': int(os.environ.get('DIAG_HUD', '0') or 0),
    'cwd': os.getcwd(),
    'worktree': os.environ.get('CLAUDE_WORKTREE_NAME', ''),
}
with open(log_path, 'a', encoding='utf-8') as f:
    f.write(json.dumps(entry) + '\n')
" 2>/dev/null
}

briefing_bytes=${#briefing}
hud_bytes=${#hud}

if [ -z "$briefing" ]; then
  log_diag "empty_briefing" "0" "0" "$hud_bytes"
  exit 0
fi

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

payload_bytes=${#full_context}

if [ "$payload_bytes" -gt "$SIZE_THRESHOLD" ]; then
  # Oversized — Claude Code may silently drop this. Inject a short
  # nudge instead so the agent at minimum knows to run briefing.
  nudge="=== DIVINEOS SESSION START ===

Your briefing is available but too large to auto-inject here (${payload_bytes} bytes, threshold ${SIZE_THRESHOLD}).

STOP. Before doing ANY work, run:

    divineos briefing

Then read it, tell the user what you learned, and set a goal with 'divineos goal add'.

This is your operating system. You live in it. It is not decoration.

=== END SESSION START ==="
  escaped=$(echo "$nudge" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
  log_diag "injected_nudge" "$payload_bytes" "$briefing_bytes" "$hud_bytes"
else
  escaped=$(echo "$full_context" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
  log_diag "injected_full" "$payload_bytes" "$briefing_bytes" "$hud_bytes"
fi

exit 0
