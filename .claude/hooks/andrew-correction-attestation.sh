#!/bin/bash
# PreToolUse gate — integration-attestation for Andrew-corrections.
#
# Aria audit 2026-05-18 fix #2 + Andrew's directives (enforcement-is-
# priority-one, bullet-wound-clause, code-does-not-think, energy-vessel-
# model-will). The Andrew-correction-attribution SURFACE I shipped
# earlier was display-only — bullet-wound-clause names that as bandaid.
#
# This gate refuses substantive tool use (Bash/Edit/Write) when there
# are OPEN Andrew-corrections AND no attestation event has been
# recorded in the current session, unless the operator has set the
# named bypass env var.
#
# Fires once per session per tool-class (so daily work isn't blocked
# constantly — only the first attempt before an attestation).
#
# Bypass: DIVINEOS_ANDREW_ATTESTATION_DEFER=1 (and explain in the
# next andrew-correction defer reason).
#
# Fail-open: any error exits 0. The gate must never break work via
# its own malfunction; that would be a different failure.

set -u

# Drain stdin so the harness does not block on an unread pipe.
cat >/dev/null 2>&1 || true
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

if [[ "${DIVINEOS_ANDREW_ATTESTATION_DEFER:-0}" == "1" ]]; then
    PYTHON_BIN="$(which python 2>/dev/null || which python3 2>/dev/null || echo python)"
    "$PYTHON_BIN" -c "
try:
    from divineos.core.bypass_telemetry import record_bypass
    record_bypass(
        gate_name='andrew-correction-attestation',
        env_var='DIVINEOS_ANDREW_ATTESTATION_DEFER',
    )
except Exception:
    pass
" >/dev/null 2>&1 || true
    exit 0
fi

# Resolve python
PYTHON_BIN="$(which python 2>/dev/null || which python3 2>/dev/null || echo python)"

ATTESTATION_MARKER="${HOME}/.divineos/andrew_attestation_$(date +%Y-%m-%d).marker"

# If today's attestation has already been performed, allow.
if [[ -f "$ATTESTATION_MARKER" ]]; then
    exit 0
fi

# Check open corrections via the OS.
OPEN_COUNT="$("$PYTHON_BIN" -c "
try:
    from divineos.core.andrew_correction_tracker import integration_rate
    print(integration_rate().get('open', 0))
except Exception:
    print(0)
" 2>/dev/null || echo 0)"

if [[ "$OPEN_COUNT" == "0" ]]; then
    # Nothing outstanding; allow.
    exit 0
fi

# We have open corrections and no today-attestation. Block via JSON
# permission decision so Claude Code surfaces the message.
cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED by andrew-correction-attestation gate. ${OPEN_COUNT} OPEN Andrew-corrections require attestation before substantive tool use today. Address one of them with: \n  divineos andrew-correction integrate <id> --evidence \\\"<commit/behavior/where it landed>\\\" \nOR explicitly defer with: \n  divineos andrew-correction defer <id> --reason \\\"<named reason >= 20 chars>\\\" \nOR (bypass for genuine emergency): set DIVINEOS_ANDREW_ATTESTATION_DEFER=1 and explain in the next defer reason. Reading the open corrections: divineos andrew-correction list. Andrew 2026-05-18 directives bullet-wound-clause + enforcement-is-priority-one + Aria audit fix #2."
  }
}
JSON
exit 0
