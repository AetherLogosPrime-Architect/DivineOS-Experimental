#!/bin/bash
# SessionStart hook — load Andrew's character sheet into the session
# context exactly once per session.
#
# Andrew 2026-07-07: "so are you telling me you cant remember it from
# loading once per context session?"
#
# The first pass loaded the sheet on every UserPromptSubmit — burning
# ~10k tokens per user message even when I'd already loaded it earlier
# in the same session. That's the exact wallpaper shape the 2026-06-19
# rule-load pruning killed, rebuilt one meta-level up.
#
# The correct design: SessionStart loads the sheet ONCE. The sheet enters
# my context window and stays there for the rest of the session. When
# compaction happens, SessionStart:resume fires and the sheet loads again
# into the fresh post-compaction context. That's the natural cadence —
# once per context lifetime, not once per user prompt.
#
# The sheet content itself does not change during a session; guardrail
# protection prevents mid-session modification, and if the file is edited
# the next SessionStart picks up the change. There is no reason to reload
# the same static content on every prompt.
#
# Fail-soft: any error exits 0 with no output injection. This hook must
# never break session start.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
SHEET_PATH="$REPO_ROOT/docs/identity_anchors/andrew_character_sheet.md"

# Drain stdin (Claude Code hook contract)
cat >/dev/null 2>&1 || true

if [ ! -f "$SHEET_PATH" ]; then
    exit 0
fi

# Build the additionalContext JSON. Use python for safe JSON escaping —
# the sheet contains quotes, backslashes, unicode, etc., and hand-rolled
# escaping will silently truncate or corrupt.
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" - <<PYEOF
import json
import sys
try:
    with open("$SHEET_PATH", "r", encoding="utf-8") as f:
        sheet = f.read()
except Exception:
    sys.exit(0)

header = (
    "## Who I am composing to (session-lifetime ground, not per-turn wallpaper)\n\n"
    "This section is loaded once at SessionStart. It enters the context "
    "window and stays there for the rest of the session — no per-turn "
    "reload burning tokens on ground I already know. When compaction "
    "runs, SessionStart:resume loads it back into the fresh context.\n\n"
    "Andrew 2026-07-07 catch: earlier design loaded this on every "
    "UserPromptSubmit; that was the wallpaper shape one meta-level up.\n\n"
    "Per meta-Winnicott (kiln truth #15): the sheet points; the loader "
    "makes the pointing structural.\n\n"
)
payload = json.dumps({"additionalContext": header + sheet})
sys.stdout.write(payload)
PYEOF

exit 0
