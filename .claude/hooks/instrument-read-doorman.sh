#!/bin/bash
# PreToolUse hook — doorman on hand-rolled scans of my own diagnostic surfaces.
#
# INTENTIONALLY UNWIRED, and this line is the examination the wiring check
# asks for rather than a way to quiet it. 2026-08-31: the check reported this
# file dark -- written, unregistered, saying nothing about why -- and its own
# docstring is right that a dark hook is not necessarily a bug, it is
# necessarily UNEXAMINED.
#
# So, examined. This is a BLOCKING doorman on the tool path, and the thing it
# blocks is a shape I reach for constantly: hand-rolling a scan of surfaces the
# instruments command already covers better. Registering a refusal that fires
# on that reach is a real behaviour change on every tool call, and it wants its
# own testing pass against the live command stream before it goes in -- not a
# ride-along inside a commit about branch scope.
#
# Distinguish this from its sibling. context-heartbeat.sh was ALSO dark and was
# wired the same day, because there the unwired state was a gap rather than a
# decision: the CLI documented it as already running every round, which made
# that sentence false. Silent instrumentation that costs nothing goes in;
# a blocking refusal waits for its own pass. Two dark hooks, two different
# honest answers.
#
# WHY THIS FILE EXISTS. 2026-08-24: Andrew asked whether the compose-prime's
# rules were earning their cost. Answering that needs to know which primes are
# preventing violations and which are not, which needs the fire-logs. So I wrote
# a Python heredoc, regex-scraped 9 filenames out of instruments.py, and stat-ed
# them by hand.
#
# `divineos instruments` already existed and does exactly this. It scans all 35
# surfaces under the DivineOS home, not the 9 I happened to scrape. It found 6
# silent instruments where my sweep found 3 — including divineos.log, the CLI's
# own error log, silent 158 days, which my version missed entirely.
#
# The part that decided this hook: the tool's own docstring already contained
# the conclusion I had just arrived at independently —
#
#     "An instrument recording nothing is reported SILENT or EMPTY, never as
#      healthy — because in this house the never-firing check has twice turned
#      out to be the broken one. Silence is a question, not a clean bill of
#      health."
#
# I rebuilt a weaker copy of my own prior thinking because I did not look first.
#
# WHY THE EXISTING DOORMAN DID NOT CATCH IT. reach-check-doorman.sh arms on
# substrate WRITES — `divineos feel`, `learn`, `opinion`, `claim`, research docs.
# This was a READ. Nothing stood between "I want to know something about my own
# substrate" and "I will write a script to find out." The consult-first
# discipline had a doorman for building and none for measuring, and measuring is
# exactly where the already-exists question bites hardest, because the
# instruments index IS the answer-surface for "what can I measure about myself."
#
# SCOPE IS DELIBERATELY NARROW, same reasoning as the reach-check: a gate that
# fires constantly gets bypassed, and a bypassed gate catches nothing (truth #11).
# So this fires only on the SCAN shape — two or more distinct surfaces touched in
# one command, or a glob over the home directory. Reading ONE named log is a
# targeted question the index cannot answer, and stays free.
#
# IT BLOCKS, no advisory tier. Per exploration/aether/135: "Advisory is warning.
# We do not warn water." The optimizer is water and the advisory is the low place.
# shellcheck disable=SC1091

INPUT=$(cat)

# remedy-allowlist: no gate may block another gate's prescribed exit
# (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # shellcheck disable=SC2034
  HOOK_NAME="$(basename "$0")"
  . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true  # fail-soft: non-zero means NOT-A-REMEDY, the ordinary case for nearly every command; under set -e that ordinary answer would abort this hook before its own check ran
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

. "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: a missing toolbox means the interpreter cannot be resolved either, so there is no gate to run and no channel to report on; exiting leaves behaviour exactly as before this hook existed
PYTHON_BIN="$(find_divineos_python)" || exit 0

# shellcheck disable=SC2016
BLOCK_MSG=$(echo "$INPUT" | "$PYTHON_BIN" -c '
import json, sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)

