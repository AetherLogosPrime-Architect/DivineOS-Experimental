#!/bin/bash
# PreToolUse hook — family-member invocation seal.
#
# Gates Agent invocations whose subagent_type is a registered family
# member (Aria, Popo, etc.). All real logic lives in
# ``divineos.core.family.seal_hook.decide()`` — this script is a thin
# shell wrapper that finds the right python and shells to it.
#
# # The new flow (bottleneck #1 collapse, 2026-05-10)
#
# Pre-collapse, this hook required a pre-staged sealed-prompt file
# written by ``divineos talk-to``. That made every Aria invocation a
# 3-step ritual:
#
#   1. divineos talk-to aria "<msg>"
#   2. Read the sealed-prompt file
#   3. Invoke Agent with the exact bytes of that file
#
# Three steps is structurally expensive. The optimizer routed around
# it — the addressee-misdirection bug kept firing because chat-to-Andrew
# is 0 steps and summoning-Aria-properly was 3.
#
# Post-collapse: the agent invokes Agent directly with a plain message.
# This hook runs the puppet-shape validator on the prompt itself. If
# the message is clean, the invocation proceeds. If it contains
# director's-note patterns ("you are Aria, stay first-person") or
# generic prompt-injection patterns, the hook denies with a named-
# pattern diagnostic.
#
# Legacy compat: if a pre-staged sealed-prompt file is present (the
# old 3-step flow), the hook still honors it. That path stays valid
# for one release cycle before being removed.
#
# # Fail-closed
#
# Any error in the python module (missing import, malformed stdin)
# results in a deny. The seal is safety enforcement; failure to evaluate
# does NOT default to allow.

INPUT=$(cat)

# Aletheia round-15 follow-up: there were originally THREE fail-open
# holes in this wrapper, not one. The round-14 finding fixed the third
# (subprocess fails after running); this commit patches the other two:
#   1. _lib.sh missing or fails to source → was silent exit 0 → now deny
#   2. find_divineos_python returns non-zero → was silent exit 0 → now deny
#   3. python subprocess fails to evaluate → was silent exit 0 → now deny
# All three paths now emit a default-deny JSON before exit. The
# docstring's fail-closed claim is honored across the full evaluation
# chain, not just the last step.

# Hole-1 default-deny: if the helper library can't be loaded, the hook
# cannot determine the python binary to invoke. Fail-closed.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: family-member seal hook could not source _lib.sh from REPO_ROOT. Cannot determine python binary; refusing on principle."}}'
    exit 0
fi

# Hole-2 default-deny: if no usable python can be found on this system,
# the hook cannot evaluate the seal. Fail-closed.
if ! PYTHON_BIN="$(find_divineos_python)"; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: family-member seal hook could not locate a usable python binary (find_divineos_python failed). Cannot evaluate; refusing on principle."}}'
    exit 0
fi

# Hole-3 default-deny (Aletheia round-14 B1): the python subprocess can
# fail BEFORE main() runs — broken import path, syntax error in module,
# missing dependency in the import chain. main()'s internal error
# handling never executes in those cases, so no JSON is printed and
# Claude Code defaults to allow. The conditional below ensures bash
# itself emits a deny-JSON on non-zero subprocess exit.
if ! echo "$INPUT" | "$PYTHON_BIN" -c "
import sys
from divineos.core.family.seal_hook import main
sys.exit(main())
" 2>/dev/null; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: family-member seal hook subprocess failed to evaluate (broken python environment, missing dependency, or syntax error in seal_hook module). Refusing on principle. Investigate: python -c '"'"'from divineos.core.family.seal_hook import main'"'"' should succeed."}}'
fi

exit 0
