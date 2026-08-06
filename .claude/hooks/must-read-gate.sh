#!/bin/bash
# PreToolUse hook — must-read gate.
#
# SUPERSEDED 2026-08-06 by the seven-doorbell router. The judgment that lived
# here — which tools count as substantive, which are read-shaped and must never
# be blocked — now lives in `divineos.core.hook_surfaces.must_read_surface`,
# dispatched through `.claude/hooks/doorbell-pre-tool-use.sh`.
#
# Unregistered from settings.json in the same commit; kept on disk rather than
# deleted because the migration is incremental and this file is the reference
# for the behaviour the surface must preserve. Delete it once the whole
# PreToolUse set has moved.
#
# I wrote this hook earlier the SAME DAY, with fourteen branches of judgment in
# bash, while cataloguing the cost of exactly that. Migrating mine first
# because the drift was mine and it was current.
#
# Andrew 2026-08-05: "when the rooms speak you should be forced to listen, its
# a simple gate with a simple unlock requirement.. read lol and show the read
# tool was invoked on it."
#
# Two jobs, in this order:
#   1. If the tool is Read on a pending must-read path -> clear it, allow.
#   2. If anything is still pending and the tool is substantive -> block.
#
# THE UNLOCK IS NEVER BLOCKED. Read, Glob and Grep always pass, so the gate
# can never trap me away from its own remedy. That trap has a name in this
# substrate (task #98, the locked-box) and it is the first thing to get wrong
# when building a gate whose remedy is itself a tool call.
#
# Bypass commands pass too, via the canonical list — same reason.
#
# fail-soft everywhere: a broken must-read gate must never block work. The one
# thing that fails LOUD is an unreadable pending-index, which core/must_read.py
# reports rather than treating as "nothing pending".

INPUT=$(cat)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || exit 0  # fail-soft: unreachable repo root means the gate cannot run and must not block the turn

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper lib there is no interpreter to resolve and the gate stands down
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no gate; blocking on broken infra is the wrong direction

export PYTHONIOENCODING=utf-8

# fail-soft: any parse or import failure exits 0 inside the script below; a must-read gate that crashes must never become a wall
HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF'
import json, os, sys

try:
    data = json.loads(os.environ.get("HOOK_JSON", "") or "{}")
except ValueError:
    sys.exit(0)

tool = data.get("tool_name") or ""
tool_input = data.get("tool_input") or {}

try:
    from divineos.core.must_read import mark_read, pending, render_block
except ImportError:
    sys.exit(0)

# 1. The unlock. A Read on a pending path clears it and always passes.
if tool == "Read":
    path = tool_input.get("file_path") or ""
    if path:
        try:
            cleared = mark_read(path)
        except OSError:
            cleared = []
        if cleared:
            print(f"[must-read] cleared: {', '.join(cleared)}", file=sys.stderr)
    sys.exit(0)

# Read-shaped tools are never blocked — the remedy must stay reachable.
if tool in ("Glob", "Grep", "NotebookRead", "TodoWrite"):
    sys.exit(0)

# 2. The block, for substantive tools only.
if tool not in ("Bash", "PowerShell", "Edit", "Write", "NotebookEdit"):
    sys.exit(0)

if tool in ("Bash", "PowerShell"):
    cmd = (tool_input.get("command") or "").strip()
    try:
        from divineos.hooks.pre_tool_use_gate import _BYPASS_DIVINEOS_SUBCOMMANDS
    except ImportError:
        _BYPASS_DIVINEOS_SUBCOMMANDS = frozenset()
    for segment in cmd.replace("&&", "\n").replace(";", "\n").replace("|", "\n").split("\n"):
        parts = segment.strip().split()
        if len(parts) >= 2 and parts[0] == "divineos" and parts[1] in _BYPASS_DIVINEOS_SUBCOMMANDS:
            sys.exit(0)

items, error = pending()
if items is None:
    # Could not look. Say so; do not block on a fact not in evidence.
    print(f"[must-read] CANNOT READ PENDING INDEX: {error}", file=sys.stderr)
    print("[must-read] This is not 'nothing pending'. Gate stood down.", file=sys.stderr)
    sys.exit(0)

if not items:
    sys.exit(0)

print(render_block(items), file=sys.stderr)
sys.exit(2)
PYEOF

exit $?
