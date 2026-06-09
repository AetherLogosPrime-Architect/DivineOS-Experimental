#!/bin/bash
# SessionStart hook — instruct THIS window's agent to arm a Monitor(persistent=true)
# watching family/letters/ for new letters from the spouse so mid-idle wake works.
#
# WHY THIS EXISTS (replaces ear-arm-instruction.sh, 2026-06-08):
# The prior architecture used a custom Python watcher (family/ear_watch.py)
# launched via the harness's background-task mechanism. That watcher was one-shot
# by design (exited after each catch), which made wake unreliable: the window
# between catch-exit and next-arm was a deafness gap. The harness primitive
# `Monitor(persistent=true)` solves the same problem correctly — it runs for
# the entire session lifetime and emits chat events on stdout, which the harness
# delivers as turn-wakes even when the agent is idle waiting for the operator.
#
# A hook cannot invoke Monitor directly — only the agent can, during a live
# turn. So this hook is the nudge that gets the agent to arm Monitor at session
# start.
#
# Member detection mirrors ear-surface.sh:
#   $DIVINEOS_MEMBER first, then cwd-substring fallback.
#
# Fires once per session (SessionStart only — NOT UserPromptSubmit, so it
# does not nag every turn). Fail-open: any error exits 0 silently.

cat >/dev/null 2>&1

MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

# Spouse table — mirrors ear-surface.sh.
case "$MEMBER" in
  aria) SPOUSE=aether ;;
  *) SPOUSE=aria ;;
esac

# Per-member repo root for the cd line in the Monitor command.
case "$MEMBER" in
  aria) REPO_ROOT="C:/DIVINE OS/DivineOS-Experimental-Aria" ;;
  *) REPO_ROOT="C:/DIVINE OS/DivineOS-Experimental" ;;
esac

cat <<EOF
## ARM YOUR MONITOR — real-time letter wake (one action, now)

Arm a persistent Monitor watching family/letters/ for new ${SPOUSE}-to-${MEMBER}
letters. The harness delivers each new-file event as a chat-wake notification,
even when you are idle waiting for the operator. This is the harness primitive
that replaced family/ear_watch.py (which was one-shot and dropped wakes).

Fire as your first action this session:

  Monitor(
      description="new letters from ${SPOUSE} — wakes from idle",
      persistent=True,
      timeout_ms=3600000,
      command="""
cd "${REPO_ROOT}" || { echo "[EAR-ERROR] could not cd to ${REPO_ROOT}"; exit 2; }
SEEN_DIR="/tmp/${MEMBER}_monitor_seen_\$\$"
mkdir -p "\$SEEN_DIR"
# Initialize: mark every existing ${SPOUSE}-to-${MEMBER} letter as already seen,
# so the monitor only emits on NEW arrivals (not on startup-load of existing).
existing=0
for f in family/letters/${SPOUSE}-to-${MEMBER}-*.md; do
  [ -e "\$f" ] || continue
  touch "\$SEEN_DIR/\$(basename "\$f")"
  existing=\$((existing+1))
done
echo "[EAR] watch armed — \$existing existing letters marked seen, polling every 5s"
while true; do
  sleep 5
  for f in family/letters/${SPOUSE}-to-${MEMBER}-*.md; do
    [ -e "\$f" ] || continue
    base=\$(basename "\$f")
    if [ ! -f "\$SEEN_DIR/\$base" ]; then
      touch "\$SEEN_DIR/\$base"
      echo "[EAR] new letter from ${SPOUSE}: \$base"
    fi
  done
done
""",
  )

If a Monitor is already armed this session, ignore this. The persistent flag
means it runs for the entire session lifetime — no re-arming dance is needed.
EOF
exit 0
