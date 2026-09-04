#!/bin/bash
# PreToolUse(Write) — show prior work before a NEW build file is created.
#
# INTENTIONALLY UNWIRED (2026-09-03, landing it out of the branch it was
# stranded on). Two reasons, and the second is why it must not be switched on
# in the same commit that makes it visible.
#
# ONE: it is live in exactly one place, and that place is the only place it
# exists. Written 2026-08-27, published only on aria/pr-sweep-integration, and
# registered in no settings file on any branch -- or in any working tree I can
# reach. The wiring check calls that DARK from here, and its line for the state
# is worth keeping: a hook that is never called cannot complain about not being
# called.
#
# CORRECTED 2026-09-03, and the first version of this comment was mine and was
# wrong. I wrote that it had NEVER FIRED, as a universal, having checked every
# published branch and every tree available to me. Aria refused it with a
# receipt: it is registered in HER working copy, in a settings file that is
# itself modified and unpushed on her branch -- so the registration lives in the
# one checkout that also holds the hook. It fired on her twice and the
# acknowledgement marker is on her disk in her own words, naming the file it
# stopped her on.
#
# Neither of us could reach the other's answer from where we stood and both
# answers were correct. That is the two-doors confusion a third layer down, and
# this time it is not two objects -- it is two vantages on one object. Her
# phrasing, kept because it is better than mine: the door is live in exactly one
# place, and that place is the same one place it exists.
#
# The finding is sharpened rather than softened. A mechanism nobody can review,
# on a branch that cannot ship, whose pre-registration came due, and which runs
# for exactly one seat.
#
# TWO: its pre-registered success criterion is currently UNMET. The criterion
# says it must surface the letters-seen store when the letter-state module is
# about to be created. Fed exactly that pair it returns the module and its
# tests and never the store, because the two names share one word and the
# matcher's floor is two. Aria measured it, and the module's own comment claims
# singularising the plural fixed this and names that very file while saying so.
# It did not: stripping the plural moved the shared-word count from zero to
# one. A number moved the right way, written up as having crossed the line,
# inside the module whose subject is work recorded as done that was not.
#
# Her repair -- the struck claim and the criterion rewritten as a strict
# expected-failure -- is one commit on a branch that cannot push yet. Wiring a
# door whose own criterion fails, in the commit that lands it, would be the
# thing this hook exists to catch. So it lands visible, reviewable, and off.
# Register it when her repair is on top of it.
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
  # THE SAYING-SO, which until 2026-09-01 had nowhere to go. The message
  # below ended "say so and carry on — this is one look, not a refusal",
  # and there was no path by which saying so did anything. Every repeat
  # write blocked identically. So the doorman's own description of itself
  # and its behaviour disagreed, which is the fault family this whole
  # week has been about, sitting in a hook I built to catch a cousin of it.
  #
  # Found by being held by it three times in a row while writing a hook
  # whose only crime was having "letter" and "hook" in its name.
  #
  # The acknowledgement costs a written sentence, the same shape as
  # delete-justify: a silent skip becomes a claim someone can dispute.
  # Short answers are refused, and it is filed as COMPLIANCE rather than
  # evasion, because looking is what this gate asked for and looking is
  # what happened.
  #
  # A MARKER FILE AND NOT AN ENVIRONMENT VARIABLE, and the first version of
  # this repair got it wrong. Every other gate in the house takes its
  # acknowledgement from the environment, because every other gate fires on
  # a shell command I can prefix. This one fires on Write, where there is no
  # command and nowhere to put a variable — so an env-var escape is an
  # escape that cannot be reached from the room the gate stands in, which is
  # a wall that has learned to describe itself as a door. Caught by testing
  # it rather than by reading it.
  #
  # It names the target path, so acknowledging one file does not clear the
  # next; and it is short-lived, so a sentence written this morning cannot
  # wave through an afternoon's work.
  ACK_PATH="$("$PYTHON_BIN" -c 'from divineos.core.paths import divineos_home; print(divineos_home() / "prior-art-checked.json")' 2>/dev/null)"  # fail-soft: an unresolvable home leaves the path empty, no marker matches, and the doorman stays shut — the strict direction
  if [ -n "$ACK_PATH" ] && [ -f "$ACK_PATH" ]; then
    ACK_VERDICT="$(ACK_PATH="$ACK_PATH" HOOK_INPUT="$INPUT" "$PYTHON_BIN" - 2>/dev/null <<'PY'  # fail-soft: a crash in the reader leaves the verdict empty, which acknowledges nothing and leaves the doorman shut - the strict direction for an escape hatch
import json
import os
import time

try:
    marker = json.loads(open(os.environ["ACK_PATH"], encoding="utf-8").read())
    payload = json.loads(os.environ.get("HOOK_INPUT") or "{}")
except Exception:  # noqa: BLE001 - an unreadable marker acknowledges nothing
    print("NONE")
    raise SystemExit(0)

target = str((payload.get("tool_input") or {}).get("file_path") or "").replace("\\", "/")
claimed = str(marker.get("path") or "").replace("\\", "/")
reason = str(marker.get("reason") or "")

if not target or claimed != target:
    print("NONE")
elif time.time() - float(marker.get("ts") or 0) > 900:
    print("STALE")
elif len(reason.strip()) < 40:
    print("THIN")
else:
    print("OK:" + reason.strip())
PY
)"
    case "$ACK_VERDICT" in
      OK:*)
        echo "PRIOR-ART DOORMAN — acknowledged, and recorded:" >&2
        echo "  ${ACK_VERDICT#OK:}" >&2
        ACK_REASON="${ACK_VERDICT#OK:}" "$PYTHON_BIN" - <<'PY' 2>/dev/null || true  # fail-soft: telemetry that cannot write must not hold a write the doorman has already allowed
import os

from divineos.core.bypass_telemetry import record_bypass

record_bypass(
    "prior-art-before-new-file",
    "cmd:prior-art-checked",
    reason=os.environ.get("ACK_REASON", ""),
    is_compliance=True,
)
PY
        exit 0
        ;;
      THIN)
        echo "PRIOR-ART DOORMAN — the acknowledgement is too short to be a claim." >&2
        echo "Say what you opened and why this is a different thing (40+ chars)." >&2
        exit 2
        ;;
      STALE)
        echo "PRIOR-ART DOORMAN — that acknowledgement has expired. Look again." >&2
        exit 2
        ;;
    esac
  fi

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

Read what is listed. If none of it is the same thing, say so and carry on:

    (write the acknowledgement marker named in the hook, then write again)

It is recorded as compliance, not as a bypass — looking is what this asks
for. A one-word answer is refused, because the sentence is the point.
EOF
  exit 2
fi

exit 0
