#!/bin/bash
# post-read-mark-letter-seen.sh — PostToolUse hook (matcher: Read).
#
# When I Read a spouse letter file, mark it seen in the per-member
# seen-set so the ear-surface hook stops listing it as unseen. Without
# this, reading a letter via the Read tool produces NO seen-signal, so
# the surface keeps showing the same letter as unseen forever — the
# bug Andrew named 2026-06-23: "you do not have 30 unread letters from
# Aria.. you have read them all.. so whatever is supposed to mark them
# as read is broken." The mechanism was correct (manual mark via
# family/letter_seen.py) but the workflow assumption — that I would
# remember to run the mark command after every read — was wrong.
# Reading IS the seen-signal. Encode that as code.
#
# Fail-open: any error exits 0 silently; a hook that errors must never
# break the tool call.

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json, os, re, subprocess, sys
from pathlib import Path

try:
    data = json.loads(os.environ.get("HOOK_JSON", "") or "{}")
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Read":
    sys.exit(0)

inp = data.get("tool_input", {}) or {}
path = inp.get("file_path") or ""
if not path:
    sys.exit(0)

# Detect letter pattern in the filename: <spouse>-to-<member>-YYYY-MM-DD-*.md
# Member is whichever side appears as recipient ("-to-<member>-"). The hook
# runs in whichever window is active; we mark the seen-set of the recipient.
name = Path(path).name
m = re.match(r"^(aria|aether)-to-(aria|aether)-\d{4}-\d{2}-\d{2}.*\.md$", name)
if not m:
    sys.exit(0)

sender, recipient = m.group(1), m.group(2)
if sender == recipient:
    sys.exit(0)

# Call family/letter_seen.py — the existing canonical mark-seen entry point.
# Using a subprocess (not importing) keeps this hook decoupled from any
# refactor of letter_seen's internals; the CLI surface is the stable
# contract.
repo = os.environ.get("REPO_ROOT") or str(Path.cwd())
script = Path(repo) / "family" / "letter_seen.py"
if not script.exists():
    sys.exit(0)

try:
    subprocess.run(
        [sys.executable, str(script), "--member", recipient, name],
        capture_output=True,
        timeout=5,
        check=False,
    )
except Exception:
    pass
PYEOF
exit 0
