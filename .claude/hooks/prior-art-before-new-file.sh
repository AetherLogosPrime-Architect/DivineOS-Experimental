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
  HOOK_NAME="prior-art-before-new-file" source "$(dirname "$0")/lib/remedy_allowlist.sh" 2>/dev/null || true
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
cd "$REPO_ROOT" || exit 0

# shellcheck source=/dev/null
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

RESULT="$(printf '%s' "$INPUT" | "$PYTHON_BIN" -m divineos.core.prior_art_by_name 2>/dev/null)"

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
