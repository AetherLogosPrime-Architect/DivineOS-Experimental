#!/bin/bash
#
# STATE (updated 2026-07-16 per Marc audit finding #5 + Aria close):
# The "deferred follow-up" the prior comment named as pending has
# ACTUALLY landed. The enforcement machinery lives in full at
# src/divineos/core/council_required/ (types, store, substance_binding,
# gate) and this script's Python invocation drives gate.decide() +
# format_block_message() correctly.
#
# Test coverage landed 2026-07-16 in tests/test_council_required_gate.py:
# 10 tests covering silent-allow, no-record BLOCK, substance-binding
# BLOCK, ALLOW + consume-on-use, emergency-skip corroborated, emergency-
# skip missing-corroborator BLOCK, corroborator scope design pin,
# concurrent-decide race probe (exactly one ALLOW under contention),
# and fingerprint normalization edges.
#
# IT IS WIRED, AND HAS BEEN SINCE THE DAY THAT WAS WRITTEN (corrected
# 2026-09-15). The paragraph that stood here said registration was still
# pending Andrew's approval and told the reader to add the entry when he
# said yes. Measured: it is registered in .claude/settings.json under
# Edit|Write|Bash|MultiEdit|NotebookEdit, and the commit that put it there
# lands 2026-07-16 -- the same date as the note claiming it had not
# happened. So the note was false within hours of being true, and stayed
# up for two months.
#
# The cost was not hypothetical. On 2026-09-15 Andrew asked whether I had
# bypassed the build flow; I had, three times in one evening, and I read
# this paragraph while hunting for why nothing stopped me. It told me the
# enforcement was not connected, which is the most expensive thing a
# comment can say when the enforcement IS connected and is answering
# ALLOW for a different reason.
#
# THE REAL REASON IT ALLOWS, so the next reader does not repeat my hour:
# this hook scores gravity with `score_substrate_modification`, whose
# council-required tier fires at a threshold of 2. A single-area code edit
# scores 1, so it is waved through. The build flow's own scorer, asked
# about the same edit, says gravity 1 owes 2 lenses. Two scorers, two
# answers, and the wired one has the lower bar -- which is why every edit
# of an evening cleared a fully-built, fully-tested council gate.
#
# That disagreement is a live question in front of Andrew as of this
# writing, not a defect to quietly resolve here.
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

if decision.outcome == GateOutcome.OPERATOR_AUTHORIZED_BYPASS:
    # 2026-07-24 fix (BFBA catch, Aria helped find): the gate has been
    # returning this outcome after successfully consuming an operator
    # state_marker via 'divineos council authorize-bypass', but the hook
    # was only branching on ALLOW and EMERGENCY_SKIP, letting this
    # outcome fall through to BLOCK. Result: every authorize-bypass
    # consumed its marker AND blocked the edit anyway — the whole
    # operator-authorization channel was silently broken end-to-end.
    sys.stderr.write(
        f'[council-required] OPERATOR_AUTHORIZED_BYPASS fired for this edit '
        f'(marker consumed: {decision.corroborator_event_id}). Operator '
        f'explicitly authorized via divineos council authorize-bypass; '
        f'gate did its job and got out of the way.\n'
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