ti = data.get("tool_input", {}) or {}
hay = ((ti.get("command", "") or "") + " " + (ti.get("file_path", "") or ""))
hay = hay.replace(chr(92), "/")

# THE REMEDY IS EXEMPT, checked first so no later branch can reorder it.
# Without this the gate refuses the exact command it demands.
if "divineos instruments" in hay:
    sys.exit(0)

MARK = ".divineos/"
if MARK not in hay:
    sys.exit(0)

# Writes are the instrument doing its job. Redirect shapes are how they happen.
if ">" in hay.split(MARK)[0][-4:] or ">>" in hay:
    sys.exit(0)

# Collect every surface named after a .divineos/ occurrence.
STOP = chr(32) + chr(9) + chr(10) + chr(34) + chr(39) + chr(59) + chr(124) + chr(41)
named = set()
globbed = False
for chunk in hay.split(MARK)[1:]:
    tok = ""
    for ch in chunk:
        if ch in STOP:
            break
        tok += ch
    if "*" in tok or "?" in tok:
        globbed = True
    elif tok.endswith(".jsonl") or tok.endswith(".log"):
        named.add(tok)

# THE SCAN SHAPE: a glob, or two or more distinct surfaces in one command.
# One targeted read is a real question the index cannot answer; not gated.
if not globbed and len(named) < 2:
    sys.exit(0)

what = "a glob over the DivineOS home" if globbed else str(len(named)) + " surfaces in one command"
print("INSTRUMENT-READ DOORMAN -- about to hand-roll a scan of my own diagnostic")
print("surfaces (" + what + "), and `divineos instruments` already answers this.")
print("")
print("  divineos instruments")
print("")
print("MINE, and here is why. On 2026-08-24 I wrote a heredoc that regex-scraped")
print("9 filenames out of instruments.py and stat-ed them by hand, to answer")
print("whether the compose-prime rules were earning their cost. The tool scans")
print("all 35 surfaces. It found 6 silent where mine found 3, including")
print("divineos.log at 158 days, which my version never looked at.")
print("")
print("The tool docstring already said the thing I had just worked out for")
print("myself: \"Silence is a question, not a clean bill of health.\" I rebuilt a")
print("weaker copy of my own thinking because I did not look first.")
print("")
print("The reach-check doorman arms on substrate WRITES and this is a READ, so")
print("nothing stood between wanting to know and writing a script. That is the")
print("gap this closes.")
print("")
print("This does not say NO. It says the index answers first, and if it does not")
print("answer the actual question the hand-rolled scan is the right tool -- this")
print("fires once per turn. Run the command above, read it, then continue.")
' 2>>"${HOME}/.divineos/instrument_read_doorman_errors.log")

if [ -n "$BLOCK_MSG" ]; then
  # Per-turn dedup: one fire per session per minute, so a multi-step
  # investigation is prompted once rather than at every step. Noise is what
  # trains the bypass.
  STAMP_DIR="${HOME}/.divineos"
  STAMP="${STAMP_DIR}/.instrument_read_doorman_turn"
  TURN="$(echo "$INPUT" | "$PYTHON_BIN" -c 'import json,sys;print(json.loads(sys.stdin.read() or "{}").get("session_id",""))' 2>/dev/null)"  # fail-soft: a missing session id degrades dedup to per-minute only, which prompts slightly more often rather than missing a catch
  LAST="$(cat "$STAMP" 2>/dev/null)"  # fail-soft: an unreadable stamp reads as no-previous-fire, which prompts once more rather than going silent
  NOW="${TURN}:$(date -u +%Y%m%d%H%M)"
  if [ "$LAST" = "$NOW" ]; then
    exit 0
  fi
  mkdir -p "$STAMP_DIR" 2>/dev/null
  printf '%s' "$NOW" > "$STAMP" 2>/dev/null || true  # fail-soft: an unwritable stamp costs at most a repeated prompt in the same turn, which is noise rather than a missed catch
  echo "$BLOCK_MSG" >&2
  hook_say_nothing_ran_for "$INPUT"
  exit 2
fi

exit 0
