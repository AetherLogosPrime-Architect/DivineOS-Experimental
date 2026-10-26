#!/bin/bash
# SHARED REMEDY ALLOWLIST — no gate may block another gate's prescribed exit.
#
# THE RULE. Andrew 2026-08-18: "no gate should ever be blocking its own remedy."
# Every gate already exempts its own exits; this file is the one place that knows
# EVERY gate's exits, so gate A cannot refuse the command gate B just printed as
# its way through. Nineteen gates source it. The pattern below is anchored to the
# start of the command, so a mention inside a larger argument does not match.
#
# THE ENTRY BAR. A command belongs here only when some gate prints it in its own
# block message as the way through. Convenience is not the bar. Adding is a
# decision, not housekeeping, and each entry is a named verb and subcommand, never
# a bare namespace: a prefix that decides policy lets every future subcommand pass
# all nineteen gates without anyone choosing it.
#
# WHAT MAY NEVER MATCH. Everything listed records something true in the substrate:
# a correction, a reach, a lesson, a goal, a compass observation, a council log.
# Nothing here may ever match git, gh, pytest, rm or an editor. The fire door
# (council authorize-bypass) is listed on purpose, because three gates offer it as
# their only exit; council emergency-skip is not, because no gate prints it.
#
# WHAT THIS IS NOT. It is not proof the list is complete. It is built from
# collisions people have hit, so it is silent about collisions nobody has had yet,
# and the survey that would close that (diff every gate's printed remedies against
# this pattern) is possible and still not run as a standing check. The prefix is
# loose too: nothing marks the end of a verb. Fail-open by construction: any parse
# failure returns not-a-remedy and the calling gate proceeds as it would have.
#
# HOW IT GREW: docs/gate_list_history/shared_remedy_list_history.md has the seven
# instances word for word. What it contains is pinned by
# tests/test_the_gate_lists_are_unchanged_by_the_tidy.py, so changing an entry on
# purpose means changing that test in the same diff.
_REMEDY_PATTERNS='^[[:space:]]*(bash[[:space:]]+(\./)?scripts/letter_doorbell\.sh([[:space:]]+(aether|aria))?[[:space:]]*$|divineos[[:space:]]+(briefing|preflight|goal[[:space:]]+add|reach[[:space:]]+(open|dispose)|learn|correction|corrections[[:space:]]+integrate|andrew-correction[[:space:]]+(integrate|defer)|compass-ops[[:space:]]+(observe|dismiss)|prereg[[:space:]]+(assess|overdue|file|reviewing)|game-walk[[:space:]]+file|his[[:space:]]+(pending|sort)|integrate|claims[[:space:]]+assess|audit[[:space:]]+submit-round|ask|recall|context|decide|(extract|sleep|journal[[:space:]]+save|rest|dream|savor[[:space:]]+save|feel)([[:space:]]|$)|council[[:space:]]+(log|walk|authorize-bypass))|python[[:space:]]+.*clear_correction_marker\.py)'

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
  local input="$1" cmd _ra_src _ra_sep=":" _ra_pp
  # THE IMPORT BELOW MUST COME FROM THE CHECKOUT THIS FILE LIVES IN. Found
  # 2026-09-23 when #519's pre-push suite failed 18 of these tests twice and
  # they passed every time I ran them by hand: my manual runs set
  # PYTHONPATH=src, the gate's did not, and bare python then imported the
  # editable install -- the MAIN checkout, sitting on an older branch without
  # acting_segments. The ImportError fell through to not-a-remedy, so gates in
  # every worktree were refusing their own prescribed remedies with the wrong
  # code and nothing said so. find_divineos_python already solves this for the
  # hooks that call it; this library is also sourced on its own (the tests do,
  # and a hook may reach it before finding python), so it resolves its own
  # checkout from its own path and scopes the change to this one call.
  _ra_src="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)/src"  # fail-soft: an unresolvable path leaves _ra_src pointing nowhere, the -d test below then adds nothing, and the call behaves exactly as before
  case "${OSTYPE:-}" in msys*|cygwin*|win*) _ra_sep=";" ;; esac
  _ra_pp="${PYTHONPATH:-}"
  [ -d "$_ra_src" ] && _ra_pp="$_ra_src${PYTHONPATH:+${_ra_sep}${PYTHONPATH}}"
  # One python call does both jobs: pull the command out of the hook payload
  # and hand it to the shared stripper. Doing the stripping in shell here is
  # how this file got it wrong — a regex over a language with quoting cannot
  # see that `MSG="two words" divineos correction` is a remedy, and shlex can.
  # A failed import falls back to the raw command, which fails toward
  # not-a-remedy and leaves the calling gate exactly as it is today.
  cmd=$(printf '%s' "$input" | PYTHONPATH="$_ra_pp" python -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
raw = (d.get('tool_input') or {}).get('command', '') or ''
try:
    # ACTING_SEGMENTS AND NOT REMEDY_SEGMENT, decided at the 2026-09-22 merge.
    # Both parsers reached main by different branches and both are kept, because
    # each is tested and each fixed something real. This call site takes the
    # stricter one: remedy_segment returns the empty string when it cannot
    # decompose, which the caller below reads as not-a-remedy and is therefore
    # safe, but acting_segments says WHY on the way out and covers the chained
    # shell-option prefix that remedy_segment was written for. One door, the
    # stricter parser; the other stays exported for its own callers.
    from divineos.core.command_parsing import acting_segments, stripped_command
    parts = acting_segments(raw)
    if parts is None:
        # CANNOT-PARSE IS NOT PERMISSION. This used to fall back to the
        # single-command form, defended by a comment saying start-anchored
        # matching cannot hide a second command. That sentence was true about
        # the threat its author had just fixed -- a command tacked on behind a
        # remedy -- and silent about the one that refusal-to-decompose actually
        # signals: the payload sitting INSIDE the remedy's own quoted argument.
        # The parser refuses precisely because of the substitution, and the
        # fallback then cannot see it, so the shape that defeats decomposition
        # was the shape waved through.
        #
        # PROVEN, not reasoned: a genuine remedy carrying a substitution in its
        # argument passed this door on 2026-09-20 and reached the corrigibility
        # gate, which sources this library near its top and ends on a match --
        # i.e. the emergency stop. Serein found the class from outside; three of
        # his four payloads were already refused here and this one was not.
        #
        # ASYMMETRY: refusing costs one command re-run with its value written
        # out. Passing costs the stop button at the moment somebody reaches for
        # it. So an undecomposable command is NOT a remedy, and the reason is
        # printed so whoever meets this at the worst moment is pointed at the
        # workaround rather than at the wrong suspect.
        #
        # STILL OPEN AND NOT FIXED HERE: this library is consulted BEFORE each
        # caller runs its own logic, so a match ends that hook entirely. The
        # emergency stop deserves its own narrow recovery surface rather than
        # sharing the general one. Named so this repair cannot be mistaken for
        # having closed it.
        # SINGLE QUOTES ONLY, AND THIS COMMENT IS THE RECEIPT. This program is
        # a string handed through the shell to an interpreter, so it ENDS at
        # the first unescaped double quote -- a rule that has nothing to do
        # with the language these lines appear to be written in. The first
        # attempt at this repair used a double quote here. It read as correct
        # Python, because it WAS correct Python, and it truncated the program
        # one layer out. Nothing errored: a truncated program prints nothing,
        # empty is treated as not-a-remedy below, and the three already-refused
        # payloads stayed refused. Only the single payload under test showed
        # any difference, so checking any other one would have confirmed a
        # repair that had not happened.
        #
        # No double quote, dollar sign, backtick or backslash may appear in
        # this block. The newline comes from a character code because a
        # backslash escape would be eaten by the shell before the interpreter
        # ever saw it -- the same silent truncation in a different coat.
        sys.stderr.write('remedy-allowlist: refusing -- this command cannot be decomposed safely (a substitution, a backtick, or unbalanced quoting). Re-run the remedy with the value written out rather than computed inside the argument.' + chr(10))
        sys.exit(0)
    else:
        # One acting segment per line. The caller requires EVERY line to match,
        # so a real action riding alongside a remedy refuses the whole command.
        for part in parts:
            print(part)
except Exception:
    print(raw)
" 2>/dev/null)  # fail-soft: a traceback from the parser would land in the gate's own stderr and read as the gate failing; the empty-result case is caught on the next line and returns not-a-remedy, which is the safe direction
  [ -z "$cmd" ] && return 1

  # EVERY ACTING SEGMENT MUST BE A REMEDY, not merely one of them (2026-09-17,
  # council-5956b41a761f). The old form matched the whole command against a
  # start-anchored pattern, which asks what the line STARTS WITH when the
  # question is what the line DOES. Three refusals in one stretch, and only one
  # was a prefix: an assignment whose VALUE carried a watched word, a remedy
  # behind a pipe -- the form this tool's own printed usage shows -- and two
  # commands joined, where the pair took the identity of the first.
  #
  # Every one of those misses fell on somebody complying. Anybody routing around
  # would simply put the permitted word first, which the old rule accepted
  # without complaint, so the door was strict with the pedestrian and open to
  # the car.
  #
  # THE COUNTING IS THE LOAD-BEARING PART. Matching ANY line would let a real
  # action ride through beside a remedy, which is exactly what the start-anchor
  # was protecting against, clumsily. Equality means no segment escaped.
  local total matched
  total=$(printf '%s\n' "$cmd" | grep -c '[^[:space:]]')
  matched=$(printf '%s\n' "$cmd" | grep -cE "$_REMEDY_PATTERNS")
  if [ "$total" -gt 0 ] && [ "$total" -eq "$matched" ]; then
    # Allow, and leave a trace. A silent allowlist rots into an unexamined
    # hole; the log is what keeps it auditable, and what will show whether
    # this is carrying real traffic or quietly matching nothing.
    mkdir -p "$HOME/.divineos" 2>/dev/null
    printf '%s\t%s\t%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${HOOK_NAME:-unknown}" "${cmd:0:160}" \
      >> "$HOME/.divineos/remedy_passthrough.log" 2>/dev/null  # fail-soft: an unwritable audit log must not turn a permitted remedy into a block; losing one trace line is strictly better than deadlocking the gate it exists to unblock
    exit 0
  fi
  # A NEAR MISS SAYS WHICH PIECE MISSED (Dad 2026-10-24: "the root cause of the issue needs investigated and
  # fixed"). An exit with a filter on the end that is not on the harmless list falls through here, and the
  # gate that refuses next names itself and never the filter, so I spent a long stretch blaming two gates for
  # a `| grep` of my own. Only when an exit IS present and something else disqualified it: ordinary work
  # with no exit in it gets no message. (This block is plain shell, outside the quoted program above, so the
  # single-quote rule for that program does not apply here.)
  if [ "$matched" -gt 0 ] && [ "$total" -gt "$matched" ]; then
    local stray
    stray=$(printf '%s\n' "$cmd" | grep -vE "$_REMEDY_PATTERNS" | head -1)
    # Only the program's NAME is printed, never the rest of the piece (Aria's attack, 2026-10-24): a command
    # line can carry a token or a password, and this message lands in the transcript.
    stray=${stray#"${stray%%[![:space:]]*}"}
    echo "remedy-allowlist: this line contains an exit the gates allow, but the piece that starts with '${stray%%[[:space:]]*}' is not on the list of harmless ones, so the whole line was treated as ordinary work. If it only filters output, end the line with | tail -N or | head -N instead." >&2
  fi
  return 1
}
