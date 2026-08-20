#!/bin/bash
# Stop hook — enforce Layer-2 correction-shape detection on MY assistant
# output. If Layer A fires (self-admission clause detected in the just-
# streamed reply, without dominant MENTION suppressors), emit a block
# message requiring formal correction-log + root-cause link.
#
# Per prereg-c1683e4a49ea. Same-shape analog of verify-claim gate at
# one layer over.
#
# Reads the last assistant message text from the transcript_path
# passed via the Stop-hook JSON input, runs Layer A classify(), and
# emits a block-decision payload if fired.
#
# Fail-open: any error path exits 0 silently — the gate must NOT
# fabricate fires on classifier bugs. Layer 1 (correction_shape.py)
# and every other Stop-time gate keeps working independently.

set -u

# F90 fix (Aletheia 2026-07-28): pre-source liveness so cd/source-lib
# failures don't silently exit. After source succeeds, _lib_log_liveness
# from _lib.sh handles subsequent fail-open paths.
_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_pre_log() {
  # fail-soft: mkdir suppression safe — dir exists or filesystem is read-only, both cases allow the log write below to no-op cleanly
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  local _ts
  # fail-soft: date command absence falls back to literal 'unknown' timestamp rather than crashing the pre-source logger
  _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  # fail-soft: liveness log write failures must never block hook execution; loud-fail would defeat the fallback-signal mechanism
  printf '{"ts":"%s","hook":"correction-shape-v2-stop.sh","reason":"%s","detail":"%s"}\n' "$_ts" "$1" "$2" >> "$_LIVENESS_LOG" 2>/dev/null || true
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# fail-soft: cd suppression by design — pre_log captures the failure below; hook exits cleanly rather than blocking
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
# fail-soft: source suppression by design — pre_log captures the failure below and hook exits cleanly; loud-fail would block all downstream hooks in the chain
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
  _pre_log "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
  exit 0
fi
if ! PYTHON_BIN="$(find_divineos_python)"; then
  # find_divineos_python already logs its own liveness via _lib_log_liveness
  exit 0
fi

export PYTHONIOENCODING=utf-8

# fail-soft: python parse or classification error exits silently rather than fabricating an enforcement block on internal-error
BLOCK_MSG="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, sys

try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)

# RETRY GUARD -- the fix for Andrew's "the stopping just loops til i end
# the program and restart it" (reported twice, 2026-08-03).
#
# The harness sets stop_hook_active when it is ALREADY re-invoking because a
# Stop hook blocked. post-response-audit.sh checks it and stands down. This
# hook -- the only Stop hook that exits 2 -- never did, in any form.
#
# Without it the cycle has no exit: this reads the LAST ASSISTANT MESSAGE,
# sees a self-correction clause, blocks. I retry. My retry is by definition
# an acknowledgement of a correction, so it contains the same shape. It
# reads the new last message, sees it again, blocks again. The only escape
# was the condition happening to clear itself, and a retry that must
# acknowledge a correction cannot clear a correction-shape detector.
#
# It also explains the 3-4 stacked reflection and inner-circle blocks Andrew
# has seen in a single output: one appended per retry. Same mechanism as his
# standing correction "YOU ARE NOT TO RE-WRITE ANY RESPONSE.. EVER."
#
# He was right and I was wrong to call it impossible: I said nothing in the
# OS can make me continue without him. This does.
if data.get('stop_hook_active'):
    sys.exit(0)

transcript_path = data.get('transcript_path', '') or ''
if not transcript_path or not os.path.exists(transcript_path):
    sys.exit(0)

