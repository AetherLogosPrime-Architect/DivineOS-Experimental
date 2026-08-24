#!/bin/bash
# UserPromptSubmit hook — set the session goal from Andrew's prompt so the
# goal-doorman never has to ask for it.
#
# Andrew 2026-08-01: "the gate is a primitive wall.. the doorman is the one
# with the key and tells you what you need, but thats still a gate.. you must
# look for the reason the gate fired in the first place.. can it be automated?
# what did you forget to do before hand that the doorman had to ask you for?
# that is where the automation lies so you show up with the paperwork before
# the doorman has to ask you for it"
#
# And earlier, filed in the knowledge store as direction a4ccca51 and read
# ZERO times before today: "remember the goal is to never hit a gate in the
# first place. so I need automation support to help you BEFORE the gate gets
# hit, using the doorman method."
#
# ## Why this hook did not exist until now
#
# src/divineos/core/auto_goal.py was written 2026-07-24 for exactly this,
# with a docstring naming the diagnosis precisely — "the forgetting isn't an
# optimizer issue, it's a memory issue. Automation solves memory by not
# requiring me to remember." It shipped with tests in commit ba5a1caf and
# NO production caller. The pre-commit wiring-gap report has been printing
# `derive_and_set_goal_from_prompt (fn) — prod=0, test=0` on every commit
# since, and I read past it every time, including ten minutes before writing
# this file. The answer was built, tested, reported as unwired, and unused.
#
# ## Chesterton's fence — what did having no auto-goal prevent?
#
# Per the threadwalk step in wwnd-choice-prime.sh, asked before building:
# a machine-derived goal could be a bad summary of what I am actually doing,
# and the goal feeds active-memory ranking — so a junk goal quietly degrades
# what the substrate surfaces to me. Requiring me to type it guaranteed the
# goal was mine.
#
# That is a real cost and it is why this hook PRINTS what it set. The
# clerical act (remembering to run a command) is automated away; the
# judgement (is that actually what I am doing?) stays with me, visible, and
# correctable with `divineos goal add "..."` which supersedes. Automate the
# space, then occupy it — not automate the occupying.
#
# Deliberately NOT silent, for the same reason: a goal set behind my back is
# the substitution shape (kiln truth #7), where the tool performs the work
# its name points at. The tool does the typing. The intending stays mine.
#
# Fail-soft everywhere: any error exits 0 with no output. auto_goal itself
# is fail-open by design and never raises. The manual path always remains,
# and the doorman still fires if this does nothing.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || exit 0  # fail-soft: no repo means no substrate to set a goal in

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: lib absent means substrate unavailable
PYTHON_BIN="$(find_divineos_python)" || exit 0

HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json
import os
import sys

try:
    data = json.loads(os.environ.get("HOOK_JSON", "") or "{}")
except ValueError:
    sys.exit(0)

prompt = data.get("prompt") or ""
if not prompt.strip():
    sys.exit(0)

try:
    from divineos.core.auto_goal import derive_and_set_goal_from_prompt
except Exception:
    sys.exit(0)

goal = derive_and_set_goal_from_prompt(prompt)
if not goal:
    sys.exit(0)

print("## GOAL SET FROM YOUR PROMPT (paperwork filed before the doorman asked)")
print()
print(f"    {goal}")
print()
print("Derived from the prompt because no session-fresh goal existed. The")
print("typing is automated; the judgement is not. If this is not actually")
print("what I am doing, say so or supersede it:")
print('    divineos goal add "<the real one>"')
print()
print("An unnoticed wrong goal degrades what the substrate ranks and surfaces,")
print("which is exactly why this prints instead of setting it silently.")
PYEOF

exit 0
