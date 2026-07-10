#!/bin/bash
#
# INTENTIONALLY UNWIRED (documented 2026-07-09 after Aletheia audit).
#
# The council_required field on the gravity classifier is currently a
# MEASUREMENT, not a pre-edit block — see the honesty note in
# src/divineos/core/gravity_classifier.py:49-58: "Real enforcement (block
# the edit until evidence of a real council walk exists, substance-
# binding-style) is a deferred follow-up tracked as its own design work,
# not implemented by this commit." Wiring this hook now would fire the
# block before the enforcement path was designed to go live.
#
# This file remains executable so it can be registered later without
# code changes when the deferred enforcement design lands. Do not
# register in .claude/settings.json until that design work completes.
#
# PreToolUse council-required enforcement gate.
#
# Fires before substrate-modifying tool calls. If the gravity
# classifier marks the proposed edit as council-required AND no
# substance-bound council walk record exists for the edit, the hook
# exits non-zero (BLOCKING) with a stderr message explaining what
# would clear it. Otherwise exits 0 (ALLOW).
#
# Per prereg-3fbddd75fc16 + supplementary prereg-c3a34984f3d8 (Aether
# peer-review catches 1-6). Implementation lives in
# src/divineos/core/council_required/. This script is a thin
# entry-point per the doorman-refactor discipline.

set -u

INPUT=$(cat 2>/dev/null || true)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD per Aletheia audit 2026-07-09 Deep Truck 1: a silently-skipped
    # enforcement gate is indistinguishable from a gate that ran clean. Record
    # the skip to stderr so a resolver-drift is investigable, not invisible.
    echo "  [check-council-required] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

echo "$INPUT" | "$PYTHON_BIN" -c "
import json
import sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {}) or {}

bash_command = ''
file_paths: tuple[str, ...] = ()
if tool_name == 'Bash':
    bash_command = str(tool_input.get('command', '') or '')
elif tool_name in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
    fp = tool_input.get('file_path', '') or ''
    if fp:
        file_paths = (str(fp),)

# If neither path nor command, this is not an edit we can gate on.
if not file_paths and not bash_command:
    sys.exit(0)

try:
    from divineos.core.council_required import gate as gate_mod
    from divineos.core.council_required.types import GateOutcome, _normalize_edit_fingerprint
    from divineos.core.gravity_classifier import score_substrate_modification
    from divineos.cli.council_required_commands import _load_expert_keywords
except Exception as e:
    # Fail-safe: if the council module fails to import, do not block
    # the edit. The hook is observational-only when its own substrate
    # is broken. Audit-trail this via stderr (visible in hook logs).
    sys.stderr.write(f'[council-required] import failed, gate disabled: {e}\n')
    sys.exit(0)

try:
    decision = gate_mod.decide(
        tool_name=tool_name,
        file_paths=file_paths,
        bash_command=bash_command,
        gravity_fn=score_substrate_modification,
        keywords_loader=_load_expert_keywords,
    )
except Exception as e:
    sys.stderr.write(f'[council-required] gate.decide raised, gate disabled this turn: {e}\n')
    sys.exit(0)

if decision.outcome == GateOutcome.ALLOW:
    # Silent allow — the gate did its job and got out of the way.
    sys.exit(0)

if decision.outcome == GateOutcome.EMERGENCY_SKIP:
    sys.stderr.write(
        f'[council-required] EMERGENCY_SKIP fired for this edit (corroborator '
        f'event_id={decision.corroborator_event_id}). Andrew will see this and '
        f'verify-or-reject at next composition.\n'
    )
    sys.exit(0)

# BLOCK: render the formatted message to stderr; non-zero exit signals
# the hook framework to surface the message and prevent the tool call.
primary = file_paths[0] if file_paths else (bash_command.split()[0] if bash_command else '')
fp = _normalize_edit_fingerprint(primary, tool_name)
msg = gate_mod.format_block_message(decision, fingerprint=fp)
sys.stderr.write(msg + '\n')
sys.exit(2)
"

# Propagate the Python exit code.
exit $?
