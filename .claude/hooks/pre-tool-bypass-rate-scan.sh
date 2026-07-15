#!/bin/bash
# PreToolUse — fire bypass_rate_scan on substrate-modifying tool calls.
# Wires the EvidenceBearingStopGate CrossTurnScan concrete instance
# (bypass_rate_scan) into actual enforcement, closing the loop that
# Andrew flagged 2026-07-15: "if they are not wired how do you expect
# them to work?"
#
# Fires when:
#   - Bypass rate exceeds threshold in the recent window AND
#   - No investigation-shape action (GATE_CLEARANCE for bypass_rate_scan,
#     AUDIT_ROUND_CREATED, or CLAIM_FILED) has occurred since the most
#     recent GATE_FIRE for this gate.
#
# Clearing:
#   - divineos audit submit-round '<focus>' --actor external-auditor
#   - divineos claim '<statement>'
#   - Any GATE_CLEARANCE event for bypass_rate_scan
#
# Fail-open: any hook failure exits 0 so the gate cannot break work.
#
# Kill-switch (requires >=20 char reason in marker file):
#   echo "why this bypass is needed and root-cause plan" > "$HOME/.divineos-aether/bypass-rate-scan.disabled"

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0

MARKER="$HOME/.divineos-aether/bypass-rate-scan.disabled"
if [ -f "$MARKER" ]; then
    REASON=$(tr -d '\r' < "$MARKER")
    if [ ${#REASON} -ge 20 ]; then
        exit 0
    fi
fi

PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    exit 0
fi

TOOL_NAME=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('tool_name',''))" 2>/dev/null)

case "$TOOL_NAME" in
    Write|Edit|MultiEdit|NotebookEdit)
        ;;
    Bash)
        COMMAND=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)
        case "$COMMAND" in
            *"git commit"*|*"git push"*)
                ;;
            *)
                exit 0
                ;;
        esac
        ;;
    *)
        exit 0
        ;;
esac

OUTPUT=$(printf '%s' "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.bypass_rate_hook 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 2 ]; then
    printf '%s\n' "$OUTPUT" >&2
    exit 2
fi

exit 0
