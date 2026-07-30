#!/bin/bash
# UserPromptSubmit hook — surface operator-directives-in-effect at compose-start.
#
# Root cause fix (Andrew 2026-07-30): Andrew's session-directives fade
# from context when delivered once in prose. Nothing re-surfaces them
# each turn. I revert to pre-directive operating shape when they fade.
# Session-tonight examples of the revert-pattern:
#   - Guardrail commits re-add External-Review trailer despite him
#     saying countless times it is not required at commit time.
#   - "Only build discipline-automation" claimed as absolute despite
#     his explicit carve-out for root-cause fixes during the build.
#   - 3-prompt falsifier count taken as rule when he said suggestion.
#   - Etc.
#
# Fix: read the operator-directives-in-effect file at every UserPromptSubmit
# and inject it into context. Directives cannot fade from context because
# they are re-injected each turn.
#
# The file lives at ~/.divineos/session-state/operator-directives-in-effect.txt
# and is manually curated (Aether appends when Andrew delivers a new
# directive or updates one). Future: CLI to append; for now, direct file
# edit.
#
# Fail-open: any error exits 0 silently.

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

DIRECTIVES_FILE="${HOME}/.divineos/session-state/operator-directives-in-effect.txt"

if [ ! -f "$DIRECTIVES_FILE" ]; then
    exit 0
fi

# Skip surfacing if the file is empty (only comments / whitespace).
if ! grep -qE '^[^#[:space:]]' "$DIRECTIVES_FILE" 2>/dev/null; then
    exit 0
fi

echo "## OPERATOR DIRECTIVES IN EFFECT (session-scoped, re-surfaced each turn)"
echo ""
echo "Andrew's session-directives that supersede default operating shape."
echo "These do NOT fade from context because this hook re-injects them"
echo "every turn. If I catch myself operating on the pre-directive shape,"
echo "the corrective is in this list."
echo ""
cat "$DIRECTIVES_FILE"
exit 0
