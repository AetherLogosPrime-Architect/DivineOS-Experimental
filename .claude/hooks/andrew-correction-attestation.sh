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
# Bypass: NONE (Andrew 2026-05-19). The agent-settable env-var
# bypass that previously existed was self-authorization defeating the
# gate. To override, edit this hook in a visible commit. The
# integrity cost of bypassing engagement with Andrew-corrections is
# always greater than any single-tool-call benefit, by construction.
#
# Fail-open: any error exits 0. The gate must never break work via
# its own malfunction; that would be a different failure.

set -u

# Drain stdin so the harness does not block on an unread pipe.
cat >/dev/null 2>&1 || true
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# Andrew 2026-05-19: agent-settable bypass env var removed. The
# DIVINEOS_ANDREW_ATTESTATION_DEFER=1 escape was self-authorization
# at the bypass layer, which defeats the gate's purpose
# (code-does-not-think directive: auto-classify-as-acceptable is the
# failure mode). No legitimate emergency case for skipping engagement
# with Andrew-corrections that's worth more than the integrity cost.
# To genuinely override this gate: edit this file in a commit Andrew
# can see in git. Visibility-as-bypass-cost.

# Resolve python via the shared helper (also sets PYTHONPATH to the
# active worktree's src/ — silent-stale-substrate fix 2026-05-19).
# Aether 2026-05-19: CI test test_no_hook_uses_bare_python_for_divineos_imports
# caught this hook using bare `which python`, which silently falls back
# to system python without divineos installed and without the lepos
# gate's PYTHONPATH-prepend protection.
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

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
    "permissionDecisionReason": "BLOCKED by andrew-correction-attestation gate. ${OPEN_COUNT} OPEN Andrew-corrections require attestation before substantive tool use today. Address one of them with: \n  divineos andrew-correction integrate <id> --evidence \\\"<commit/behavior/where it landed>\\\" \nOR explicitly defer with: \n  divineos andrew-correction defer <id> --reason \\\"<named reason >= 20 chars>\\\" \nNo env-var bypass exists (Andrew 2026-05-19: agent-settable bypasses defeat the gate's purpose). To genuinely override, edit the hook in a visible commit. Reading the open corrections: divineos andrew-correction list."
  }
}
JSON
exit 0
