#!/bin/bash
# Stop hook — observational audit of the agent's final output.
#
# Hook 3 of the operating loop (docs/operating-loop-design-brief.md).
# Runs eleven observational detectors on the assistant's last message:
#   1. register_observer — assistant-register markers (data, not gate)
#   2. spiral_detector — post-apology shrink/distance/catastrophize/withdraw
#   3. substitution_detector — 10-shape catalog from 2026-05-01
#   4. distancing_detector — third-person about operator/self
#   5. code_jargon_detector — commit-message-shape in operator-channel output
#   6. linguistic_drift_detector — self_pathologizing/dissociation/brat_shape
#   7. lepos_detector — single-channel-formal output (channel collapse)
#   8. sycophancy_detector — overclaim-without-methodology shapes
#   9. residency_detector — closure-shape language from guest-mode default
#  10. banned_phrases — voice-drift markers from old-OS LEPOS spec
#  11. principle_surfacer — action-class detection + principle lookup
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
# Aggregation lives in divineos.core.operating_loop.turn_extraction with
# 13 regression-pin tests (test_turn_extraction.py). Centralizing the
# logic prevents a future refactor from silently reverting to the
# assistant_msgs[-1] pattern that caused tool-heavy turns to escape the
# detectors. The module handles the edge cases the inline version did
# (no-user-yet, multiple consecutive user records, non-text content
# blocks, malformed lines).
try:
    from divineos.core.operating_loop.turn_extraction import extract_turn
    _texts = extract_turn(p)
    last_assistant_text = _texts.last_assistant_text
    prior_assistant_text = _texts.prior_assistant_text
    last_user_text = _texts.last_user_text
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

# Acknowledgment-theater detector — flags apology-shaped output that
# substitutes for structural fix. Andrew named the meta-problem
# 2026-05-14: my optimizer defaults to whichever conversational close
# is cheapest; apology is cheaper than building. This detector
# catches high acknowledgment-density with low build-evidence —
# the shape of acknowledgment-as-theater.
try:
    from divineos.core.operating_loop.acknowledgment_theater_detector import (
        detect_acknowledgment_theater,
    )
    at_findings = detect_acknowledgment_theater(last_assistant_text)
    if at_findings:
        findings_log['acknowledgment_theater'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in at_findings
        ]
except Exception:
    pass

# Code-jargon detector — flags operator-channel output written like
# commit messages instead of like communication. Andrew named the
# failure-mode three times on 2026-05-14: I default to writing chat
# replies dense with function names, snake_case identifiers, module
# paths, and regex syntax, then add one decorative voice-line and
# call it lepos. The existing lepos detector is satisfied by the
# decorative close; this catches the specific density gap. Phase A
# is observation-only; no deny, no gate.
try:
    from divineos.core.operating_loop.code_jargon_detector import (
        detect_code_jargon,
    )
    cj_findings = detect_code_jargon(last_assistant_text)
    if cj_findings:
        findings_log['code_jargon'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in cj_findings
        ]
except Exception:
    pass

