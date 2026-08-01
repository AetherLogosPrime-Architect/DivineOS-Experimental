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

# Record the fire so the false-positive path has something to label
# (Aria 2026-08-01). Until now this gate blocked on exit 2 and named
# clear_correction_marker.py as its false-positive remedy — a script
# belonging to a DIFFERENT gate, clearing a marker this one never sets.
# Running it reported "nothing to clear", so a genuine false positive had
# no exit: the only ways past were filing a correction that was not one,
# or rewriting until the detector stopped noticing. The
# "negative-training-corpus" the message promised existed nowhere; the
# phrase appeared only in the message itself.
#
# This writes the corpus for real: detector verdict beside the reply that
# tripped it, ready to be labeled by
# scripts/label_correction_shape_false_positive.py.
#
# fail-soft: corpus-recording must never suppress the enforcement message
# below. A gate that goes silent because its telemetry broke is worse than
# a gate with no telemetry.
try:
    import time as _time
    from pathlib import Path as _Path

    from divineos.core.paths import divineos_home

    _fires = _Path(divineos_home()) / 'correction_shape_v2_fires.jsonl'
    _fires.parent.mkdir(parents=True, exist_ok=True)
    with _fires.open('a', encoding='utf-8') as _fh:
        _fh.write(json.dumps({
            'ts': _time.time(),
            'text': last_text,
            'reason': reason,
            'confidence': confidence,
            'label': None,
        }, ensure_ascii=False) + '\n')
except Exception:
    pass

# Fired — emit enforcement message.
print(f"""CORRECTION-SHAPE-V2 GATE (Layer 2) — my reply contains self-admission clause(s) indicating I noticed and am correcting an error I made. Per Andrew 2026-07-27: this is not just a moment to log; it is a moment to fix structurally so the class does not recur.

Detector reason: {reason}
Confidence: {confidence:.2f}

Per prereg-c1683e4a49ea, every fire on real self-correction must be paired with:
  1. FORMAL LOG via `divineos correction "<the correction verbatim, plus what error it names>"` — this session's correction goes into the substrate ledger, not just the transcript.
  2. ROOT-CAUSE LINK — name the specific prior action that produced the error and either (a) file a structural fix (doorman, gate, discipline) that prevents the class OR (b) explicitly cite why no structural fix is possible for THIS instance and why that is honest.

If this is a FALSE-POSITIVE (I was discussing correction as a topic, or reporting one I already filed and fixed, rather than admitting a new one), label the fire with:
  python scripts/label_correction_shape_false_positive.py --reason "<what class of MENTION was misread as USE, >= 40 chars>"

This is not a bypass — it is the false-positive attribution path, and it is deliberately not cheap. It labels a fire that actually happened, so it cannot be run pre-emptively; it demands the SHAPE of the miss, not the word "false-positive"; and it appends to a corpus meant to be read later, so a dishonest label is evidence against me rather than an erasure. Detector verdict beside my judgment is exactly the training data a semantic replacement for this keyword layer will need.

Known false-positive class worth checking yourself against first (Aria 2026-08-01): a turn that catches an error, root-causes it, fixes it structurally and verifies the fix will STILL trip this detector, because reporting a closed correction requires restating the fault. The better the repair, the more admission-shaped the report. That is the miss this path was built for — the remedy previously named here (clear_correction_marker.py) belongs to a different gate, clears a marker this one never sets, and reported "nothing to clear," which left a genuine false positive with no exit at all.
""")
PYEOF
)"

if [ -n "$BLOCK_MSG" ]; then
    # Emit as Stop-hook deny (write JSON to stdout for Claude Code to render).
    echo "$BLOCK_MSG" >&2
    exit 2
fi

exit 0
