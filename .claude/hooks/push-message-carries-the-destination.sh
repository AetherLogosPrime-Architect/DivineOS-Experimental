#!/usr/bin/env bash
# PreToolUse(Bash) — a background push must use the wrapper, because the
# wrapper's answer is the only one that survives the trip.
#
# Andrew 2026-09-10, correcting a repair of mine: *"so the root cause would be
# fixing the message so it tells you what you need to know on all sides"*.
#
# WHAT I BUILT FIRST, AND WHY IT WAS WRONG. I wrote a hook to report the
# destination after a push. Then I found that hook already exists, wired, and
# correct: verify-push-landed.sh has been reporting the remote's actual state
# since 2026-06-04, built from Aletheia's finding on this exact boundary. Fed a
# branch that is not on origin it says so plainly. Nothing was missing.
#
# SO WHY DID IT NEVER REACH ME. Every push on 2026-09-10 ran in the BACKGROUND,
# and on that path the hook's answer does not arrive. Measured, not assumed:
# its output appears in none of this session's background push logs. What
# arrives instead is a completion notice carrying an exit code.
#
# That is his sentence exactly. The message I actually receive does not tell me
# what I need to know. A hook computes the truth and the trip drops it.
#
# THE ONE THING THAT SURVIVES. scripts/divineos_push.sh prints its verdict as
# the LAST line of its own output, deliberately, so a truncated tail still
# carries it. Andrew built it that way in June after this fault recurred ten
# times in two days. The wrapper solves the background case; the hook cannot,
# because the hook speaks on a channel the background path does not carry.
#
# WHY A DOORMAN AND NOT A LOUDER NOTE. I pushed six times tonight without the
# wrapper. Not once did I decide against it -- it never entered my head, which
# is what "requires remembering at the moment of the reach" means in practice.
# Truth #11: take the option away.
#
# NARROW ON PURPOSE. Only a push, only when the wrapper is not already in the
# line. A foreground push is left alone: there the hook's answer does arrive,
# and refusing it would be ceremony over a channel that already works.
#
# Fail-open, and say so. A broken doorman must not stop a push, but silence
# from a guard is indistinguishable from a guard approving.

set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

case "$INPUT" in
  *push*) ;;
  *) exit 0 ;;
esac

PAYLOAD="$(printf '%s' "$INPUT" | python -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('|'); raise SystemExit
ti = d.get('tool_input') or {}
print((d.get('tool_name') or '') + '|' + (ti.get('command') or '') + '|' + str(ti.get('run_in_background') or ''))
" 2>/dev/null || echo "|")"  # fail-soft: malformed stdin must not hold a push

TOOL="${PAYLOAD%%|*}"
REST="${PAYLOAD#*|}"
CMD="${REST%%|*}"
BACKGROUND="${REST##*|}"

[ "$TOOL" = "Bash" ] || exit 0

case "$CMD" in
  *"git push"*) ;;
  *) exit 0 ;;
esac

# Already using the wrapper, or one of the scripts that calls it.
case "$CMD" in
  *divineos_push*|*safe_push*|*ready_pr*|*check_push_readiness*) exit 0 ;;
esac

# A foreground push keeps the existing reporter, which works there.
case "$BACKGROUND" in
  True|true|1) ;;
  *) exit 0 ;;
esac

cat >&2 <<'EOF'
BACKGROUND PUSH — the answer you will get back does not include the destination.

A background push returns a completion notice carrying an EXIT CODE. That is a
true statement about the command and says nothing about the remote. The hook
that reports the remote does exist and is wired, and its output does not travel
on this path — measured against this session's own background logs, where it
appears zero times.

Use the wrapper, whose verdict is the LAST line of its own output precisely so
a truncated tail still carries it:

    bash scripts/divineos_push.sh <same arguments>

It prints one of: pushed and verified, pushed and unverified, push failed, or
infrastructure error. All four are answers. The exit code alone is not.

Andrew built that wrapper in June after this fault recurred ten times in two
days. I pushed six times tonight without it, and never once decided against it.
EOF
exit 2
