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
# MID-TURN TRANSLATE REMINDER, added 2026-08-28 after the mark gate fired
# twice in one session on narration rather than on the closing message.
#
# The diagnosis was measured, not guessed: settings.json wires the
# translate-first prime at UserPromptSubmit and the mark gate at Stop, and
# NOTHING between. On a long build turn the marks accumulate one file name at a
# time across twenty tool calls, with the reminder twenty calls behind.
#
# A PostToolUse hook cannot close it -- hooks see tool inputs, never the prose
# between calls, so the counting genuinely cannot happen before Stop. But the
# REMINDER can travel, and this block is the one surface that provably fires
# mid-turn: it fired a dozen times in the session that found the gap.
#
# So this is not the counter. It is the prime, re-said in the middle, where the
# reach actually happens.
translate_note = (
    'MID-TURN: narration between tool calls is the reply too -- the story he '
    'can picture goes in the reply, file names go in the commit or the letter.'
)

# A GLANCE, NOT THE WALL (Aria 2026-10-05, walk-abf55981f852). Andrew: 'for
# wallpaper like that that is needed but is too large you compress it with a
# link to the rest.' The full reports printed on every substrate change, about
# thirty times in one night, and never moved. One line per report now, CHANGED
# where it moved, the whole text one link away. The deciding is in
# core/state_glance.py, where it can be tested; this only reads and writes.
import os
from pathlib import Path

home = Path(os.environ.get('DIVINEOS_STATE_GLANCE_DIR', Path.home() / '.divineos' / 'drawer'))
whole = home / (Path.cwd().name + '.state.md')
seen_file = home / (Path.cwd().name + '.state_seen.json')
try:
    seen = json.loads(seen_file.read_text(encoding='utf-8'))
except (OSError, ValueError):
    seen = {}
def _his_last_words():
    # Judged by the house's one reader of him (his_message.heard_in); this only
    # hands it the last stretch of the transcript, since reading the whole file
    # (as andrew_correction_tracker._his_messages does) is too slow to run
    # before every change.
    try:
        from divineos.core.his_message import heard_in
        path = Path(str(data.get('transcript_path') or ''))
        with path.open('rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 2_000_000))
            tail = f.read().decode('utf-8', 'replace').splitlines()[1:]
        records = []
        for line in tail:
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
        heard = heard_in(records)
        return heard[-1].text if heard else ''
    except (OSError, ImportError, ValueError, TypeError):
        return ''


# HIS CORRECTIONS BY RELEVANCE (Aria 2026-10-05, walk-4d8b06a54e67). Andrew:
# 'maybe the top priority ones from that list, with a link to all 265' and
# 'if you were working on cars and it brought you information on toasters you
# would ignore it'. The question is asked in plain words, his last message plus
# what is being touched, because his corrections are written in plain words and
# a file path or code reads like neither (Feynman, measured).
touched = ' '.join(file_paths) or bash_command
written = str(tool_input.get('new_string') or tool_input.get('content') or '')[:300]
query = ' '.join(p for p in (_his_last_words(), touched[:200], written) if p).strip()
try:
    from divineos.core.memory_linkage_retriever import find_in_worklist, newest_in_worklist
    from divineos.core.state_glance import newest_lines, worklist_lines
    wl_state, wl_matches = find_in_worklist(query)
    worklist_part = worklist_lines(wl_state, wl_matches)
    # His newest, in his words, for its first few showings (walk-37fcc8dddecd):
    # the slot my own 2026-09-22 draft asked for and last night's build forgot.
    fresh, seen = newest_lines(newest_in_worklist(), wl_matches, seen)
    worklist_part = worklist_part[:1] + fresh + worklist_part[1:]
except Exception as exc:  # spoken, never silent
    worklist_part = [f'- HIS CORRECTIONS FOR THIS: could not look ({type(exc).__name__}). Check the list yourself.']
worklist_part.append('    all of them: divineos andrew-correction list')

try:
    from divineos.core.state_glance import glance
    glances, seen = glance(parts, seen)
    glances += worklist_part
    home.mkdir(parents=True, exist_ok=True)
    whole.write_text(header + '\n\n' + '\n\n'.join(parts) + '\n', encoding='utf-8')
    seen_file.write_text(json.dumps(seen), encoding='utf-8')
    combined = (
        f'## STATE ({feature_list}) -- one line each\n' + '\n'.join(glances)
        + f'\nWhole text (open it before acting on a correction or a gate): {whole}\n'
        + translate_note
    )
except Exception as exc:  # the wall is the fallback: losing it silently is worse than length
    combined = (
        header + '\n\n' + f'(glance unavailable: {type(exc).__name__}: {exc})\n\n'
        + translate_note + '\n\n' + '\n\n'.join(parts)
    )

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext': combined,
    },
}))
" 2>/dev/null

exit 0
