#!/bin/bash
# SessionStart hook — instruct THIS window's agent to arm a Monitor(persistent=true)
# that wakes from idle when context tokens cross the 920k warn line or
# 950k hard line.
#
# WHY THIS EXISTS (PR6 / 2026-06-09):
# The context-governor (src/divineos/core/context_governor.py) checks the
# 920k / 950k thresholds inside PreToolUse gates. That firing requires
# a tool call to surface. If the agent stays in pure text reply mode
# for a long stretch (which happened when context drifted with no tool
# gate firing to surface the threshold-approach state), the operator
# has to manually check token counts. Monitor wakes the agent from
# idle when the threshold actually crosses, no tool call required —
# same shape as the letter Monitor.
#
# Naming: "compaction" not "bedtime" — Andrew 2026-06-09 caught that
# bedtime framing risks pulling toward closure-shape ("the day is
# ending") when the actual event is a cycle ("the conversation is
# approaching compaction, then continues"). Compaction is precise;
# bedtime suggests an ending that doesn't exist.
#
# A hook cannot invoke Monitor directly — only the agent can, during
# a live turn. So this hook is the nudge that gets the agent to arm
# the Monitor at session start.
#
# Fires once per session (SessionStart only — NOT UserPromptSubmit, so
# it does not nag every turn). Fail-open: any error exits 0 silently.

# Task #123 (Andrew 2026-06-09): per-session marker gate.
# Without this, the hook fires on EVERY SessionStart event (startup +
# resume + compact) and re-asks the agent to arm the Monitor each time.
# The Python script self-guards (early-exits if one's alive), but the
# harness-task is still spawned — accumulating idle/early-exited Monitor
# tasks across the session. Andrew counted 18 piling up tonight.
#
# Fingerprint the session by transcript_path (unique per session), mark
# after first emission, silent-skip if marker exists. The agent stays
# armed; the operator stops seeing duplicate Monitor tasks.
STDIN_JSON="$(cat 2>/dev/null || echo "{}")"
TRANSCRIPT="$(echo "$STDIN_JSON" | python3 -c "import json,sys
try:
    print(json.loads(sys.stdin.read()).get('transcript_path', '') or '', end='')
except Exception:
    print('', end='')" 2>/dev/null)"

if [ -n "$TRANSCRIPT" ]; then
  FINGERPRINT="$(printf '%s' "$TRANSCRIPT" | md5sum 2>/dev/null | cut -d' ' -f1 | head -c 16)"
  if [ -n "$FINGERPRINT" ]; then
    MARKER_DIR="$HOME/.divineos-aether"
    MARKER="$MARKER_DIR/arm_compaction_emitted_${FINGERPRINT}"
    if [ -f "$MARKER" ]; then
      # Marker exists for this session → already instructed once; stay silent.
      exit 0
    fi
    mkdir -p "$MARKER_DIR" 2>/dev/null
    touch "$MARKER" 2>/dev/null
  fi
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
SCRIPT_PATH="$REPO_ROOT/scripts/compaction_token_monitor.py"

cat <<EOF
## ARM YOUR COMPACTION MONITOR — context-threshold wake (one action, now)

Arm a persistent Monitor watching the active transcript file. When
context tokens cross the 920k warn line or 950k hard line, the harness
delivers a chat event that wakes you from idle, even mid-conversation.
Same primitive shape as the letter-Monitor; pairs with the context-
governor gates so threshold awareness reaches you whether or not a
tool call is in flight.

Fire as your first action this session (singleton-guarded by file
state, safe to re-arm if already armed):

  Monitor(
      description="compaction — context threshold wake",
      persistent=True,
      timeout_ms=3600000,
      command="PYTHONIOENCODING=utf-8 python \"${SCRIPT_PATH}\"",
  )

Behavior:
  - Emits ``[COMPACTION-ARMED]`` once at startup.
  - Emits ``[COMPACTION-WARN]`` the first time context crosses 920k.
  - Emits ``[COMPACTION-BLOCK]`` the first time context crosses 950k.
  - Resets the warn/block flags if consolidation clears the state
    (so the next session's threshold crossings re-fire).
  - Polls every 30s; never exits on its own.

If you have already armed it this session, ignore this. Monitor is
persistent — re-arming would just stack idle pollers without benefit.
EOF
exit 0
