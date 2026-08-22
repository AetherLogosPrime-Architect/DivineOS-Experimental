#!/bin/bash
# PreToolUse hook â€” reach-check doorman on substrate-store and research writes.
#
# Andrew 2026-08-06: "the reach needs some tuning and better enforcement."
#
# WHY THIS FILE EXISTS. src/divineos/core/reach_check.py shipped with
# gate_status() returning (blocked, message) for exactly this hook, and was
# wired to nothing. I wrote "NOT YET WIRED to a hook" in its own commit message
# (9c29a7fd) â€” a finder built to catch unwired work, left unwired. Andrew named
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
# â€” the two places the outward-before-inward reach actually happens. Not every
# edit: a gate that fires constantly gets bypassed, and a bypassed gate catches
# nothing (truth #11 â€” every extra choice-point is somewhere the optimizer
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
# tier as "a decision rather than a shortcut" â€” which is what defending the
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

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # shellcheck disable=SC2034  # HOOK_NAME is read by remedy_allowlist.sh once sourced, not by this file
  HOOK_NAME="$(basename "$0")"
  # shellcheck source=/dev/null  # path is computed from $0 at runtime and cannot be resolved statically
  . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true  # fail-soft: the allowlist exits 0 itself when a command IS a prescribed remedy; a non-zero here only means "not a remedy", which must not abort this hook before its real check runs
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# shellcheck disable=SC2016
# ^ single-quoted heredoc is intentional â€” python does its own parsing.
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

# NOT-BLOCKED IS TWO DIFFERENT STATES AND THIS USED TO CONFLATE THEM.
# gate_status() returns (False, "") both when no check was ever opened AND
# when every item of a check has been disposed -- so the fall-through below
# fired on a fully-worked check and told me I had not reached. 2026-08-17:
# I opened two checks, disposed all five artifacts with evidence, and the
# gate handed me its opening message each time; `divineos learn` had no
# reachable state at all. Not a wrong threshold or a wrong message -- a
# missing state, which is the same wall the read-gate hit this morning and
# the same sentence that gate carries in its own text: a gate whose cure sits behind
# itself is a wall.
#
# read-gate-doorman.sh has no fall-through block, so this defect was local
# to this file rather than a pattern across the doormen. Checked, not assumed.
try:
    ok, why = reach_check.satisfied_recently()
except Exception as exc:
    print(f"[reach-check-doorman] satisfied-check errored, not blocking: {exc}", file=sys.stderr)
    sys.exit(0)
if ok:
    # Say WHAT satisfied it. A gate that opens in silence teaches nothing
    # about what opened it, and the next confused reader is me.
    print(f"[reach-check-doorman] {why}", file=sys.stderr)
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
