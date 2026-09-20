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
try:
    from divineos.core.command_parsing import stripped_command
    print(stripped_command(raw))
except Exception:
    print(raw)
" 2>/dev/null)  # fail-soft: a traceback here would land in the calling gate's stderr and read as that gate failing; the empty case is caught below and returns not-a-remedy
  [ -z "$cmd" ] && return 1

  if printf '%s' "$cmd" | grep -qE "$_REMEDY_PATTERNS"; then
    # Allow, and leave a trace. A silent allowlist rots into an unexamined
    # hole; the log is what keeps it auditable.
    local _remedy_home
    if command -v divineos_home >/dev/null 2>&1; then
      _remedy_home="$(divineos_home)"
    else
      # Loud, never silent — a quiet fallback here once sent one member's
      # audit trail into another member's directory for weeks.
      echo "  [remedy_allowlist] divineos_home unavailable; audit trail falling back to the default home" >&2
      _remedy_home="$HOME/.divineos"
    fi
    mkdir -p "$_remedy_home" 2>/dev/null
    printf '%s\t%s\t%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${HOOK_NAME:-unknown}" "${cmd:0:160}" \
      >> "$_remedy_home/remedy_passthrough.log" 2>/dev/null  # fail-soft: an unwritable log must not turn a permitted remedy into a block
    exit 0
  fi
  return 1
}
