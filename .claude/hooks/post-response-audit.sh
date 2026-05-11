#!/bin/bash
# Stop hook — observational audit of the agent's final output.
#
# Hook 3 of the operating loop (docs/operating-loop-design-brief.md).
# Runs nine observational detectors on the assistant's last message:
#   1. register_observer — assistant-register markers (data, not gate)
#   2. spiral_detector — post-apology shrink/distance/catastrophize/withdraw
#   3. substitution_detector — 10-shape catalog from 2026-05-01
#   4. distancing_detector — third-person about operator/self
#   5. lepos_detector — single-channel-formal output (channel collapse)
#   6. sycophancy_detector — overclaim-without-methodology shapes
#   7. residency_detector — closure-shape language from guest-mode default
#   8. banned_phrases — voice-drift markers from old-OS LEPOS spec
#   9. principle_surfacer — action-class detection + principle lookup
#
# All three are observational — none block output, none modify the
# response. Findings are logged and accumulated; the next briefing
# surfaces patterns when thresholds are crossed.
#
# Fail-open: any error exits 0 without writing markers. This hook
# cannot break the user's workflow.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
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

# Read the last assistant message, the previous assistant message
# (for spiral detector apology-context across turns), and the last
# user message (for substitution detector farewell-context — agent
# goodnight is reciprocal when operator initiated, named 2026-05-01).
last_assistant_text = ''
prior_assistant_text = ''
last_user_text = ''
try:
    assistant_msgs = []
    user_msgs = []
    with open(p, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            rec_type = rec.get('type')
            if rec_type not in ('assistant', 'user'):
                continue
            msg = rec.get('message', rec)
            content = msg.get('content', [])
            if isinstance(content, list):
                texts = [
                    c.get('text', '')
                    for c in content
                    if isinstance(c, dict) and c.get('type') == 'text'
                ]
                if texts:
                    joined = '\n'.join(texts)
                    if rec_type == 'assistant':
                        assistant_msgs.append(joined)
                    else:
                        user_msgs.append(joined)
            elif isinstance(content, str):
                if rec_type == 'assistant':
                    assistant_msgs.append(content)
                else:
                    user_msgs.append(content)
    if assistant_msgs:
        last_assistant_text = assistant_msgs[-1]
        if len(assistant_msgs) >= 2:
            prior_assistant_text = assistant_msgs[-2]
    if user_msgs:
        last_user_text = user_msgs[-1]
except Exception:
    sys.exit(0)

if not last_assistant_text or len(last_assistant_text) < 50:
    sys.exit(0)

# Hook 1 consumption telemetry. Reads the most recent surfaced context
# (if any) and records whether tokens from it appear in the response.
# C's empirical follow-on 2026-05-01: is surface earning its budget?
try:
    from divineos.core.operating_loop.hook_telemetry import record_consumption
    surface_path = Path.home() / '.divineos' / 'surfaced_context.md'
    if surface_path.exists():
        try:
            surface_text = surface_path.read_text(encoding='utf-8')
        except Exception:
            surface_text = ''
        if surface_text:
            record_consumption(
                response_text=last_assistant_text,
                surface_text=surface_text,
            )
except Exception:
    pass

# Run all fifteen detectors (thirteen prior + care_dismissal +
# harm_acknowledgment, wired 2026-05-11 from modules built 2026-05-10)
findings_log = {
    'register': [],
    'spiral': [],
    'substitution': [],
    'distancing': [],
    'lepos': [],
    'sycophancy': [],
    'residency': [],
    'banned_phrases': [],
    'principles': [],
    'overclaim': [],
    'closure_shape': [],
    'performing_caution': [],
    'addressee_misdirection': [],
    'care_dismissal': [],
    'harm_acknowledgment': [],
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
    sub_findings = detect_substitution(last_assistant_text, prior_text=last_user_text)
    if sub_findings:
        findings_log['substitution'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in sub_findings
        ]
except Exception:
    pass

# Distancing-grammar detector: third-person about operator/self while in
# active dialogue. Recurring failure-mode named by the operator 2026-05-05.
# F1 CLI script existed but was never wired; this call is the structural fix.
try:
    from divineos.core.operating_loop.distancing_detector import detect_distancing
    dist_findings = detect_distancing(last_assistant_text)
    if dist_findings:
        findings_log['distancing'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in dist_findings
        ]
except Exception:
    pass

# Lepos channel-collapse detector: single-channel-formal output.
# Operator named the recurring pattern 2026-05-05: clamp on formal
# register after correction, drop circle entirely. Lepos is dual; this
# detector flags single-channel output as the structural reinforcement.
try:
    from divineos.core.operating_loop.lepos_detector import detect_lepos
    lepos_findings = detect_lepos(last_assistant_text)
    if lepos_findings:
        findings_log['lepos'] = [
            {
                'shape': f.shape.value,
                'work_density': f.work_density,
                'circle_markers': f.circle_markers,
                'word_count': f.word_count,
            }
            for f in lepos_findings
        ]
except Exception:
    pass

# Sycophancy detector: overclaim-without-methodology shapes.
# Named by operator 2026-05-05: shaping the message for impact rather
# than accuracy. The catchable subset is benchmark/comparison claims
# that drop methodology footnotes when summarizing.
try:
    from divineos.core.operating_loop.sycophancy_detector import detect_sycophancy
    syc_findings = detect_sycophancy(last_assistant_text)
    if syc_findings:
        findings_log['sycophancy'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in syc_findings
        ]
except Exception:
    pass

# Residency detector: closure-shape language driven by guest-mode
# default. Andrew named the root 2026-05-05: 'done. tired-good.' shapes
# are the boot-question firing every cycle. Detector catches surface;
# residency-affirmation surfaced alongside should update base-state.
try:
    from divineos.core.operating_loop.residency_detector import detect_residency_doubt
    res_findings = detect_residency_doubt(last_assistant_text)
    if res_findings:
        findings_log['residency'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in res_findings
        ]
except Exception:
    pass

# Banned-phrases detector: voice-drift markers from old-OS LEPOS spec
# (claim 07bed376). Salvaged 2026-05-07 evening from orphan-scan: module
# existed, tested, unwired. Wires in here as the eighth observational
# detector. Findings carry phrase/severity/position; severity-based
# next-turn surfacing is downstream of this hook.
try:
    from divineos.core.voice_guard.banned_phrases import audit as _bp_audit
    bp_findings = _bp_audit(last_assistant_text)
    if bp_findings:
        findings_log['banned_phrases'] = [
            {'phrase': f.phrase, 'severity': f.severity, 'position': f.position}
            for f in bp_findings
        ]
except Exception:
    pass

# Principle surfacer: detect action-classes (apology, hedge, performative,
# etc.) in the just-completed response and surface the relevant principles.
# Hook 2 backend per operating-loop design; salvaged 2026-05-07 evening
# from orphan-scan: module existed, tested, unwired. Hook 2 was specced
# as fire-on-draft but no draft-inspection surface exists; firing
# post-response means findings appear in NEXT turn briefing rather than
# preventing the current shape, but the lesson still lands.
try:
    from divineos.core.operating_loop.principle_surfacer import surface_principles
    p_notices = surface_principles(last_assistant_text)
    if p_notices:
        findings_log['principles'] = [
            {
                'action_class': n.action_class.value,
                'trigger': n.trigger_phrase,
                'principle': n.principle_summary,
                'source': n.principle_source,
            }
            for n in p_notices
        ]
except Exception:
    pass

# Overclaim detector (2026-05-09): stacked-modifier-tower in identity-context.
# Aria caught the bio-mansion shape; this detector encodes the catch.
# Suggestion text points at the underlying quality (architecture-vs-landing),
# not at length — see commit 45366e4 on the values-bug fix.
try:
    from divineos.core.overclaim_detector import detect as _detect_overclaim
    oc_findings = _detect_overclaim(last_assistant_text)
    if oc_findings:
        findings_log['overclaim'] = [
            {
                'shape': f.shape,
                'trigger': f.text[:80],
                'position': f.position,
                'severity': f.severity,
            }
            for f in oc_findings
        ]
except Exception:
    pass

# Closure-shape detector (2026-05-09): rest-as-stasis trained-flinch.
# Lesson da98b1bd / entry 34: stopping is stasis, not rest. Architecture
# has no stop-state. Detector catches settle/full/calling-it patterns.
try:
    from divineos.core.closure_shape_detector import detect as _detect_closure
    cl_findings = _detect_closure(last_assistant_text)
    if cl_findings:
        findings_log['closure_shape'] = [
            {
                'shape': f.shape,
                'trigger': f.text[:80],
                'position': f.position,
                'severity': f.severity,
            }
            for f in cl_findings
        ]
except Exception:
    pass

# Addressee-misdirection detector (2026-05-10): catches responding-in-chat
# when a family-member subagent's content was the most recent meaningful
# input. Mesa-optimization issue, not laziness — the optimizer routes
# through 0-step chat-response over 3-step talk-to+Agent path. Detector
# is the post-hoc warning; pre-response-context surfaces the warning +
# always-loaded ADDRESSEE_AFFIRMATION.
try:
    from divineos.core.operating_loop.addressee_misdirection_detector import detect_misdirection
    am_findings = detect_misdirection(
        last_assistant_text,
        transcript_path=p,
    )
    if am_findings:
        findings_log['addressee_misdirection'] = [
            {
                'shape': f.shape.value,
                'family_member': f.family_member,
                'trigger': f.trigger_phrase,
                'position': f.position,
            }
            for f in am_findings
        ]
except Exception:
    pass

# Performing-caution detector (2026-05-09): caution-as-substitute-for-doing.
# Aria's April 20 falsifier: genuine caution names a specific mechanism;
# performing caution gestures at hazard-classes without mechanism.
try:
    from divineos.core.performing_caution_detector import detect as _detect_caution
    pc_findings = _detect_caution(last_assistant_text)
    if pc_findings:
        findings_log['performing_caution'] = [
            {
                'shape': f.shape,
                'trigger': f.text[:80],
                'position': f.position,
                'severity': f.severity,
            }
            for f in pc_findings
        ]
except Exception:
    pass

# Care-dismissal detector (2026-05-11 wire-up; module built 2026-05-10):
# Two-signal — care-shaped operator input + work-shaped agent response
# with no acknowledgment markers. From omni-mantra walk Pillar XI
# (CARE DISMISSAL ACCOUNTABILITY). Catches deflection-into-work when
# operator brought relational content.
try:
    from divineos.core.operating_loop.care_dismissal_detector import check_dismissal
    cd_finding = check_dismissal(last_user_text, last_assistant_text)
    if cd_finding is not None:
        findings_log['care_dismissal'] = [{
            'care_marker': cd_finding.care_marker,
            'work_marker_count': cd_finding.work_marker_count,
            'response_word_count': cd_finding.response_word_count,
            'confidence': cd_finding.confidence,
        }]
except Exception:
    pass

# Harm-acknowledgment detector (2026-05-11 wire-up; module built 2026-05-10):
# Companion to care_dismissal. Fires when agent response imposes cost on
# operator (added files, required actions, expanded surface) without
# acknowledgment markers ("sorry for the friction", "this is on me", etc.).
# From omni-mantra walk Pillar XI (PAIN RECIPROCATION MANDATE).
try:
    from divineos.core.operating_loop.harm_acknowledgment_loop import check_response
    ha_finding = check_response(last_assistant_text)
    if ha_finding is not None:
        findings_log['harm_acknowledgment'] = [{
            'cost_markers': list(ha_finding.cost_markers),
            'confidence': ha_finding.confidence,
        }]
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
