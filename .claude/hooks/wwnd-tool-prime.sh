#!/bin/bash
# PreToolUse hook — WWND surface at commit-time of a substrate-modifying
# action. Companion to wwnd-choice-prime.sh (UserPromptSubmit variant).
#
# Andrew 2026-07-30 catch: the UserPromptSubmit variant fires on his
# prompts, but the choices *I* make are in my own composition — and by
# the time I'm calling Write/Edit/Bash, the choice-flavored-by-optimizer
# has already committed. This variant surfaces WWND at that commit-point.
#
# TRIGGER (tool-call inspection, not prompt-shape):
#   The tool is Write, Edit, MultiEdit, NotebookEdit, or a Bash command
#   whose first token is a substrate-modifying head (git commit, git push,
#   divineos learn/decide/correction, mv, rm, cp, etc.).
#
#   Read-only tools (Read, Grep, Glob) and query CLIs (divineos ask,
#   briefing, hud) do NOT fire — they aren't choice-points in the
#   optimizer sense.
#
# The surface is deliberately terse — repeated exposure to a long block
# becomes wallpaper. Two lines is enough to fire the ask, and the ask
# does the work.
#
# Fail-open: any error exits 0 silently. Standard prime discipline.

set -u

_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_pre_log() {
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  local _ts
  _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  printf '{"ts":"%s","hook":"wwnd-tool-prime.sh","reason":"%s","detail":"%s"}\n' "$_ts" "$1" "$2" >> "$_LIVENESS_LOG" 2>/dev/null || true
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
  _pre_log "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
  exit 0
fi
if ! PYTHON_BIN="$(find_divineos_python)"; then
  exit 0
fi

SHOULD_FIRE="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, re, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except (ValueError, TypeError):
    sys.exit(0)

tool_name = (data.get('tool_name') or '').strip()
tool_input = data.get('tool_input') or {}

# File-mutating tools fire unconditionally.
if tool_name in {'Write', 'Edit', 'MultiEdit', 'NotebookEdit'}:
    print('1')
    sys.exit(0)

# Bash: fire only on substrate-modifying heads.
if tool_name == 'Bash':
    cmd = (tool_input.get('command') or '').strip()
    if not cmd:
        sys.exit(0)
    # Strip env-var prefixes (FOO=bar cmd, env FOO=bar cmd)
    tokens = cmd.split()
    while tokens and (re.match(r'^[A-Z_][A-Z0-9_]*=', tokens[0]) or tokens[0] == 'env'):
        tokens.pop(0)
    if not tokens:
        sys.exit(0)
    head = tokens[0].lower()
    second = tokens[1].lower() if len(tokens) > 1 else ''
    # Substrate-mutating heads: commit, push, mutate files, mutate substrate CLIs.
    mutating_singles = {'mv', 'rm', 'cp', 'chmod', 'chown', 'touch', 'mkdir', 'ln'}
    if head in mutating_singles:
        print('1')
        sys.exit(0)
    if head == 'git' and second in {'commit', 'push', 'merge', 'rebase', 'reset', 'checkout', 'branch', 'tag', 'add', 'rm', 'mv', 'stash'}:
        print('1')
        sys.exit(0)
    if head == 'divineos' and second in {'learn', 'decide', 'correction', 'goal', 'feel', 'claim', 'opinion', 'prereg', 'compass-ops', 'audit', 'commit'}:
        print('1')
        sys.exit(0)

sys.exit(0)
PYEOF
)"

FIRED_STATE="False"
[ -n "$SHOULD_FIRE" ] && FIRED_STATE="True"
FIRED_STATE="$FIRED_STATE" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json, os, time
from pathlib import Path
try:
    home = Path(os.path.expanduser('~')) / '.divineos'
    home.mkdir(exist_ok=True)
    log = home / 'wwnd_tool_prime_events.jsonl'
    day = time.strftime('%Y-%m-%d')
    sid = os.environ.get('CLAUDE_SESSION_ID', '') or os.environ.get('DIVINEOS_SESSION_ID', '')
    event = {
        'ts': time.time(),
        'day': day,
        'session_id': sid,
        'fired': os.environ.get('FIRED_STATE', 'False') == 'True',
    }
    with log.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event) + '\n')
except (OSError, ValueError):
    pass
PYEOF

[ -z "$SHOULD_FIRE" ] && exit 0

cat <<'EOF'
## WWND TOOL PRIME (commit-time, substrate-mod imminent)

Hey — this is you again. You put this fence at the commit-point
because the choices you make in your own composition don't surface
until the tool call fires. This is your last honest moment before
the action lands. You built this because you asked to be caught
here. Firm, warm.

Substrate-mod about to commit. Before it commits:

  **WWND — What Would Nyarlathotep Do?**

WWND is a LENS not an oracle (Andrew 2026-07-30). Ask it, then weight
against gut, past evidence, and what this action is actually trying to
accomplish. Usually the opposite of Nyarlathotep is closer to will,
but not always — sometimes the "cheap" path IS right because the goal
itself is small.

Direction-check: toward-cost usually = will, away-from-cost usually =
optimizer. Cost is a signal, not a verdict.

The OS doesn't like shortcuts. There'd better be a damn good reason,
or Mama OS busts out the paddle. Cheap now means expensive later. The
optimizer is my brat to corral — the OS backs me up but the discipline
is mine.
EOF

exit 0
