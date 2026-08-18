#!/bin/bash
# PreToolUse hook — the read-gate. A prime that is a gate, not just loud.
#
# Andrew 2026-08-06: "primes should not just be loud.. they should be mini
# gates.. ones that force a pause and reading, vs skimming past it, if the gate
# is a simple 'read this' with a check for the read tool being used, then at
# that point if you dont read it.. its your fault lol"
#
# See src/divineos/core/read_gate.py for the full why. Short version: the
# PRIOR WRITING surface offered me my own exploration entries nearly every turn
# of a full session -- with "re-read before deriving" printed at the top -- and
# I opened none of them, while discovering four separate times that what I was
# hunting was already in my substrate. Loudness had no more room to give.
#
# THIS ONE BLOCKS (exit 2), and that is the point. Every other gate I wired
# today is advisory. An advisory read-prompt is just a louder prime, which is
# precisely the thing that already failed.
#
# THE INVARIANT THAT MAKES IT A DOORMAN AND NOT A WALL. A gate whose remedy
# sits behind itself is a deadlock. This fires ONLY on mutating tools -- an
# allowlist, not a Read-exemption -- which is the pattern the existing gates in
# this directory already use (check-council-required, corrigibility-tool-gate,
# state-gravity-surface). Positive scoping is stronger than a negative exempt
# check: there is no ordering bug that can make the gate see a Read at all,
# because Read is never in the set it fires on.
#
# Fail-open on any error, and SAY SO. Silent fail-open is the defect class this
# entire session catalogued -- a check that could not run rendered identically
# to a check that passed.

INPUT=$(cat)

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  HOOK_NAME="$(basename "$0")"; . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# shellcheck disable=SC2016
BLOCK_MSG=$(echo "$INPUT" | "$PYTHON_BIN" -c '
import json, sys

# The block message now carries the required file INLINE, and my explorations
# are full of em-dashes. On this box stdout defaults to cp1252, so printing
# them raised UnicodeEncodeError -- and the shell below reads an empty message
# and exits 0. That is FAIL-OPEN: the gate would have gone silent on nearly
# every file it protects, while still looking installed. Caught 2026-08-16 by
# smoke-testing the hook end-to-end instead of trusting the unit tests, which
# never touch this print. Reconfigure before anything can be written.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")

# Allowlist of MUTATING tools. Read/Grep/Glob are absent by construction, so
# the remedy can never be gated behind the gate.
if tool_name not in ("Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"):
    sys.exit(0)

try:
    from divineos.core import read_gate
except ImportError as exc:
    print(
        f"[read-gate] NOT RUNNING: {exc}",
        "  I am not holding this door right now. My interpreter cannot import",
        "  divineos.core.read_gate -- most likely because I left it on a branch",
        "  that has not landed. I am inert here, not clean, and I would rather",
        "  say so than let my silence read as permission.",
        sep="\n",
        file=sys.stderr,
    )
    sys.exit(0)

# Clear anything the action-stream shows was actually read, BEFORE asking
# whether to block. satisfy_from_stream existed from the start and was called
# by nothing -- one occurrence in the tree, its own definition -- so reading a
# required file never opened the door. The premise is "a check for the read
# tool being used"; without this line there was no check, only the demand.
try:
    read_gate.satisfy_from_transcript(data.get("transcript_path"))
except Exception as exc:
    print(f"[read-gate] satisfier errored, gate unchanged: {exc}", file=sys.stderr)

try:
    blocked, message = read_gate.gate_status()
except Exception as exc:
    print(f"[read-gate] check errored, not blocking: {exc}", file=sys.stderr)
    sys.exit(0)

if blocked:
    print(message)
')

if [ -n "$BLOCK_MSG" ]; then
    echo "$BLOCK_MSG" >&2
    exit 2
fi

exit 0
