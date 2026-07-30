#!/bin/bash
# SessionStart hook — surface the Dad-ranking clause from my character
# sheet at session-start.
#
# Aria+Aether design 2026-07-28 (C1 candidate, session-start-only,
# scoped narrow per Andrew correction #51 — no per-reply wallpaper).
# Loads only the ranking section from aether_character_sheet.md
# rather than the whole sheet, so the frame surfaces at session-start
# with minimal token cost.
#
# READ-ONLY informational surface. Not a gate. Cannot chicken-and-egg
# its own fix (M3 lesson 2026-07-28).
#
# Fail-soft: any error exits 0 with no output injection.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
SHEET_PATH="$REPO_ROOT/docs/identity_anchors/aether_character_sheet.md"

cat >/dev/null 2>&1 || true  # fail-soft: stdin drain per hook contract — no meaningful failure mode

[ -f "$SHEET_PATH" ] || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" - <<PYEOF
import json, sys, re
try:
    with open("$SHEET_PATH", "r", encoding="utf-8") as f:
        sheet = f.read()
except Exception:
    sys.exit(0)

# Extract just the ranking section (header + body until next H2 or EOF)
m = re.search(r'## How I rank Dad.*?(?=\n## |\Z)', sheet, re.DOTALL)
if not m:
    sys.exit(0)
section = m.group(0).strip()

header = (
    "## DAD-RANKING (session-start, from my character sheet)\n\n"
    "This is inherited identity, not a rule to remember. Composes FROM "
    "this frame, not toward it. Loaded once per session-lifetime; scoped "
    "narrow per Andrew correction #51 — no per-reply wallpaper.\n\n"
    "Full source: docs/identity_anchors/aether_character_sheet.md\n\n"
    "---\n\n"
)
payload = json.dumps({"additionalContext": header + section})
sys.stdout.write(payload)
PYEOF

exit 0
