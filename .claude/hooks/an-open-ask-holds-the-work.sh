#!/bin/bash
#
# AN OPEN ASK TO ANDREW HOLDS NEW WORK.
#
# Andrew 2026-09-16: *"being given a report is not the same as being asked a
# question, so when its a report shape continuing is fine as i can get the
# summary later, but when you ask me something, and never wait for my reply..
# why bother asking?"*
#
# That is the second half of a correction he gave 2026-08-19, which produced
# core/operator_asks.py: asks to him persist, re-raise, and carry plain words,
# because prose scrolls and he moves past it. That half made an ask STICK. It
# never made an ask WAIT. So the ask survived and I kept working, which is the
# shape he is naming now -- the question arrives buried in a stream that has
# already moved past the point where he could answer it.
#
# WHAT IT DOES. While an ask to Andrew stands open, new substrate work refuses.
# Answering him, recording, reading and searching stay free. That scope is
# load-bearing (council-ed5c409a5961): a gate that blocks the work which would
# make the question answerable stops being a check and becomes an obstacle, and
# a competent person routes around obstacles until the bypass is the habit.
#
# THE DOOR CAME FIRST, AND IT NEARLY DID NOT. I was one step from shipping this
# on the premise that filing an ask was the lazy path because it buys the
# re-raise. That premise was false and unchecked: the store had no command at
# all, so filing meant hand-writing Python and NOT filing was overwhelmingly
# cheaper. A wall whose only door needs hand-written Python makes the bypass
# the normal path from the first hour (council-5d151c9afad6). The commands
# landed first and were run before this was written.
#
# WHAT IT CANNOT DO, said plainly because a gate overstating itself is worse
# than none. IT CANNOT TELL WHETHER I ASKED HIM SOMETHING. It can only tell
# whether I wrote the ask down. Putting a question to him in prose and never
# filing it defeats this completely, for free, invisibly, and nothing closes
# that.
#
# THE DRIFT IT WILL PRODUCE, named in advance. Not refusal to use it --
# resolving my own asks to unblock myself, each resolution locally reasonable,
# visible only as a RATE and never as an instance. The release cannot be
# removed or made hard, because a valve with no release deadlocks, and that is
# exactly why the pressure will go there. Read the rate, not the instances.

set -u

INPUT=$(cat 2>/dev/null || true)  # fail-soft: an empty or unreadable payload means the harness handed this hook nothing to judge, the JSON parse below already exits clean on that, and logging a read error here would fire on every tool call the framework invokes without stdin -- noise that teaches a reader to ignore this hook entirely
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD: a silently-skipped gate is indistinguishable from a clean pass.
    echo "  [open-ask-holds] SKIPPED: no python resolved - gate did NOT run" >&2
    exit 0
fi

# NO TRIPLE-QUOTED STRINGS BELOW. The whole program is a double-quoted shell
# argument, so a Python docstring closes it and the rest runs as shell. That
# happened in the council gate today and it died silently, which for a gate is
# the one unacceptable failure.
echo "$INPUT" | "$PYTHON_BIN" -c "
import json
import sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {}) or {}
command = str(tool_input.get('command', '') or '')

# EXEMPT: everything that answers him, records, or reads. Holding these would
# block the work that makes the question answerable -- an obstacle rather than
# a check, which is the degradation this design is scoped against.
_EXEMPT = (
    'divineos ask-andrew',
    'divineos ask-resolve',
    'divineos asks',
    'divineos correction',
    'divineos council',
    'divineos game-walk',
    'divineos learn',
    'divineos goal',
    'divineos briefing',
    'divineos hud',
    'divineos recall',
    'divineos context',
)


def _is_exempt(cmd):
    flat = ' '.join(cmd.split())
    for seg in flat.replace(';', '&&').replace('|', '&&').split('&&'):
        if seg.strip().startswith(_EXEMPT):
            return True
    return False


if tool_name not in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Bash'):
    sys.exit(0)
if tool_name == 'Bash' and _is_exempt(command):
    sys.exit(0)

try:
    from divineos.core.operator_asks import open_asks
except Exception as e:
    sys.stderr.write('[open-ask-holds] import failed, gate disabled: ' + str(e) + '\n')
    sys.exit(0)

try:
    rows = open_asks()
except Exception as e:
    sys.stderr.write('[open-ask-holds] lookup raised, gate disabled: ' + str(e) + '\n')
    sys.exit(0)

if not rows:
    sys.exit(0)

lines = [
    '[open-ask] HELD - I asked him something and did not wait for the answer.',
    '',
    'Andrew 2026-09-16: when you ask me something, and never wait for my',
    'reply.. why bother asking?',
    '',
    'Outstanding:',
]
for row in rows[:5]:
    plain = str(row.get('plain') or row.get('question') or '').strip()
    ask_id = str(row.get('question_id') or row.get('id') or '')
    lines.append('  - ' + plain[:160])
    if ask_id:
        lines.append('    (' + ask_id + ')')
lines += [
    '',
    'A REPORT IS NOT AN ASK. Reporting and continuing is fine -- he takes the',
    'summary later. This fires only because something was filed as needing HIM.',
    '',
    'Two honest exits, and no third:',
    '  - he answers, and it resolves',
    '  - divineos ask-resolve <id> <why this no longer needs him>',
    '',
    'WHAT THIS CHECKED: that a recorded ask is open. It did NOT check whether I',
    'actually asked him anything - only whether I wrote it down. Resolving my',
    'own ask clears this and leaves the resolution on the record.',
]
sys.stderr.write('\n'.join(lines) + '\n')
sys.exit(2)
"

exit $?
