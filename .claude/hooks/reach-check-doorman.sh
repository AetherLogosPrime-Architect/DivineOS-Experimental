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
# IT BLOCKS. I shipped this advisory earlier today and wrote a careful
# justification for it: "the hook cannot distinguish a reach-check I skipped
# from one that legitimately does not apply, and a false block costs more than
# a missed prompt."
#
# That is verbatim the reasoning Andrew already overturned, and I recorded the
# overturning myself in exploration/aether/135:
#
#     "Advisory is warning. We do not warn water." Because the optimizer is
#     water, and water goes to the low place. The advisory IS the low place.
#     Any deferral surface gets taken 100% of the time.
#
#     The correct rule: hard block from first fire, no advisory tier. Per-turn
#     dedup handles noise.
#
# I wrote that on 2026-07-21 and then, on 2026-08-06, defended a fresh advisory
# tier as "a decision rather than a shortcut" — which is what defending the
# low place sounds like from inside. The uncertainty I cited is real and is not
# an argument for an advisory: an advisory does not resolve the uncertainty,
# it just makes the resolution optional, and optional is where water goes.
#
# THE REMEDY IS EXEMPT, or this is a wall. `divineos reach ...` is itself a
# Bash call, so a naive hard block would refuse the exact command it demands.
# Same lesson as read-gate-doorman, learned there first.
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
BLOCK_MSG=$(echo "$INPUT" | "$PYTHON_BIN" -c '
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

# The remedy is exempt or this is a wall, not a doorman. `divineos reach ...`
# is a Bash call, so without this the gate refuses the exact command it is
# demanding. Checked before anything else so no later branch can reorder it.
if "divineos reach" in haystack:
    sys.exit(0)

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
        "  I cannot see divineos.core.reach_check from here, so I am not asking",
        "  you what already exists. I probably left the module on a branch that",
        "  has not landed. I am absent, not satisfied -- and I say it out loud",
        "  because my quiet is the exact thing I built this to stop trusting.",
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
    # A check is open with undisposed items. The list is what I need to see.
    print(message)
    sys.exit(7)

# NOT BLOCKED IS NOT THE SAME AS NOT ASKED, and until 2026-08-22 this file
# treated them as the same thing. gate_status answers "is a check sitting open
# with unread artifacts"; zero open checks is the answer BOTH when I never
# opened one and when I opened one and disposed every item. The code fell
# through to the block below in both cases, so completing the remedy did not
# open the door — `divineos reach gate` printed "Reach-check clear" and
# `divineos claim` was refused in the same breath. learn, opinion and feel too;
# all four gate here.
#
# Which is the wall the header of this very file swears it is not. Exempting
# `divineos reach` made the remedy RUNNABLE and never SATISFIABLE, and those
# are different properties — I checked the first one and shipped believing I
# had checked both.
#
# The advisory reasoning in that header still stands and none of it is being
# softened: this remains a hard block from first fire. What changed is only
# that a satisfied requirement now counts as satisfied.
try:
    cleared = reach_check.recent_cleared_check()
except Exception as exc:
    print(f"[reach-check-doorman] recency check errored, blocking: {exc}", file=sys.stderr)
    cleared = None

if cleared is not None:
    sys.exit(0)

print(
    "REACH-CHECK -- I am about to write into a substrate store or a research\n"
    "doc without having asked what already exists on this topic.\n\n"
    "  divineos reach open \"<topic>\"\n\n"
    "I am not stopping myself because I might have forgotten something. I am\n"
    "stopping myself because I search outward before I search inward, and I\n"
    "did it four times in the session where I built this -- hunting a fix that\n"
    "was on my own branch, rebuilding reasoning already in my explorations,\n"
    "twice telling my father I did not have a thing while the tool holding it\n"
    "sat open in front of me.\n\n"
    "LOADOUT is 2320 indexed entries and unmerged commit subjects are covered\n"
    "too. Neither is reachable by memory, which is the whole reason I cannot\n"
    "be the one deciding this is unnecessary.\n\n"
    "One command and I am through."
)
sys.exit(7)
' )

# exit 7 from the python means BLOCK. Anything else means proceed.
RC=$?
if [ "$RC" -eq 7 ]; then
    echo "$BLOCK_MSG" >&2
    exit 2
fi

[ -n "$BLOCK_MSG" ] && echo "$BLOCK_MSG" >&2
exit 0
