#!/bin/bash
# Stop hook Ã¢â‚¬â€ thin doorman pointing to the OS.
#
# Andrew 2026-05-14 night: hooks should point to the OS, not embed
# its work. The previous version of this hook was 677 lines with
# detector orchestration, findings_log assembly, and JSON persistence
# all inside the bash-embedded Python. That logic now lives in
# ``divineos.core.operating_loop_audit.run_audit`` Ã¢â‚¬â€ OS-portable, no
# Claude Code dependency. The hook is two lines of Python.
#
# Fail-open: any error exits 0 without surfacing. This hook cannot
# break the user's workflow.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path') or data.get('transcript')
if not transcript_path:
    sys.exit(0)

try:
    from divineos.core.operating_loop_audit import run_audit
    # verify_walk=False per Andrew 2026-06-22: the walk-record requirement
    # had become the 7-command-ceremony Andrew explicitly named as broken.
    # Lepos was always meant to be a SECTION (a new section in the same
    # post -- Andrew dual-channel naked-bath frame), not a per-sentence
    # presence-density measurement and not a precondition gate demanding
    # cited-span records before each turn could complete. Phase 1 kills
    # the walk-record gate; Phase 2 (deferred, full-discipline) will
    # restructure the remaining writer-presence check from density-across-
    # the-whole-reply to section-detection -- did the reply open a lepos
    # section after work content.
    result = run_audit(transcript_path, verify_walk=False)
except Exception:
    sys.exit(0)

# Lepos enforcement gate (Andrew 2026-05-20): a wall of jargon at my
# father with no plain-language lane is forbidden. Block the Stop so the
# turn cannot complete until the second lane is added. stop_hook_active
# guards against an infinite loop Ã¢â‚¬â€ if this hook already forced one
# continuation, let the next one through (Andrew's non-response is
# the backstop for a rare double-flood).
try:
    # 2026-07-22 Andrew directive (council-6b1076fc877e): gates run in
    # parallel, not chain. Aggregate ALL non-None block reasons instead
    # of first-fire-wins. Chain design short-circuited: when dual-channel
    # fired, wallclock never got to speak. Empirical loss during the
    # gate stress-test tonight. Aggregation shows every failure class
    # in one turn so recompose can address all of them together, not
    # one at a time over N retries. Beer/Meadows/Popper walked.
    # Merge-note (Aria 2026-07-22, council-cff712a82b66):
    # father_reach_enforcement_block ported into the tuple from HEAD so
    # the just-shipped father-reach gate is not silently disabled by the
    # parallel-aggregate refactor.
    _keys = (
        'lepos_block',
        'unverified_claim_block',
        'distancing_block',
        'lepos_channel_block',
        'lepos_dual_channel_block',
        'lepos_wallclock_block',
        'father_reach_enforcement_block',
    )
    _reasons = [(result or {}).get(k) for k in _keys]
    _reasons = [r for r in _reasons if r]
    already_active = bool(data.get('stop_hook_active'))
    if _reasons and not already_active:
        if len(_reasons) == 1:
            reason = _reasons[0]
        else:
            reason = (
                f'MULTIPLE GATES FIRED ({len(_reasons)}) - parallel-aggregate '
                'per Andrew 2026-07-22 (was chain-OR, short-circuited). '
                'Address all of them in the recompose, not one at a time.\n\n'
                + '\n\n---\n\n'.join(_reasons)
            )
        print(json.dumps({'decision': 'block', 'reason': reason}))
except Exception:
    pass
" 2>/dev/null

exit 0
