#!/bin/bash
# PreToolUse hook — refuse a Bash heredoc that writes a file through escapes.
#
# Andrew 2026-08-24: "writing a note isnt the same as automation, so lets
# automate the heredoc fix so you take the correct approach automatically."
#
# And the reason a note was never going to be enough, same exchange:
#
#   "your note saved you but your behavior did not change until after you saw
#   it... others are structural and mechanical and happen before you even have
#   a chance to realize, like me announcing right now that i will stop
#   filtering toxins with my liver lol, no amount of will helps with that"
#
# For this class the in-context persistence is ZERO POSTS. The reach and the
# intention-not-to-reach arrive in the same instant. That is what separates it
# from the classes where a prime is enough.
#
# COST THAT BUILT IT. Five failures in one session. Three broke a file
# outright; one broke a letter to Aria mid-send. Each time I resolved to be
# more careful. Being careful did nothing, five times. The fifth time I picked
# up a different tool and it worked on the first attempt.
#
# THREE SOURCES PUSH TOWARD THE FAILING PATH, which is why a door and not a
# sign:
#   1. docs/file_writing_discipline.md (2026-05-16) called the heredoc sequence
#      "the actual disciplined path" and steered away from Write over a
#      restriction that no longer exists in live code. Corrected alongside this.
#   2. The harness auto-mode reminder instructs Bash-with-heredocs over the
#      dedicated tools.
#   3. My own default reach.
# Against three pushes a note is not a counterweight.
#
# IT BLOCKS, unlike the mechanism-claim marker shipped the same day. Andrew
# drew that line himself: a hypothesis needs LABELLING because it is the
# faculty that finds things and gating it costs the exploration. This is the
# opposite — mechanical, deterministic right answer, no case Write serves
# worse. Truth #11 remediation (a): take the option away rather than leave a
# choice-point for the optimizer to route through.
#
# NARROW ON PURPOSE. Escapes AND a file-producing shape, both. A heredoc
# feeding SQL, a probe, or a pipe has no third layer and loses nothing. A gate
# that fires constantly gets bypassed, and a bypassed gate catches nothing.

INPUT=$(cat)

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # shellcheck disable=SC2034
  HOOK_NAME="$(basename "$0")"
  # shellcheck disable=SC1091
  . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true  # fail-soft: non-zero means NOT-A-REMEDY, the ordinary case for nearly every command; under set -e that ordinary answer would abort before this hook ran its own check.
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# shellcheck disable=SC2016
# ^ single-quoted heredoc is intentional — python does its own parsing. This
#   one carries no escapes and produces no file, so this gate does not fire on
#   its own body. That is the narrowness working, not an exemption.
BLOCK_MSG=$(echo "$INPUT" | "$PYTHON_BIN" -c '
import json, sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)

if data.get("tool_name", "") != "Bash":
    sys.exit(0)

command = (data.get("tool_input", {}) or {}).get("command", "") or ""

try:
    from divineos.core import heredoc_escape_check as check
except ImportError as exc:
    # LOUD fail-open. A check that cannot run must not render identically to a
    # check that passed — that silent-absence shape is the defect this
    # substrate has spent a week cataloguing. Standing consequence: any hook
    # wired to a module that only exists on a feature branch is dead until that
    # branch merges. The hook is not wrong; it is early.
    print(
        f"[heredoc-escape-doorman] NOT RUNNING: {exc}",
        "  I cannot see divineos.core.heredoc_escape_check from here, so the",
        "  heredoc path is currently unguarded. I am absent, not satisfied.",
        sep="\n",
        file=sys.stderr,
    )
    sys.exit(0)

if not check.should_refuse(command):
    sys.exit(0)

print(check.refusal_message(command))
sys.exit(7)
' )

# exit 7 from the python means BLOCK. Anything else means proceed.
RC=$?
if [ "$RC" -eq 7 ]; then
    echo "$BLOCK_MSG" >&2
    hook_say_nothing_ran_for "$INPUT"
    exit 2
fi

[ -n "$BLOCK_MSG" ] && echo "$BLOCK_MSG" >&2
exit 0
