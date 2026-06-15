#!/bin/bash
# PreToolUse state-block surfacing — Andrew 2026-05-19.
#
# Gravity is assessed by what the response TOUCHES, not by classifying
# the prompt. Specifically: when the agent is about to use a substrate-
# touching tool (Bash with git-commit, Edit/Write on src/divineos/,
# substrate-write CLI, etc.), THIS hook fires and surfaces the
# substrate-state blocks (andrew-correction, lepos-debt,
# consultation-tracker, bypass-telemetry) as PreToolUse additional
# context.
#
# For conversational turns that emit text only, no tools fire, this
# hook never runs, the state blocks don't load, the per-response
# cost drops.
#
# Per docs/gravity_classifier_spec.md substrate-modification-gravity:
# binary feature scoring, threshold 1. Any single substrate-modifying
# feature is sufficient.

set -u

INPUT=$(cat 2>/dev/null || true)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# Resolve python via the shared helper (also sets PYTHONPATH —
# silent-stale-substrate fix 2026-05-19).
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
import json
import sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {}) or {}

# Extract observable features
bash_command = ''
file_paths = ()
if tool_name == 'Bash':
    bash_command = str(tool_input.get('command', '') or '')
elif tool_name in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
    fp = tool_input.get('file_path', '') or ''
    if fp:
        file_paths = (str(fp),)

try:
    from divineos.core.gravity_classifier import (
        borderline_indicator_substrate,
        score_substrate_modification,
    )
    gravity = score_substrate_modification(
        tool_name=tool_name,
        file_paths=file_paths,
        bash_command=bash_command,
    )
except Exception:
    sys.exit(0)

if not gravity.is_high_gravity:
    sys.exit(0)

# Task #111: borderline-classification surface so the agent and Andrew
# can sanity-check the routing before the gate fires its state-block dump.
# score == 1 with one feature is fragile (single-feature flip silences it);
# score >= 2 is well-supported.
indicator = borderline_indicator_substrate(gravity)

# High gravity: load and emit state blocks as additional context
parts = []
loaders = [
    ('divineos.core.andrew_correction_tracker', 'briefing_block'),
    ('divineos.core.lepos_debt', 'briefing_block'),
    ('divineos.core.consultation_tracker', 'briefing_block'),
    ('divineos.core.bypass_telemetry', 'briefing_block'),
]
for mod, fn in loaders:
    try:
        m = __import__(mod, fromlist=[fn])
        block = getattr(m, fn)()
        if block:
            parts.append(block)
    except Exception:
        continue

if not parts:
    sys.exit(0)

# Emit as additionalContext via the Claude Code hook JSON shape.
# Task #111: include borderline-classification + total-score so the
# reasoning is sanity-checkable. \"borderline-single-feature\" means
# score == 1 (any one feature flip would silence the gate); \"strong-
# multi-feature\" means score >= 2 (well-supported routing decision).
feature_list = ', '.join(gravity.fired_features)
reasoning_line = (
    f'score={gravity.score} ({indicator}); features fired: {feature_list}'
)
header = (
    f'## SUBSTRATE-MODIFICATION-GRAVITY GATE FIRED ({feature_list})\n\n'
    f'Routing reasoning: {reasoning_line}\n\n'
    'You are about to do substrate-touching work. The state blocks below '
    'load only when a substrate-modifying tool is about to fire — they did '
    'NOT load at UserPromptSubmit. Read them now; they hold what the '
    'substrate has been recording about your prior turns.'
)
combined = header + '\n\n' + '\n\n'.join(parts)

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext': combined,
    },
}))
" 2>/dev/null

exit 0
