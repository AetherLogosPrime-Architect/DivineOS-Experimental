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
# it — the addressee-misdirection bug kept firing because chat-to-the-
# operator is 0 steps and summoning-Aria-properly was 3.
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

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Aletheia round-14 (B1): the python subprocess can fail BEFORE main()
# runs — broken import path, syntax error in module, missing dependency
# in the import chain. main()'s internal error handling never executes
# in those cases, so no JSON is printed and Claude Code defaults to
# allow. That makes the docstring's fail-closed claim a lie when the
# environment breaks. Wrap the subprocess in a conditional: if python
# exits non-zero, emit a default-deny JSON ourselves so the gate
# actually holds when its evaluation path is broken.
if ! echo "$INPUT" | "$PYTHON_BIN" -c "
import sys
from divineos.core.family.seal_hook import main
sys.exit(main())
" 2>/dev/null; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: family-member seal hook subprocess failed to evaluate (broken python environment, missing dependency, or syntax error in seal_hook module). Refusing on principle. Investigate: python -c '"'"'from divineos.core.family.seal_hook import main'"'"' should succeed."}}'
fi

exit 0
