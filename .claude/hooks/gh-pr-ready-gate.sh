#!/bin/bash
# PreToolUse hook — route `gh pr ready` through `divineos stamp-ready`.
#
# Root cause (Andrew 2026-08-12): PR #409 was taken out of draft and
# reported ready, then failed the External-Review trailer check when he
# pulled it. The trailer machinery all existed — push-ready amends
# trailers onto branch commits, prepare-merge validates a round and
# prints a paste-able body, gh-pr-merge-gate refuses an untrailered
# merge — but nothing watched the draft->ready transition, and GitHub
# builds the squash message from the PR body, not from branch commits.
# So a branch could be green and the merge still untrailered.
#
# `divineos stamp-ready <pr>` does the transition as one act: validate
# the round, write the trailer into the PR body, then clear the draft
# flag. This gate removes the option to do it the other way — truth #11
# remediation (a), take the option away rather than remember not to
# take it.
#
# `gh pr ready --undo` is pulling a PR BACK to draft. That direction is
# always safe and is never gated.
#
# Fail-open on infrastructure errors; the block itself is deliberate.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD: a silently-skipped gate is indistinguishable from a gate
    # that ran clean. Bare `python3` on this box resolves to the Windows
    # Store stub, which exits 49 and gates nothing.
    echo "  [gh-pr-ready-gate] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, re, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

if (data.get('tool_name') or '') != 'Bash':
    sys.exit(0)
cmd = (data.get('tool_input') or {}).get('command') or ''
if not cmd.strip():
    sys.exit(0)

# Must be at a command position -- start of the line, or just after a
# separator. Without this anchor the gate fires on the words appearing
# inside a quoted argument to some unrelated command, which is exactly
# how it blocked an 'audit submit-round' whose focus text described it.
COMMAND_START = r'(?:^|[;&|]|&&|\|\||\n)\s*'
if not re.search(COMMAND_START + r'gh\s+pr\s+ready\b', cmd):
    sys.exit(0)
# Only the draft -> ready direction. --undo goes the safe way.
if '--undo' in cmd:
    sys.exit(0)

m = re.search(COMMAND_START + r'gh\s+pr\s+ready\s+(\d+)', cmd)
pr = m.group(1) if m else '<pr-number>'

sys.stderr.write(
    'GH-PR-READY-GATE — taking a PR out of draft is the moment the\n'
    'External-Review trailer has to exist, and bare \`gh pr ready\` does not\n'
    'write one. GitHub builds the squash-merge message from the PR BODY, so\n'
    'a trailer that lives only on a branch commit does not survive the merge.\n'
    'That is how #409 went ready and still failed the trailer check.\n'
    '\n'
    'Use instead:\n'
    '    divineos stamp-ready ' + pr + '\n'
    '\n'
    'It validates the audit round carries both CONFIRMS, writes the trailer\n'
    'into the PR body, and only then clears the draft flag. If the round is\n'
    'not confirmed it refuses and names which CONFIRMS is missing.\n'
    '\n'
    'Preview without changing anything:  divineos stamp-ready ' + pr + ' --dry-run\n'
    'Pull a PR back to draft (never gated):  gh pr ready --undo ' + pr + '\n'
)
sys.exit(2)
"
