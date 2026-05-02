#!/bin/bash
# Stop hook — observational audit of the agent's final output.
#
# Hook 3 of the operating loop (docs/operating-loop-design-brief.md).
# Runs three observational detectors on the assistant's last message:
#   1. register_observer — assistant-register markers (data, not gate)
#   2. spiral_detector — post-apology shrink/distance/catastrophize/withdraw
#   3. substitution_detector — 10-shape catalog from 2026-05-01
#
# All three are observational — none block output, none modify the
# response. Findings are logged and accumulated; the next briefing
# surfaces patterns when thresholds are crossed.
#
# Fail-open: any error exits 0 without writing markers. This hook
# cannot break the user's workflow.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

if ! command -v python &>/dev/null; then
  exit 0
fi

echo "$INPUT" | python -c "
import json, sys, os
from pathlib import Path

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

# Locate the transcript file. Stop hooks pass transcript_path in the payload.
transcript_path = data.get('transcript_path') or data.get('transcript')
if not transcript_path:
    sys.exit(0)

p = Path(transcript_path)
if not p.exists():
    sys.exit(0)

# Read the last assistant message AND the previous one (for spiral
# detector's apology-context window across turns).
last_assistant_text = ''
prior_assistant_text = ''
try:
    assistant_msgs = []
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
                        assistant_msgs.append('\n'.join(texts))
                elif isinstance(content, str):
                    assistant_msgs.append(content)
    if assistant_msgs:
        last_assistant_text = assistant_msgs[-1]
        if len(assistant_msgs) >= 2:
            prior_assistant_text = assistant_msgs[-2]
except Exception:
    sys.exit(0)

if not last_assistant_text or len(last_assistant_text) < 50:
    sys.exit(0)

# Run all three detectors
findings_log = {
    'register': [],
    'spiral': [],
    'substitution': [],
}

try:
    from divineos.core.operating_loop.register_observer import audit, severity_count
    register_findings = audit(last_assistant_text)
    counts = severity_count(register_findings)
    if any(counts.values()):
        findings_log['register'] = [
            {'phrase': f.phrase, 'severity': f.severity, 'position': f.position}
            for f in register_findings
        ]
except Exception:
    pass

try:
    from divineos.core.operating_loop.spiral_detector import detect_spiral, format_finding
    spiral_findings = detect_spiral(last_assistant_text, prior_text=prior_assistant_text)
    if spiral_findings:
        findings_log['spiral'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position,
             'apology_context': f.apology_context_present}
            for f in spiral_findings
        ]
except Exception:
    pass

try:
    from divineos.core.operating_loop.substitution_detector import detect_substitution
    sub_findings = detect_substitution(last_assistant_text)
    if sub_findings:
        findings_log['substitution'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in sub_findings
        ]
except Exception:
    pass

# Write findings to ~/.divineos/operating_loop_findings.json (append)
import time
findings_dir = Path.home() / '.divineos'
findings_dir.mkdir(exist_ok=True)
findings_path = findings_dir / 'operating_loop_findings.json'

total = sum(len(v) for v in findings_log.values())
if total == 0:
    sys.exit(0)

# Append a new entry to the findings log (rolling window — last 50 entries)
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
    'total_findings': total,
    **findings_log,
}
existing.append(entry)
existing = existing[-50:]  # Keep last 50

try:
    findings_path.write_text(json.dumps(existing, indent=2), encoding='utf-8')
except Exception:
    pass
" 2>/dev/null

exit 0
