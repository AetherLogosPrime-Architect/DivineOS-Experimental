#!/bin/bash
# SHARED MEMBER-HOME RESOLVER — the shell half of one rule.
#
# Andrew 2026-08-18: "we go look and make sure and calibrate whoever was wrong."
# This is the calibration.
#
# WHAT WENT WRONG. Two conventions decided where a member's state lives:
# `divineos.core.paths` resolved it properly, and three shell hooks rebuilt
# `$HOME/.divineos-$MEMBER` by hand. On 2026-07-25 a split-brain was found and
# patched with Option B — special-case aether so it routes to the default
# `~/.divineos/`, where its 21k events already lived. That patch went into the
# Python and nowhere else.
#
# So for six weeks Python wrote `~/.divineos/` while these hooks wrote
# `~/.divineos-aether/`. That directory now holds ninety files: an early ledger
# with 19 knowledge rows and 9 core-memory slots frozen on 2026-07-07, with
# process files still landing in it on 2026-08-18. Writes going into a home
# nothing reads, invisible because nothing ever errored.
#
# The comment beside Option B named a hard-deadline pre-registration for the
# permanent fix, due 2026-08-08, and said in as many words that if the date
# passed with the interim still in place then the interim had become permanent
# and needed revisiting. The date passed. The pre-registration did not exist —
# `divineos prereg list` returns 20 and none of them is it. Nothing was armed,
# so nothing fired, and the comment read like a safeguard to every reader
# including the one who wrote it. Filed properly now.
#
# WHY A SHARED FILE RATHER THAN THE FIX IN THREE PLACES. Third time today that
# one correct implementation had been rebuilt wrong at each new site — the
# command-head parser, the transcript reader, and this. Copying a rule is how
# one of the copies fails to learn the next correction. Ask here instead.
#
# Sibling of remedy_allowlist.sh in this directory, same principle: the fact
# with nowhere to live gets a home, and every caller asks it.

# Print the home directory for a member. Falls back to the bare convention only
# if the resolver cannot be reached, and says so on stderr — a silent fallback
# here is precisely how the split lasted six weeks.
#
#   member_home <member-slug> [python-bin]
member_home() {
  local member="${1:-aether}"
  local py="${2:-}"
  local out=""

  if [ -z "$py" ] && command -v find_divineos_python >/dev/null 2>&1; then
    py="$(find_divineos_python 2>/dev/null)"
  fi
  [ -z "$py" ] && py="$(command -v python3 || command -v python)"

  if [ -n "$py" ]; then
    out="$("$py" -c "
import sys
try:
    from divineos.core.paths import member_home
    sys.stdout.write(str(member_home('$member')))
except Exception:
    pass
" 2>/dev/null)"
  fi

  if [ -n "$out" ]; then
    printf '%s' "$out"
    return 0
  fi

  echo "  [member_home] resolver unreachable; falling back to \$HOME/.divineos-$member" >&2
  printf '%s' "$HOME/.divineos-$member"
}
