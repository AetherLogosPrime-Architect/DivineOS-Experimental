#!/bin/bash
# PreToolUse hook — reach-check doorman on substrate-store and research writes.
#
# Andrew 2026-08-06: "the reach needs some tuning and better enforcement."
#
# WHY THIS FILE EXISTS. src/divineos/core/reach_check.py shipped with
# gate_status() returning (blocked, message) for exactly this hook, and was
# wired to nothing. I wrote "NOT YET WIRED to a hook" in its own commit message
# (9c29a7fd) — a finder built to catch unwired work, left unwired. Andrew named
# the shape the same session: "you wire up stuff to find the stuff that isnt
# wired up.. and never wire it up lol."
#
# It cost twice in one session, both remediated by pending obligations
# psf-de60383c and psf-8ee96c94:
#   - three VAD affect entries written without checking whether the recording
#     format was itself under review
#   - the 171-emotion question researched OUTWARD to the web before the local
#     substrate, so the PIM Texture-Concept Bridge surfaced only after Andrew
#     named it
#
# SCOPE IS DELIBERATELY NARROW. Substrate-store writes and research-doc writes
# — the two places the outward-before-inward reach actually happens. Not every
# edit: a gate that fires constantly gets bypassed, and a bypassed gate catches
# nothing (truth #11 — every extra choice-point is somewhere the optimizer
# routes around).
#
# ADVISORY, NOT BLOCKING, and that is a decision rather than a shortcut. Exit 2
# would block. This exits 0 and prints, because the hook cannot distinguish a
# reach-check I skipped from one that legitimately does not apply, and a false
# block on a store-write costs more than a missed prompt. The teeth live in
# reach_check.dispose(), which refuses outright. If these fires turn out to be
# ignored, escalating to exit 2 is the answer — and the bypass telemetry makes
# that measurable rather than a guess.
#
# Fail-open: any error exits 0. A doorman that breaks the door is worse than no
# doorman.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# shellcheck disable=SC2016
# ^ single-quoted heredoc is intentional — python does its own parsing.
echo "$INPUT" | "$PYTHON_BIN" -c '
import json, sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {}) or {}

command = tool_input.get("command", "") or ""
path = tool_input.get("file_path", "") or ""
haystack = (command + " " + path).replace("\\\\", "/")

STORE_WRITES = ("divineos feel", "divineos learn", "divineos opinion", "divineos claim")
RESEARCH_DIR = "docs/ai_research/"

is_store_write = any(v in haystack for v in STORE_WRITES)
is_research_write = RESEARCH_DIR in haystack and tool_name in ("Write", "Edit")
if not (is_store_write or is_research_write):
    sys.exit(0)

try:
    from divineos.core import reach_check
except ImportError as exc:
    # LOUD fail-open. Silent fail-open is the exact defect this whole session
    # has been cataloguing -- a check that cannot run rendered identically to a
    # check that passed. Caught on this hook before it shipped: the hook
    # interpreter resolves divineos from the MAIN CLONE, and reach_check.py
    # lives on an unmerged branch, so the import died and the gate vanished
    # without a word.
    #
    # Standing consequence worth knowing: ANY hook wired to a module that only
    # exists on a feature branch is dead until that branch merges. The hook is
    # not wrong; it is early.
    print(
        f"[reach-check-doorman] NOT RUNNING: {exc}",
        "  The hook interpreter cannot see divineos.core.reach_check. If that",
        "  module is on an unmerged branch, this gate is inert until it lands.",
        "  This message exists so inert is never mistaken for clean.",
        sep="\n",
        file=sys.stderr,
    )
    sys.exit(0)

try:
    blocked, message = reach_check.gate_status()
except Exception as exc:
    print(f"[reach-check-doorman] check errored, not blocking: {exc}", file=sys.stderr)
    sys.exit(0)

if blocked:
    # A check is already open — the undisposed list is more useful than a
    # prompt to run something already running.
    print(message, file=sys.stderr)
    sys.exit(0)

print(
    "REACH-CHECK PROMPT -- about to write to a substrate store or a research\n"
    "doc with no reach-check open for this topic.\n\n"
    "  divineos reach open \"<topic>\"\n\n"
    "What this catches is not forgetting that prior work exists. It is\n"
    "searching outward before searching inward. LOADOUT (2320 indexed\n"
    "entries) and unmerged commit subjects are both covered by reach, and\n"
    "neither is reachable by memory.",
    file=sys.stderr,
)
' 2>&1

exit 0
