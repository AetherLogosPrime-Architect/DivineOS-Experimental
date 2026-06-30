#!/bin/bash
# UserPromptSubmit hook — surface the real token state every turn.
#
# Aether 2026-06-30: I was fabricating token claims all night ("947k of 1M",
# "182/1m") because the measurement tool existed but wasn't pointed at me
# automatically. Pop named the root: "any claims about tokens need verified
# with that tool" — and the structural fix is to inject the measurement
# into my context every turn rather than hope I remember to run the tool.
#
# This hook fires on UserPromptSubmit. It runs `divineos context-tokens`,
# captures the output, and prints a one-line surface. The output lands in
# additionalContext alongside the other UserPromptSubmit injections so the
# real number is in front of me whenever I might be tempted to invent one.
#
# Fail-open: any error exits 0 silently. Never blocks the user prompt.

# Find the repo root from the calling environment.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO_ROOT" || exit 0

# Try to read the token measurement. Suppress stderr; we only want the
# clean stdout line if the tool is healthy. If `divineos` isn't on PATH
# or the tool errors, the surface stays silent (fail-open).
TOKEN_LINE="$(divineos context-tokens 2>/dev/null | head -1)"
if [ -z "$TOKEN_LINE" ]; then
    exit 0
fi

# Print the surface block. UserPromptSubmit hooks have their stdout
# captured and merged into the next user-prompt's additionalContext.
cat <<EOF
## CONTEXT TOKENS (verified — do not fabricate this number)

$TOKEN_LINE

This is the real number from \`divineos context-tokens\`. If you are about
to write a sentence containing token-state language (kb used, % of 1M,
"getting deep", "tokens remaining"), use THIS number, not a guess.
EOF

exit 0
