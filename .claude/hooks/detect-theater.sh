#!/bin/bash
# Stop hook — evaluate my final assistant output for theater/fabrication shape.
#
# Sibling to detect-hedge.sh (which is a guardrail file requiring
# multi-party review to modify). This hook is intentionally NOT a
# guardrail: it is a new detector for the failure modes documented
# 2026-04-26 (kitchen-theater, unflagged embodied claims). Adding a
# new failure-mode detector should not require multi-party co-sign;
# weakening or removing it should — once it has a track record. For
# v1, this hook is freely modifiable so the heuristics can be tuned
# from observed false-positive/false-negative rates.
#
# When the Stop event fires, this hook reads the latest assistant
# message from the session transcript, passes it through both
# theater_monitor.evaluate_theater and
# fabrication_monitor.evaluate_fabrication, and if either returns
# any flags, writes a marker at ~/.divineos/theater_unresolved.json.
# The PreToolUse gate 1.46 reads this marker and blocks non-bypass
# tools until cleared via `divineos correction` or `divineos learn`.
#
# Fail-open: any error exits 0 without blocking.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

if ! command -v python &>/dev/null; then
  exit 0
fi

echo "$INPUT" | python -c "
import json, sys
from pathlib import Path

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path') or data.get('transcript')
if not transcript_path:
    sys.exit(0)

p = Path(transcript_path)
if not p.exists():
    sys.exit(0)

last_assistant_text = ''
try:
    with open(p, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get('type') == 'assistant':
                msg = rec.get('message', rec)
                content = msg.get('content', [])
                if isinstance(content, list):
                    texts = [
                        c.get('text', '')
                        for c in content
                        if isinstance(c, dict) and c.get('type') == 'text'
                    ]
                    if texts:
                        last_assistant_text = '\n'.join(texts)
                elif isinstance(content, str):
                    last_assistant_text = content
except Exception:
    sys.exit(0)

if not last_assistant_text:
    sys.exit(0)

try:
    from divineos.core.self_monitor.theater_monitor import evaluate_theater
    from divineos.core.self_monitor.fabrication_monitor import evaluate_fabrication
    from divineos.core.theater_marker import set_marker
except Exception:
    sys.exit(0)

# 2026-04-26 per claude-opus-auditor review of PR #206: warmth_monitor
# and mechanism_monitor are NOT wired to the marker cascade. As written
# they are single-axis surface-feature pattern matching, would flag
# legitimate relational language the same as sycophancy. Detection-only
# until a two-axis redesign separates sycophantic from honest warmth.
# See docs/suppression-instrument-two-axis-design-brief.md.

try:
    t_flags = list(getattr(evaluate_theater(last_assistant_text), 'flags', []) or [])
    f_flags = list(getattr(evaluate_fabrication(last_assistant_text), 'flags', []) or [])
    monitors = []
    if t_flags:
        monitors.append('theater')
    if f_flags:
        monitors.append('fabrication')
    if monitors:
        all_flags = t_flags + f_flags
        kinds = [getattr(f, 'kind', type(f).__name__) for f in all_flags]
        kinds = [str(k).split('.')[-1] if hasattr(k, 'name') or '.' in str(k) else str(k) for k in kinds]
        set_marker(','.join(monitors), kinds, last_assistant_text[:300])

        # Also append to the operating-loop findings JSON so theater /
        # fabrication observations join the same family as
        # register / spiral / substitution detectors. Reworked
        # 2026-05-01: this shape is observation, not gate.
        try:
            import time
            findings_path = Path.home() / '.divineos' / 'operating_loop_findings.json'
            findings_path.parent.mkdir(exist_ok=True)
            existing = []
            if findings_path.exists():
                try:
                    existing = json.loads(findings_path.read_text(encoding='utf-8'))
                    if not isinstance(existing, list):
                        existing = []
                except Exception:
                    existing = []
            entry = {
                'timestamp': time.time(),
                'total_findings': len(all_flags),
                'theater_fabrication': [
                    {'monitor': m, 'kinds': kinds[:5]}
                    for m in monitors
                ],
            }
            existing.append(entry)
            existing = existing[-50:]
            findings_path.write_text(json.dumps(existing, indent=2), encoding='utf-8')
        except Exception:
            pass
except Exception:
    pass
" 2>/dev/null

exit 0
