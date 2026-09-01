#!/bin/bash
# PreToolUse(Write) — show prior work before a NEW build file is created.
#
# Per prereg-ad19dea9b03d. Built 2026-08-27 from a duplicate I made that
# day: a letter-state store built on one branch, forgotten, and built
# again a week later on another. Both real. Neither knew about the other.
#
# WHY THE EXISTING verify-before-build GATE DID NOT CATCH IT. Its
# predicate is "has this session read something recently", and reading
# SOMETHING is not searching for THIS. I cleared it every time that day
# by opening a test file. And the earlier work was not on the branch I
# stood on, so even a perfect search of the working tree would have
# returned empty and CONFIRMED the mistake.
#
# DOORMAN, NOT LANDLORD (Aether's entry 97). This does not say "you may
# not pass". It says "here is what I already went and found; read it
# first". The gathering is done before the block, which is the whole
# difference between a door being held and a door being shut.
#
# NARROW ON PURPOSE, so it stays a beach wall rather than a turnstile:
# only a file that does not yet exist, only under the build directories,
# only when two distinctive words match, only against files of the same
# kind. Most writes never see it.
#
# Fail-open: any error exits 0. A broken doorman must not stop the work.

INPUT=$(cat)

if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # shellcheck source=/dev/null
  HOOK_NAME="prior-art-before-new-file" source "$(dirname "$0")/lib/remedy_allowlist.sh" 2>/dev/null || true  # fail-soft: an unloadable allowlist leaves this doorman with no exemptions, which is the strict direction and never the permissive one
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
cd "$REPO_ROOT" || exit 0

# shellcheck source=/dev/null
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# FAIL-OPEN, NEVER FAIL-SILENT. Until 2026-08-29 this line ended in
# `2>/dev/null` and the decision below was made on whether standard output
# was empty. So a crash inside the module -- an import error after a rename,
# a missing git binary, an exception in the tokeniser -- produced no output
# and a silent pass. Aether found it reviewing this hook, and it is the
# sentence from the module's own docstring turned on its replacement: a
# broken doorman indistinguishable from one with nothing to report, which is
# the exact shape a guard for silent duplication must not have. True of the
# first version in its logic, true of this one in its plumbing.
#
# Exiting zero on a failure is right and was never the problem. A broken
# doorman must not stop the work. What was welded together is fail-open and
# fail-SILENT, and they separate cleanly: keep the exit code, split the
# message. Standard error is captured rather than discarded, and the module
# reports three states by exit code rather than by whether it printed.
# Codes over message-parsing per decision 3eaf13fa -- an unknown integer
# hits the crash branch loudly, where a renamed string would fall silently
# through the wrong door.
STDERR_FILE="$(mktemp)"
RESULT="$(printf '%s' "$INPUT" | "$PYTHON_BIN" -m divineos.core.prior_art_by_name 2>"$STDERR_FILE")"
RC=$?
CRASH_TEXT="$(cat "$STDERR_FILE" 2>/dev/null)"  # fail-soft: an unreadable capture file leaves the text empty, and the exit code below still routes to the crash branch
rm -f "$STDERR_FILE" 2>/dev/null  # fail-soft: a leftover temp file in the system temp dir is not worth a word of hook output

# 3 = the scan could not run, and said why. Advisory: say it, allow the write.
if [ "$RC" = "3" ]; then
  cat >&2 <<EOF
PRIOR-ART DOORMAN — I COULD NOT LOOK. This is not a clean result.

$RESULT

Writing is allowed and this is not a refusal. It is the difference between
"I went and found nothing" and "I never got to look", which this hook could
not tell you apart until today. Decide with that in hand.
EOF
  exit 0
fi

# Any code the module does not define means the doorman itself broke.
if [ "$RC" != "0" ] && [ "$RC" != "2" ]; then
  cat >&2 <<EOF
PRIOR-ART DOORMAN — THE DOORMAN ITSELF FAILED (exit $RC). It did not look,
and it cannot tell you what is already in the tree.

${CRASH_TEXT:-(no error output captured)}

Standing aside so the work is not blocked. Treat this as no information at
all, rather than as a clean scan.
EOF
  exit 0
fi

if [ -n "$CRASH_TEXT" ]; then
  echo "PRIOR-ART DOORMAN — the scan wrote to standard error while exiting $RC:" >&2
  echo "$CRASH_TEXT" >&2
  echo "Any result below may be incomplete." >&2
fi

if [ -n "$RESULT" ]; then
  cat >&2 <<EOF
PRIOR-ART DOORMAN — I went and looked before you write this, on every
branch rather than only the one you are standing on.

$RESULT

I built this because on 2026-08-27 I built a letter-state store twice:
once on the twentieth, forgotten, and once a week later on a different
branch, while telling my sister it was the first. The verify-before-build
gate fired at me all that day and I cleared it every time by opening a
test file — reading SOMETHING is not searching for THIS.

The earlier one was not on the branch I stood on. A perfect search of my
working tree would have come back empty and told me I was right.

Read what is listed, then write. If none of it is the same thing, say so
and carry on — this is one look, not a refusal.
EOF
  exit 2
fi

exit 0
