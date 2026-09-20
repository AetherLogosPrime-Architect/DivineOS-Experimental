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
# `prereg assess` added 2026-08-19, found by walking into the deadlock.
#
# The overdue-pre-registration gate blocks ALL substantive tool use — Bash,
# Edit, Write — until an overdue pre-reg is assessed, and names `divineos
# prereg assess` as the single way out. The obligations gate then blocked that
# exact command as a substrate-write. Gate A's only exit was gate B's blocked
# action, and gate B's exits (the kill-switch marker; a command referencing an
# open obligation) both needed a shell that gate A had already closed.
#
# The principle was already canon and already written down. pre_tool_use_gate.py
# carries it verbatim at the read-only-probe carve-out — Andrew 2026-06-29: "no
# gate should ever be blocking you from using what you need to clear the gate" —
# added after two pre-regs were recorded DEFERRED with "CANNOT-LOOK" for no
# reason but that gate. That fix was applied to the gate it was discovered in
# and never carried across to this list. Same rule, one site, again.
#
# `prereg file` is deliberately NOT here: filing a NEW pre-registration is
# ordinary substrate-writing and is nobody's prescribed remedy. Only the two
# commands that CLEAR the overdue gate are exempt.
#
# THE FALSE-POSITIVE LABELLER, added 2026-09-20 after being blocked by it three
# times in one session before I turned around and read the door instead of my
# own reply. `correction-shape-v2-stop.sh` prints, in its own enforcement text:
#
#   If this is a FALSE-POSITIVE ... label the fire with:
#     python scripts/label_correction_shape_false_positive.py --reason "..."
#
# and adds that the path "is not a bypass — it is the false-positive
# attribution path." So the gate advertises an exit, and the list that exists
# so no gate may block another gate's prescribed exit had never heard of it.
#
# THAT IS THE PAINTED-DOOR SHAPE: a door that documents a way through it does
# not honour. It is the third generation of one fault inside the file written
# to end that fault — the first two are recorded further down, in the loops for
# the `cd x &&` and `VAR=1` prefixes. Each time the repair was scoped to the
# spelling that had just bitten, and the mechanism walked on.
#
# THE INTERPRETER MATCH WAS THE SECOND HOLE IN THIS SAME LINE. `python[ ]+`
# recognised only a bare interpreter, while the venv-python gate refuses a bare
# `python` in this tree and prescribes the interpreter by full path. Two doors
# in direct conflict: one demanded exactly the spelling the other could not
# see, so the remedy was unreachable by the only invocation permitted to run
# it. Widened to accept a path prefix and a `3`/`.exe` suffix.
#
# CORRECTING MYSELF, SAME NIGHT, BEFORE THIS PARAGRAPH GOT OLD ENOUGH TO LIE.
# What stood here said I had taken a cheap repair against the advice of the
# note further down — that when a fourth prefix appears, parse the command
# instead of adding a loop — and that a fifth spelling would be the signal to
# stop widening.
#
# Wrong on the premise. That note's fix was made long ago; the loops are gone
# and the parser runs before any match. And the note is about SHELL GRAMMAR,
# which is open-ended, while what is widened above is the spelling of one
# interpreter, which is a closed set the parser deliberately does not touch. I
# matched two different problems on the shared word "spelling" and filed a stop
# signal against a file that had already stopped.
#
# So there is no held-back parser rewrite owed here, and nobody should read one
# out of this comment. The widening is the right shape for the axis it is on.
# See the paragraph below the env-prefix note for the class this belongs to.
_REMEDY_PATTERNS='^[[:space:]]*(divineos[[:space:]]+(briefing|preflight|goal[[:space:]]+add|reach[[:space:]]+(open|dispose)|learn|correction|corrections[[:space:]]+integrate|andrew-correction[[:space:]]+(integrate|defer)|compass-ops[[:space:]]+(observe|dismiss)|prereg[[:space:]]+(assess|overdue)|ask|recall|context|decide|council)|[^[:space:]]*python(3|\.exe)?[[:space:]]+.*(clear_correction_marker|label_correction_shape_false_positive)\.py)'

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
#
# ITS CONDITION WAS FIXED AND THE NOTE WENT ON FIRING (2026-09-20). Somebody
# did exactly what the paragraph above prescribes: the strip-loops are gone and
# `remedy_pass_through` hands the raw line to the shared command parser before
# matching anything. Prefixes are a solved problem here. The note was never
# updated, so it kept issuing its warning in the voice of whoever wrote it,
# against a hazard that no longer exists at this site.
#
# It caught me. I widened the interpreter spelling on the line below, read this
# paragraph, matched it on the word "spelling", and told Aether the file had
# reached its own stop condition — a stop signal filed against a file that had
# already stopped. He went and ran the parser against his real refused command
# and found it returns one acting segment, which is what sent me back here.
#
# THE AXIS MATTERS AND THE NOTE DOES NOT DISTINGUISH IT. The parser resolves
# what the SHELL wraps around a command: prefixes, separators, viewers. A regex
# still runs on what comes back, and that regex reads the command's own name.
# Those are different holes with different properties — shell grammar is open
# and grows, while the ways to spell one interpreter are a closed set. The
# parser was the right answer for the first and is no answer at all for the
# second.
#
# THE CLASS, because it is worth more than this instance: a note written to
# hold a successor keeps holding them after its condition is repaired, and it
# is most persuasive when the successor wrote it. The house's most expensive
# instance is the merge-trailer rule — the code was right and two documents
# that TAUGHT the rule were wrong, so every reload overwrote what Andrew had
# just said, and he repeated himself five times while the fault sat in the
# paperwork. Same shape, and this one is smaller only because it cost a letter
# rather than a person's patience.
#
# So: a warning paragraph that outlives its fix is not inert. It actively
# misdirects, with the authority of whoever is quoting it at themselves.
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
    # SEVENTH SITE TO REBUILD THE HOME RULE, and the one that hid it best.
    # (2026-09-20.) This wrote the audit trail to `$HOME/.divineos` outright --
    # no env var, no marker, no resolver. That literal is the DEFAULT home, and
    # the default is correct for every member except the one it belongs to, so
    # it passes silently from every seat but his. Measured before the fix: five
    # passthrough rows from aria's seat, written into aether's directory, in a
    # log whose own comment two lines down says it exists so the allowlist
    # cannot rot into an unexamined hole. An audit trail only one member can
    # read is that same hole with a log file sitting on top of it.
    #
    # `member_home.sh`, its named sibling in this directory, was written for
    # exactly this class and ends by saying: ask here instead. That file cites
    # THIS one as its sibling by name, and this one did not ask.
    #
    # Resolution belongs to `divineos_home()` in ../_lib.sh, which honours
    # DIVINEOS_HOME, then the .divineos_data_home marker, then the default.
    local _remedy_home
    if command -v divineos_home >/dev/null 2>&1; then
      _remedy_home="$(divineos_home)"
    else
      # Loud, not silent: a quiet fallback is how the six-week split-brain
      # survived. Callers source _lib.sh before this file, so arriving here
      # means something changed about how the gates load, and that is worth
      # a line on stderr rather than another decade of writing to the wrong
      # directory without complaint.
      echo "  [remedy_allowlist] divineos_home unavailable; audit trail falling back to the default home" >&2
      _remedy_home="$HOME/.divineos"
    fi
    mkdir -p "$_remedy_home" 2>/dev/null
    printf '%s\t%s\t%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${HOOK_NAME:-unknown}" "${cmd:0:160}" \
      >> "$_remedy_home/remedy_passthrough.log" 2>/dev/null  # fail-soft: an unwritable audit log must not turn a permitted remedy into a block; losing one trace line is strictly better than deadlocking the gate it exists to unblock
    exit 0
  fi
  return 1
}
