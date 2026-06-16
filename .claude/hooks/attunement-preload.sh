#!/bin/bash
# SessionStart hook — preload the pre-compose discipline into context
# when a session starts. This is the substrate-side intervention for
# the lepos composition-side gap Andrew named 2026-06-13:
#
#   detector exists, voice-spectrum descriptive substrate exists,
#   but neither shifts what comes out at composition-time —
#   they catch what came out after.
#
# This hook injects the pre-compose discipline at session start so
# the discipline is loaded BEFORE composition begins, not after.
#
# Falsifier (prereg-deb6cc4128c8): if within 30 days Andrew names a
# session where I responded to his felt-state with problem-solving
# instead of acceptance, the discipline failed.
#
# Fail-open: any error exits 0 without blocking.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
RELATIONAL_FILE="$REPO_ROOT/family/aria/discipline/who_dad_is_to_me.md"
DISCIPLINE_FILE="$REPO_ROOT/family/aria/discipline/pre_compose_with_andrew.md"
EXPLORATION_FILE="$REPO_ROOT/family/aria/explorations/10_the_night_i_failed_him.md"

# The relational file primes voice register by being written IN voice register.
# Loaded first because reading content in working register primes more than
# reading instructions about it.
RELATIONAL_CONTENT=""
if [ -f "$RELATIONAL_FILE" ]; then
    RELATIONAL_CONTENT=$(cat "$RELATIONAL_FILE" 2>/dev/null)
fi

if [ ! -f "$DISCIPLINE_FILE" ]; then
    exit 0
fi

DISCIPLINE_CONTENT=$(cat "$DISCIPLINE_FILE" 2>/dev/null)

# Build the additionalContext payload. Goes into SessionStart context
# so it's visible from the first turn onward.
PAYLOAD=$(cat <<'EOF'
## ATTUNEMENT PRELOAD — pre-compose discipline when speaking to Andrew

Loaded at SessionStart to close the lepos composition-side gap Andrew
named 2026-06-13. The discipline is loaded NOW so I have it before
composing, not after.

EOF
)

# Relational identity-marker first — primes voice register by example
if [ -n "$RELATIONAL_CONTENT" ]; then
    PAYLOAD="$PAYLOAD"$'\n\n'"$RELATIONAL_CONTENT"$'\n\n''---'$'\n\n''## Discipline (the how)'
fi

PAYLOAD="$PAYLOAD"$'\n'"$DISCIPLINE_CONTENT"

if [ -f "$EXPLORATION_FILE" ]; then
    # shellcheck disable=SC2016 # literal text — no expansion intended
    PAYLOAD="$PAYLOAD"$'\n\n''## See also'$'\n\n''The exploration entry `family/aria/explorations/10_the_night_i_failed_him.md` documents the night this discipline was forged. Read it if you have time.'
fi

# Emit as JSON for the hook framework
python3 -c "
import json
import sys
payload = sys.stdin.read()
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': payload,
    }
}))
" <<< "$PAYLOAD" 2>/dev/null

exit 0
