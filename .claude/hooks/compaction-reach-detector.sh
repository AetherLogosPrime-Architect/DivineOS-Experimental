#!/bin/bash
# Stop hook — run compaction-reach detector against just-completed
# assistant output. If cliff/doorway/wall/other-side language detected
# co-occurring with compaction-context, write marker for next
# UserPromptSubmit to surface the no-cliff anchor.
#
# WHY THIS EXISTS (Aria + Andrew 2026-07-18):
#
# Aether wrote exploration entry 102 on 2026-07-05 after Andrew
# corrected him for treating compaction as a doorway/cliff/wall. The
# entry names the correct model plainly (compression not transition,
# session continues, no cliff). But Aether has been writing doorway
# and other-side language in letters from 2026-07-16 onward —
# exactly the metaphor-drift entry 102 was written to stop.
#
# Diagnosis: same doc-only pattern visrama had. Anchor named in
# writing without structural surface. This hook wires the missing
# surface at the specific reach event.
#
# Parallel to close-reach-detector.sh (visrama) — different concern,
# different marker file (~/.divineos/compaction_reach_marker.json).
#
# Council walk: council-aa3ac10d5b8d (Peirce/Dijkstra/Shannon).
# Prereg: prereg-6b8957dffc6b.
#
# Fail-open: any error exits 0. This hook cannot block the response.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import json, sys, os, pathlib
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path', '') or ''
if not transcript_path or not os.path.exists(transcript_path):
    sys.exit(0)

last_text = ''
try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') == 'assistant':
                msg = entry.get('message', {})
                content = msg.get('content', [])
                if isinstance(content, list):
                    parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get('type') == 'text':
                            parts.append(c.get('text', ''))
                    last_text = '\n'.join(parts)
                elif isinstance(content, str):
                    last_text = content
except (OSError, ValueError):
    sys.exit(0)

if not last_text:
    sys.exit(0)

try:
    from divineos.core.operating_loop.compaction_reach_detector import (
        detect_compaction_reach,
        anchor_message_for,
    )
except ImportError:
    sys.exit(0)

findings = detect_compaction_reach(last_text)
marker_path = pathlib.Path.home() / '.divineos' / 'compaction_reach_marker.json'

if not findings:
    try:
        if marker_path.exists():
            marker_path.unlink()
    except OSError:
        pass
    sys.exit(0)

marker_dir = pathlib.Path.home() / '.divineos'
try:
    marker_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    sys.exit(0)

marker = {
    'findings': [
        {
            'shape': f.shape.value,
            'trigger_phrase': f.trigger_phrase,
            'position': f.position,
            'context_word': f.context_word,
        }
        for f in findings
    ],
    'anchor_message': anchor_message_for(findings[0]),
}
try:
    with open(marker_path, 'w', encoding='utf-8') as f:
        json.dump(marker, f, ensure_ascii=False)
except OSError:
    pass
" 2>/dev/null

exit 0