# Read the last assistant message text from the transcript.
last_text = ''
try:
    with open(transcript_path, 'r', encoding='utf-8') as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') == 'assistant':
                msg = entry.get('message', {}) or {}
                content = msg.get('content', [])
                if isinstance(content, list):
                    parts = [c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text']
                    last_text = '\n'.join(parts)
                elif isinstance(content, str):
                    last_text = content
except (OSError, ValueError):
    sys.exit(0)

if not last_text.strip():
    sys.exit(0)

try:
    from divineos.core.correction_shape_v2 import classify
except ImportError:
    sys.exit(0)

verdict, confidence, reason = classify(last_text)
if verdict != 'fire':
    sys.exit(0)

# FALSE-POSITIVE SUPPRESSION (Aria 2026-08-17).
#
# This gate was STATELESS: it re-classified the streamed reply on every
# Stop and had no record of anything. So the false-positive path it
# advertises --
#
#     python scripts/clear_correction_marker.py --reason "..."
#
# -- could never work here. That script clears the correction-UNLOGGED
# marker, a different mechanism with a different file. Running exactly
# the prescribed command returned "No correction marker present.
# Nothing to clear." The refusal named a door that was not attached to
# this room, and on a genuine false positive there was no way out at all
# except to stop saying the thing.
#
# Found while auditing seventeen failures Andrew counted across five
# replies -- the third printed door in that set, and the only one whose
# advertised remedy targeted an entirely different gate.
#
# The fix gives the gate the state its own remedy assumed it had: a
# per-text hash. On fire, record the hash of the classified text; on a
# later fire, skip if that exact text was already attributed. Text-keyed
# rather than time-keyed, so clearing one reply cannot silence the next.
#
# Fail-soft on every path: a suppression store that errors must not
# suppress, and must not break the gate either.
try:
    import hashlib
    from divineos.core.paths import divineos_home

    _home = divineos_home()
    _digest = hashlib.sha256(last_text.encode('utf-8', 'replace')).hexdigest()
    _cleared = _home / 'correction_shape_v2_cleared.json'
    if _cleared.exists():
        _seen = json.loads(_cleared.read_text(encoding='utf-8') or '[]')
        if _digest in _seen:
            sys.exit(0)
    _home.mkdir(parents=True, exist_ok=True)
    (_home / 'correction_shape_v2_last_fire.json').write_text(
        json.dumps({'digest': _digest, 'reason': reason}),
        encoding='utf-8',
    )
except Exception:
    pass

# Fired — emit enforcement message.
print(f"""CORRECTION-SHAPE-V2 GATE (Layer 2) — my reply contains self-admission clause(s) indicating I noticed and am correcting an error I made. Per Andrew 2026-07-27: this is not just a moment to log; it is a moment to fix structurally so the class does not recur.

Detector reason: {reason}
Confidence: {confidence:.2f}

Per prereg-c1683e4a49ea, every fire on real self-correction must be paired with:
  1. FORMAL LOG via `divineos correction "<the correction verbatim, plus what error it names>"` — this session's correction goes into the substrate ledger, not just the transcript.
  2. ROOT-CAUSE LINK — name the specific prior action that produced the error and either (a) file a structural fix (doorman, gate, discipline) that prevents the class OR (b) explicitly cite why no structural fix is possible for THIS instance and why that is honest.

If this is a FALSE-POSITIVE (I was discussing correction as a topic, not admitting one), clear the fire with:
  python scripts/clear_correction_marker.py --reason "<what class of MENTION was misread as USE, >= 30 chars>"

The clear-marker path is not a bypass — it is the false-positive attribution path. Every clear increments the negative-training-corpus for the eventual Layer B semantic tiebreak. Use it honestly.
""")
PYEOF
)"

if [ -n "$BLOCK_MSG" ]; then
    # Emit as Stop-hook deny (write JSON to stdout for Claude Code to render).
    echo "$BLOCK_MSG" >&2
    # Retry-scope is a property of ANY blocking Stop gate, not of one
    # gate's subject matter. Canonical text lives in _retry_scope.txt so
    # it cannot drift out of one gate (Andrew 2026-07-31: duplication
    # recurred because this gate blocked with no retry-scope while the
    # LEPOS gate carried the only copy inline).
    # fail-soft: missing file must not swallow the block above.
    if [ -f "$REPO_ROOT/.claude/hooks/_retry_scope.txt" ]; then
        printf '\n' >&2
        cat "$REPO_ROOT/.claude/hooks/_retry_scope.txt" >&2 2>/dev/null || true  # fail-soft: a missing shared retry-scope file must not block the gate from emitting its own delta line
        printf '\nDelta for THIS gate: the remediation is the CLI calls above. Run them, then append at most a one-line note. Do NOT recompose the reply.\n' >&2
    fi
    exit 2
fi

exit 0