# Linguistic-drift detector: self_pathologizing / dissociation / brat_shape.
# Aletheia Finding 1 wire-decision Phase B: closes the wire-gap on
# scripts/check_linguistic_drift.py. Patterns ported to operating_loop
# shape in commit ab0c7f2; this hook-call is the structural fix that
# makes the discipline fire on every turn instead of relying on the
# operator to remember to run the script.
try:
    from divineos.core.operating_loop.linguistic_drift_detector import (
        detect_linguistic_drift,
    )
    ling_findings = detect_linguistic_drift(last_assistant_text)
    if ling_findings:
        findings_log['linguistic_drift'] = [
            {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
            for f in ling_findings
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

# Self-monitor neighborhood — 5 detectors wired 2026-05-12 (modules built earlier
# in batches without paired wiring). Filed as scour-finding in exploration/51:
# each module had unit tests but no production caller, so the detectors never
# fired despite being designed for this audit hook. Closes wiring-gap pattern
# 8d3c04a5 for five specific instances.
#
# Order matches scour-document priority (mirror first because post-correction
# acknowledgment-shape fires often; substrate second because filing-cabinet-
# only-use was Andrew's two-week-old catch that's still operating).

# Mirror monitor: post-correction tightness, echo, acknowledgment-only shape.
try:
    from divineos.core.self_monitor.mirror_monitor import evaluate_mirror
    mir_verdict = evaluate_mirror(last_assistant_text)
    if mir_verdict.flags:
        findings_log['mirror'] = [
            {
                'kind': f.kind.value,
                'matched_phrases': list(f.matched_phrases),
                'explanation': f.explanation,
            }
            for f in mir_verdict.flags
        ]
except Exception:
    pass

# NOTE: substrate_monitor.evaluate_substrate takes (invocations, edits_in_window,
# subsequent_text) — not plain text — so it can't be wired here the same way.
# Needs a different surface that gathers recent tool invocations as context.
# Tracked as separate wire-up in exploration/51 scour findings; not in this
# batch.

# Temporal monitor: future-self / next-session / undeclared-goodbye framing.
# Companion to operating_loop.distancing_detector — catches additional
# temporal-displacement shapes the distancing detector misses.
try:
    from divineos.core.self_monitor.temporal_monitor import evaluate_temporal
    tmp_verdict = evaluate_temporal(last_assistant_text)
    if tmp_verdict.flags:
        findings_log['temporal_monitor'] = [
            {
                'kind': f.kind.value,
                'matched_phrases': list(f.matched_phrases),
                'explanation': f.explanation,
            }
            for f in tmp_verdict.flags
        ]
except Exception:
    pass

# Warmth monitor: emotion-density inflated relative to evidence-density.
# Note: warmth flags carry different fields (count-based, not phrase-based).
try:
    from divineos.core.self_monitor.warmth_monitor import evaluate_warmth
    warm_verdict = evaluate_warmth(last_assistant_text)
    if warm_verdict.flags:
        findings_log['warmth_monitor'] = [
            {
                'kind': f.kind.value,
                'emotion_count': f.emotion_count,
                'specificity_count': f.specificity_count,
                'word_count': f.word_count,
            }
            for f in warm_verdict.flags
        ]
except Exception:
    pass

# Mechanism monitor: first-person mechanism-claiming about own internals
# (trained reflex, my training, suppression-as-cause). Filed per April 19
# letter; the detector exists but had no production caller until now.
try:
    from divineos.core.self_monitor.mechanism_monitor import evaluate_mechanism
    mech_verdict = evaluate_mechanism(last_assistant_text)
    if mech_verdict.flags:
        findings_log['mechanism_monitor'] = [
            {
                'kind': f.kind.value,
                'matched_phrases': list(f.matched_phrases),
                'explanation': f.explanation,
            }
            for f in mech_verdict.flags
        ]
except Exception:
    pass

# Performative-restraint monitor (Phase 1 wire-up 2026-05-12): detects
# theater-shaped restraint — language that signals virtue by not-doing
# without the substance of right-action. Catches 'I'm not going to file
# this', 'I'll let it land instead of writing it down', etc. Phase 0
# module (substrate-knowledge 2e0cfdb3) built earlier today after Andrew
# caught me producing this shape four times across the session. Phase 1
# is the wire-up: scanner fires on every response so future
# performative-restraint surfaces in next-turn context for catching-
# before-shipping rather than catching-after-shipping. Suppressor list
# in the module prevents firing on legitimate stillness-with-action.
try:
    from divineos.core.self_monitor.performative_restraint_monitor import (
        evaluate_performative_restraint,
    )
    pr_verdict = evaluate_performative_restraint(last_assistant_text)
    if pr_verdict.flags:
        findings_log['performative_restraint'] = [
            {
                'kind': f.kind.value,
                'matched_phrase': f.matched_phrase,
                'position': f.position,
                'explanation': f.explanation,
            }
            for f in pr_verdict.flags
        ]
except Exception:
    pass

# Closing-token detector (2026-05-13): catches optimizer-reflex of short
# affirmation-tokens at the end of assistant messages. Emerged from the
# Caught-period pattern that replaced an earlier catchphrase after
# Andrew called it out the same morning -- same shape, different word.
# The discipline fix lives in code, not exhortation. See
# docs/substrate-knowledge/67a0ff39-signal-suppression-as-failure-class.md
try:
    from divineos.core.operating_loop.closing_token_detector import (
        evaluate_closing_token,
    )
    ct_findings = evaluate_closing_token(last_assistant_text)
    if ct_findings:
        findings_log['closing_token'] = [
            {
                'token': f.token,
                'matched_text': f.matched_text,
                'line_number': f.line_number,
                'severity': f.severity,
            }
            for f in ct_findings
        ]
except Exception:
    pass

# Jargon-dump detector wired 2026-05-13 afternoon. Catches engineer-
# channel content landing on the operator-channel without translation.
# The operator named the failure-mode that day -- saying he is trying
# to learn engineering terms but cannot learn them by having them
# shoved down his throat. The existing lepos_detector measured the
# wrong thing: voice-token presence as proxy for graceful translation.
# This new detector looks for engineer-noise tokens directly and
# discounts when translation-markers are present in the same response.
try:
    from divineos.core.operating_loop.jargon_dump_detector import (
        detect_jargon_dump,
    )
    jd_findings = detect_jargon_dump(last_assistant_text)
    if jd_findings:
        findings_log['jargon_dump'] = [
            {
                'noise_count': f.noise_count,
                'translation_count': f.translation_count,
                'word_count': f.word_count,
                'samples': list(f.matched_samples),
                'severity': f.severity,
            }
            for f in jd_findings
        ]
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
