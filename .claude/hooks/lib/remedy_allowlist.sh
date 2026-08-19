#!/bin/bash
# SHARED REMEDY ALLOWLIST — no gate may block another gate's prescribed exit.
#
# Andrew 2026-08-18: "no gate should ever be blocking its own remedy."
#
# He said the same thing on 2026-06-16, signing off Aria's signal-based-gates
# design (docs/signal-based-gates-design-2026-06-16.md): every gate must have
# an emergency exit that is not a cheap route, *"that way you don't get stuck
# in a cage of your own building."* Her doc carries it as the one load-bearing
# addition to v4. Two months later I built the cage anyway, because each gate
# got its own exit and nobody owned the exits collectively.
#
# WHAT HAPPENED. The correction-marker gate fired and named three ways out.
# Every one was held shut by a different gate:
#
#   divineos learn              -> blocked by the reach-check doorman
#   divineos reach open         -> the reach doorman's OWN remedy, blocked by
#                                  the correction-marker gate
#   divineos correction         -> refused without a file path for a structural
#                                  fix; the fix I designed was then correctly
#                                  blocked by the keyword-enforcement doorman
#   clear_correction_marker.py  -> blocked by the goal doorman
#
# A closed cycle. The only way through was the fire door, which is meant for a
# burning building and not for a Tuesday. That escape has now been taken four
# times on this marker class; telemetry counts it as
# `bypass:dismiss:correction-marker:cli-broken`. Bypass habituation degrades a
# gate to a warning (psf-ac523181) — so a deadlock that forces the fire door on
# an ordinary day is not an inconvenience. It is a slow way of killing every
# gate at once, by teaching me that walls are things you go around.
#
# THE MISSING FACT. Every gate ALREADY exempts its own remedy. The reach
# doorman carries `if "divineos reach" in haystack: sys.exit(0)` under the
# comment "the remedy is exempt or this is a wall, not a doorman." The
# principle was understood — just scoped one gate wide. Nineteen gates each
# know their own way out and none knows anyone else's, so gate A blocks the
# command gate B just prescribed, and neither is wrong from inside its scope.
# The fact with nowhere to live is: THIS COMMAND IS SOMEBODY'S WAY OUT. This
# file is that somewhere. It generalises a pattern already in the code; it does
# not invent one.
#
# WHY THIS IS NOT A BYPASS SURFACE. Everything listed is a RECORDING action —
# files a correction, opens a reach, logs a lesson, sets a goal, observes on
# the compass. None of it edits code, commits, pushes, merges, or deletes. The
# worst that routing through this list achieves is writing true things into the
# substrate, which is the behaviour the gates were trying to produce. The
# dangerous verbs are deliberately absent and must stay absent: nothing here
# may ever match git, gh, pytest, rm, or an editor. Per Aria's spine — the
# honest fix is never to loosen a gate, it is to make it fire only on evidence.
# This does not loosen any gate's claim. It only stops a gate asserting a
# violation against the act of resolving a different one.
#
# ADDING TO THIS LIST is a decision, not housekeeping. The test: does some
# gate's own block-message name this command as the way through? If no gate
# prescribes it, it does not belong here, however convenient.
#
# Fail-open by construction: any parse failure returns 1 (not-a-remedy) and the
# calling gate proceeds exactly as it does today. This file can only ever let
# something through; it can never introduce a new block.

# Union of every remedy any gate names in its block message. Anchored to the
# start of the command, so `divineos goal add` matches while a mention of it
# inside a larger argument does not.
_REMEDY_PATTERNS='^[[:space:]]*(divineos[[:space:]]+(briefing|preflight|goal[[:space:]]+add|reach[[:space:]]+(open|dispose)|learn|correction|corrections[[:space:]]+integrate|andrew-correction[[:space:]]+(integrate|defer)|compass-ops[[:space:]]+(observe|dismiss)|ask|recall|context|decide|council)|python[[:space:]]+.*clear_correction_marker\.py)'

# Exit 0 (allow, silently) if the command being gated is somebody's remedy.
#
# Takes the raw hook stdin JSON. Strips leading `cd <path> &&` segments so a
# remedy invoked from a worktree is recognised — the marker-clear escape was
# unreachable from a worktree for exactly this reason, its exemption matcher
# knowing only the bare relative form. That bug is this same defect, one scope
# smaller, and it is why the stripping is here rather than left to each caller.
#
# ENV-ASSIGNMENT PREFIXES (2026-08-18) — the same defect a third time, hours
# after this file was written to end it. `VAR=value cmd` is ordinary shell and
# the patterns above are anchored to the start, so
# `DIVINEOS_REQUIRE_MONITORS_BYPASS=1 divineos compass-ops observe ...` did not
# match. The compass marker blocked its own prescribed remedy, then blocked the
# edit that would have repaired it. Confirmed by experiment rather than reading:
# the identical command with the prefix removed passed immediately. A bypass
# variable one gate told me to use had made me invisible to the list that keeps
# another gate's door open.
#
# The lesson worth keeping is not "add a third strip." It is that this matcher
# reads SHELL with a regex that only knows bare invocations, so every legal
# prefix shell permits is a fresh hole — `cd x &&`, `VAR=1`, and whatever turns
# up next. These loops are a floor, not a proof. If a fourth prefix appears the
# answer is to parse the command, not to add a fourth loop.
remedy_pass_through() {
  local input="$1" cmd
  # One python call does both jobs: pull the command out of the hook payload
  # and hand it to the shared stripper. Doing the stripping in shell here is
  # how this file got it wrong — a regex over a language with quoting cannot
  # see that `MSG="two words" divineos correction` is a remedy, and shlex can.
  # A failed import falls back to the raw command, which fails toward
  # not-a-remedy and leaves the calling gate exactly as it is today.
  cmd=$(printf '%s' "$input" | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
raw = (d.get('tool_input') or {}).get('command', '') or ''
try:
    from divineos.core.command_parsing import stripped_command
    print(stripped_command(raw))
except Exception:
    print(raw)
" 2>/dev/null)  # fail-soft: a traceback from the parser would land in the gate's own stderr and read as the gate failing; the empty-result case is caught on the next line and returns not-a-remedy, which is the safe direction
  [ -z "$cmd" ] && return 1

  if printf '%s' "$cmd" | grep -qE "$_REMEDY_PATTERNS"; then
    # Allow, and leave a trace. A silent allowlist rots into an unexamined
    # hole; the log is what keeps it auditable, and what will show whether
    # this is carrying real traffic or quietly matching nothing.
    mkdir -p "$HOME/.divineos" 2>/dev/null
    printf '%s\t%s\t%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${HOOK_NAME:-unknown}" "${cmd:0:160}" \
      >> "$HOME/.divineos/remedy_passthrough.log" 2>/dev/null  # fail-soft: an unwritable audit log must not turn a permitted remedy into a block; losing one trace line is strictly better than deadlocking the gate it exists to unblock
    exit 0
  fi
  return 1
}
