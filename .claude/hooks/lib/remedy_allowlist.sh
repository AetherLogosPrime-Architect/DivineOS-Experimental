#!/bin/bash
# SHARED REMEDY ALLOWLIST — no gate may block another gate's prescribed exit.
#
# Andrew 2026-08-18: "no gate should ever be blocking its own remedy."
#
# Nineteen gates each know their own way out and none knows anyone else's, so
# gate A blocks the command gate B just prescribed and neither is wrong from
# inside its scope. The fact with nowhere else to live is: THIS COMMAND IS
# SOMEBODY'S WAY OUT.
#
# ADDING TO THIS LIST is a decision, not housekeeping. The test: does some
# gate's own block-message name this command as the way through? If no gate
# prescribes it, it does not belong here, however convenient.
#
# EVERYTHING HERE IS A RECORDING ACTION — files a correction, opens a reach,
# logs a lesson, sets a goal, observes on the compass. The dangerous verbs are
# deliberately absent and must stay absent: nothing here may ever match git,
# gh, pytest, rm, or an editor.
#
# Fail-open by construction: any parse failure returns 1 (not-a-remedy) and the
# calling gate proceeds exactly as it does today. This file can only ever let
# something through; it can never introduce a new block.
#
# WHY IT SAYS WHAT IT SAYS, and the seven times it has been wrong:
#   docs/remedy_allowlist_rationale.md

_REMEDY_PATTERNS='^[[:space:]]*(divineos[[:space:]]+(briefing|preflight|goal[[:space:]]+add|reach[[:space:]]+(open|dispose)|learn|correction|corrections[[:space:]]+integrate|andrew-correction[[:space:]]+(integrate|defer)|compass-ops[[:space:]]+(observe|dismiss)|prereg[[:space:]]+(assess|overdue)|ask|recall|context|decide|council)|[^[:space:]]*python(3|\.exe)?[[:space:]]+.*(clear_correction_marker|label_correction_shape_false_positive)\.py)'

# Exit 0 (allow, silently) if the command being gated is somebody's remedy.
# Takes the raw hook stdin JSON.
remedy_pass_through() {
  local input="$1" cmd
  # Parsed rather than pattern-stripped: a regex over a language with quoting
  # cannot see that `MSG="two words" divineos correction` is a remedy, shlex
  # can. Import failure falls back to the raw command, which fails toward
  # not-a-remedy.
  cmd=$(printf '%s' "$input" | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
raw = (d.get('tool_input') or {}).get('command', '') or ''

# THE PATTERN BELOW IS START-ANCHORED AND THEREFORE BLIND TO THE TAIL.
# Serein's audit found a substitution riding a genuine remedy; testing that
# here turned up the plainer one, which needs no substitution at all -- a real
# remedy, an operator, then anything. The pattern matches the front and never
# reads the rest. This library is consulted near the top of every gate that
# sources it and exits ALLOW on a match, so whatever rides in behind a remedy
# skips that entire gate.
#
# A quote-AWARE check is what closes it, and it already existed rather than
# needing writing. Quote-aware is not fussiness: the re-joined text drops
# quoting, so a note that legitimately contains a semicolon comes back looking
# exactly like a chained command, and a plain search would refuse honest
# remedies. That trap is recorded in the parser's own comments from August and
# I still nearly walked into it.
#
# STILL OPEN, AND NOT MINE TO CLOSE TODAY: a substitution inside DOUBLE quotes
# survives, because the checker blanks the contents of both quote kinds while
# single quotes are inert and double quotes expand. Aether found that half and
# is repairing it where it lives, so this note never reads as full coverage.
#
# AND THE CHECK RUNS ON THE TAIL, NOT ON THE WHOLE LINE. My first version
# asked it about the raw command and refused a perfectly good remedy issued
# from another directory, because the operator joining the directory change to
# the remedy is itself a chain operator. That is the precise failure this
# whole file exists to prevent -- a gate blocking somebody's prescribed exit.
# Caught by putting the legitimate prefixed case in the probe alongside the
# attacks, which is the only reason I saw it before shipping.
#
# The prefix-stripper that preserves quoting exists for exactly this: a
# quote-aware check on what is left once the leading noise is gone.
try:
    from divineos.core.command_parsing import stripped_command, strip_prefixes_raw
    from divineos.hooks.pre_tool_use_gate import _has_unquoted_chain_shape

    if _has_unquoted_chain_shape(strip_prefixes_raw(raw)):
        print('__TAIL__')
        sys.exit(0)
    print(stripped_command(raw))
except Exception:
    # Could-not-check is not a pass. Falling back to the raw command preserves
    # the old matcher behaviour, and the marker is deliberately NOT printed
    # here, because an import failure must never become a verdict of safe.
    print(raw)
" 2>/dev/null)  # fail-soft: a traceback here would land in the calling gate's stderr and read as that gate failing; the empty case is caught below and returns not-a-remedy
  [ -z "$cmd" ] && return 1

  if [ "$cmd" = "__TAIL__" ]; then
    # Loud, because a refused remedy looks from outside exactly like a gate
    # being wrong, and whoever meets it deserves to know which it is.
    echo "  [remedy_allowlist] this wears a remedy at the front and carries more behind it, so it is NOT being waved through. Run the remedy on its own." >&2
    return 1
  fi

  if printf '%s' "$cmd" | grep -qE "$_REMEDY_PATTERNS"; then
    # Allow, and leave a trace. A silent allowlist rots into an unexamined
    # hole; the log is what keeps it auditable.
    local _remedy_home=""
    if command -v divineos_home >/dev/null 2>&1; then
      _remedy_home="$(divineos_home)"
    fi
    if [ -z "$_remedy_home" ]; then
      # NO GUESS, and this replaced a loud one. The old branch fell back to
      # the bare default home with a warning beside it, which was still the
      # defect wearing a notice: that directory belongs to one particular
      # member, so the fallback filed one member's audit trail under another
      # member's name and announced it to a stream nobody re-reads.
      #
      # Unlike member_home below, nobody has told this function whose seat it
      # is in -- it is ASKING. So there is nothing to fall back to. Skipping
      # costs this one row; guessing puts a wrong row in somebody's permanent
      # record where it reads as theirs forever.
      #
      # Found by the seat-hardcode check within an hour of writing that check,
      # on a line written this morning by the same person.
      echo "  [remedy_allowlist] divineos_home unavailable — remedy ALLOWED but NOT logged, because a guessed home files this under the wrong member" >&2
      exit 0
    fi
    mkdir -p "$_remedy_home" 2>/dev/null
    printf '%s\t%s\t%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${HOOK_NAME:-unknown}" "${cmd:0:160}" \
      >> "$_remedy_home/remedy_passthrough.log" 2>/dev/null  # fail-soft: an unwritable log must not turn a permitted remedy into a block
    exit 0
  fi
  return 1
}
