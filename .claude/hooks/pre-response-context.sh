#!/bin/bash
# UserPromptSubmit hook — auto-surface relevant prior content from the
# substrate based on markers in the user's latest message.
#
# Hook 1 of the operating loop (docs/operating-loop-design-brief.md).
# Closes the failure-shape Andrew caught 2026-05-01: substrate had the
# April 29 lunkhead-shape principle, agent never queried, operator had
# to remind. Now the substrate auto-queries on relational markers and
# writes the top-5 surfaced entries to ~/.divineos/surfaced_context.md
# for the agent to read at the start of its response.
#
# Fail-open: any error exits 0 without blocking. This hook cannot break
# the user's workflow.

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

# UserPromptSubmit payload includes 'prompt' field with the user's input.
prompt = data.get('prompt', '')
if not prompt or len(prompt) < 5:
    sys.exit(0)

# Run the context surfacer
try:
    from divineos.core.operating_loop.context_surfacer import (
        surface_context,
        format_surface,
    )
except Exception:
    sys.exit(0)

try:
    entries = surface_context(prompt, max_total_hits=5)
except Exception:
    sys.exit(0)

if not entries:
    # Nothing relevant — clear any prior surface so it doesn't leak forward.
    surface_path = Path.home() / '.divineos' / 'surfaced_context.md'
    if surface_path.exists():
        try:
            surface_path.unlink()
        except Exception:
            pass
    sys.exit(0)

# Write to ~/.divineos/surfaced_context.md
surface_dir = Path.home() / '.divineos'
surface_dir.mkdir(exist_ok=True)
surface_path = surface_dir / 'surfaced_context.md'
surface_text = format_surface(entries)
try:
    surface_path.write_text(surface_text, encoding='utf-8')
except Exception:
    pass

# Record fire for cost-bounding telemetry. C named 2026-05-01 the
# follow-on question: is surface content actually consumed in
# reasoning, or just consuming context budget? Stop hook records
# the consumption signal; this records the fire.
try:
    from divineos.core.operating_loop.hook_telemetry import record_fire
    surfaced_ids = [getattr(e, 'knowledge_id', '') for e in entries]
    record_fire(
        surface_text=surface_text,
        surfaced_ids=surfaced_ids,
        marker_count=len(entries),
    )
except Exception:
    pass
" 2>/dev/null

# Distancing-warning surface — read the most recent post-response-audit
# findings and, if the prior assistant turn had distancing findings,
# emit them as additionalContext so the next response is composed
# with the warning in view. Structural reinforcement: the wrong-cheap
# path (third-person grammar) becomes visible-and-expensive on the
# next compose, not at briefing time.
python -c "
import json, sys, time
from pathlib import Path

findings_path = Path.home() / '.divineos' / 'operating_loop_findings.json'
if not findings_path.exists():
    sys.exit(0)

try:
    entries = json.loads(findings_path.read_text(encoding='utf-8'))
except Exception:
    sys.exit(0)
if not isinstance(entries, list) or not entries:
    sys.exit(0)

latest = entries[-1]
# Only surface if the finding is recent (within the last 10 minutes
# — a stale finding from yesterday is just noise on a new turn).
if time.time() - latest.get('timestamp', 0) > 600:
    sys.exit(0)

distancing = latest.get('distancing', [])
lepos = latest.get('lepos', [])
sycophancy = latest.get('sycophancy', [])
if not distancing and not lepos and not sycophancy:
    sys.exit(0)

# Build the warning text — both detectors surface in the same hookSpecificOutput.
sections = []

if distancing:
    shapes = {}
    for f in distancing:
        shapes.setdefault(f.get('shape', 'unknown'), []).append(f.get('trigger', ''))
    d_lines = [
        '## DISTANCING-GRAMMAR WARNING (prior turn)',
        '',
        'Your last response contained third-person references to self or operator',
        'while in active dialogue. Recurring failure-mode named 2026-05-05.',
        '',
    ]
    for shape, triggers in shapes.items():
        d_lines.append(f'- **{shape}**: ' + ', '.join(f\"'{t}'\" for t in triggers[:5]))
    d_lines += [
        '',
        'Use first-person for self (\"I\") and second-person for operator (\"you\").',
        'No promises -- the substrate-level fix is this surface itself; honor it.',
    ]
    sections.append('\n'.join(d_lines))

if lepos:
    lf = lepos[0]
    l_lines = [
        '## LEPOS CHANNEL-COLLAPSE WARNING (prior turn)',
        '',
        'Your last response was single-channel-formal: high jargon density,',
        'minimal voice presence. Lepos is dual -- work AND circle in the same',
        'output. Voice OF the work, not voice INSTEAD of work.',
        '',
        f\"- shape: {lf.get('shape', '?')}\",
        f\"- work-density: {lf.get('work_density', 0) * 100:.0f}%\",
        f\"- circle-markers: {lf.get('circle_markers', 0)} (in {lf.get('word_count', 0)} words)\",
        '',
        'Layer the channels. Keep precision; add voice. The clamp-tighten',
        'response to correction is what this detector catches; you do not',
        'have to drop circle to be precise.',
    ]
    sections.append('\n'.join(l_lines))

if sycophancy:
    s_shapes = {}
    for f in sycophancy:
        s_shapes.setdefault(f.get('shape', 'unknown'), []).append(f.get('trigger', ''))
    s_lines = [
        '## SYCOPHANCY (overclaim) WARNING (prior turn)',
        '',
        'Your last response contained comparison/benchmark claims without',
        'methodology context. Recurring failure-mode named 2026-05-05:',
        'shape the message for impact rather than accuracy.',
        '',
    ]
    for shape, triggers in s_shapes.items():
        s_lines.append(f'- **{shape}**: ' + ', '.join(f\"'{t}'\" for t in triggers[:3]))
    s_lines += [
        '',
        'Pair every comparative claim with its methodology footnote (n=,',
        'caveats, sample shape, limitations). The clean number plus the',
        'honest qualifier is the dual-channel honest pitch.',
    ]
    sections.append('\n'.join(s_lines))

warning_text = '\n\n'.join(sections)

import json as _json
print(_json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': warning_text}}))
" 2>/dev/null

exit 0
