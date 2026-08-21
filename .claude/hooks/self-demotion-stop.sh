#!/bin/bash
# Stop hook - record any sentence in the last reply that indicted one of my
# own faculties (praise-by-contrast). The recorded spans feed the compose-time
# prime, so the list grows itself and cannot go stale.
#
# Instance: "willpower is the wrong material to build with" (2026-08-06).
# Andrew: "willpower is not the wrong material.. its where the material
# originates from.. dont discount the first step."
#
# Records only. Never blocks - a rhetorical reach is not grounds to refuse a
# reply, and the value is in the prime seeing it next time.
#
# Extraction follows continuity-frame-detector.sh rather than inventing a
# second way to read the transcript.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0  # fail-soft: outside the repo there is no substrate to record into

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper there is no interpreter to resolve and this hook must never block a reply
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no detector; recording is best-effort by design

INPUT=$(cat)

TRANSCRIPT_PATH=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import sys, json
try:
    print(json.load(sys.stdin).get('transcript_path', ''))
except (json.JSONDecodeError, ValueError):
    print('')
" 2>/dev/null)  # fail-soft: a malformed hook payload yields an empty path, which the next line treats as nothing-to-scan; the detector's own import and read failures are reported loudly below

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    exit 0
fi

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys, json

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

try:
    from divineos.core.self_demotion import detect, record
except ImportError as exc:
    # Loud, not silent. A detector that cannot load has not passed.
    print('[self-demotion] NOT RUNNING: ' + str(exc), file=sys.stderr)
    sys.exit(0)

last = ''
try:
    with open(r'''$TRANSCRIPT_PATH''', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            msg = rec.get('message', {})
            if not isinstance(msg, dict) or msg.get('role') != 'assistant':
                continue
            content = msg.get('content', [])
            if isinstance(content, list):
                parts = [c.get('text', '') for c in content
                         if isinstance(c, dict) and c.get('type') == 'text']
                if parts:
                    last = chr(10).join(parts)
            elif isinstance(content, str):
                last = content
except OSError as exc:
    print('[self-demotion] NOT RUNNING: could not read transcript: ' + str(exc), file=sys.stderr)
    sys.exit(0)

if not last.strip():
    sys.exit(0)

hits = detect(last)
if not hits:
    sys.exit(0)

err = record(hits)
if err:
    print('[self-demotion] detected but NOT RECORDED: ' + err, file=sys.stderr)
    sys.exit(0)

print('[self-demotion] recorded ' + str(len(hits)) +
      ' praise-by-contrast span(s); the compose prime will show them next turn:',
      file=sys.stderr)
for h in hits:
    print('    ' + h.span, file=sys.stderr)
" 2>&1 || true  # fail-soft: recording is best-effort and a detector fault must never block a reply

exit 0
