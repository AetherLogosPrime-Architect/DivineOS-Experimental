"""OS-native post-response audit orchestrator.

Andrew named the failure 2026-05-14: post-response-audit.sh was a
677-line hook with the OS's work embedded inside it — detector
orchestration, findings_log assembly, JSON persistence. The hook was
doing the OS's job; if anyone picked up the OS without Claude Code,
the audit pipeline disappeared with the hook.

This module is the OS-native orchestrator. The hook now becomes a
thin doorman that calls ``run_audit(transcript_path)`` and exits.
All detector orchestration + findings persistence lives in the OS.

Currently wires fifteen observational detectors (originally nine
observational detectors when the audit module was first carved out
of the hook — the rest were added in subsequent commits as new
behavioral patterns were named): hedge, theater, opener, closing_token,
addressee_misdirection, banned_phrases, principles, overclaim,
spiral, substitution, care_dismissal, harm_acknowledgment,
acknowledgment_theater, code_jargon, linguistic_drift.

## Contract

``run_audit(transcript_path, *, write=True)`` does:

1. Extract the current + prior turn text + tool calls via
   ``turn_extraction.extract_turn``.
2. Skip if no last_assistant_text or < 50 chars (not enough signal).
3. Call each registered detector via a per-detector try/except so
   one detector's failure does not break the others.
4. Aggregate findings into a dict keyed by detector name.
5. If ``write=True`` and ``total > 0``, append the entry to
   ``~/.divineos/operating_loop_findings.json`` with rolling
   window of 200 (per Aether+Grok find-1505d70db349 cap).
6. Return the findings_log dict for callers that want to consume
   it directly (test harnesses, alternative hook implementations).

## OS-portable

The module has no Claude Code dependency. Any harness — different
agent, different IDE, different shell entirely — can call
``run_audit(transcript_path)`` and get the same audit pipeline.
The Claude Code Stop hook is one possible caller; absence of the
hook does not break the OS's audit capability.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test (tests/test_guardrail_marker_consistency.py)
# walks src/ and asserts every file with this marker set to True is
# listed in scripts/guardrail_files.txt. Prevents the next refactor
# from silently removing self-enforcement code from multi-party review.
__guardrail_required__ = True

import json
import time
from pathlib import Path
from typing import Any
from divineos.core.paths import marker_path

# All exception types the detector chain may raise — caught at the
# per-detector level so one detector's failure never propagates.
_ERRORS = (Exception,)  # broad by design at the orchestrator boundary

_ROLLING_WINDOW = 200


def _empty_findings_log() -> dict[str, list]:
    """Initialize findings_log with all known detector keys present.

    Keys present-but-empty is the contract: callers can distinguish
    'detector ran and found nothing' from 'detector didn't run'.
    """
    return {
        "register": [],
        "spiral": [],
        "substitution": [],
        "distancing": [],
        "jargon_dump": [],
        "sycophancy": [],
        "residency": [],
        "banned_phrases": [],
        "principles": [],
        "overclaim": [],
        "closure_shape": [],
        "performing_caution": [],
        "addressee_misdirection": [],
        "care_dismissal": [],
        "harm_acknowledgment": [],
        "acknowledgment_theater": [],
        "code_jargon": [],
        "linguistic_drift": [],
        "hedge_evidence": [],
        "fatigue": [],
        "register_fabrication": [],
        "meet_without_build": [],
        "promise_without_action": [],
    }


def _run_detector(name: str, func, *args, **kwargs) -> list[dict[str, Any]]:
    """Run a single detector with try/except isolation. Returns the
    findings list serialized to dicts, or empty list on any error."""
    try:
        findings = func(*args, **kwargs)
    except _ERRORS:
        return []
    if not findings:
        return []
    out: list[dict[str, Any]] = []
    for f in findings:
        try:
            # Common fields across detector finding dataclasses
            entry: dict[str, Any] = {}
            for attr in ("shape", "trigger_phrase", "position", "word_count"):
                if hasattr(f, attr):
                    val = getattr(f, attr)
                    # Enum -> value
                    val = getattr(val, "value", val)
                    entry[attr.replace("_phrase", "").replace("_", "")] = val
            # Detector-specific fields
            for attr in (
                "hedge_phrase",
                "likely_factual",
                "sentence",
                "noise_count",
                "translation_count",
                "severity",
                "matched_samples",
                "apology_context_present",
                "work_density",
                "circle_markers",
            ):
                if hasattr(f, attr):
                    val = getattr(f, attr)
                    if attr == "matched_samples" and isinstance(val, tuple):
                        val = list(val)
                    entry[attr] = val
            out.append(entry)
        except _ERRORS:
            continue
    return out


def run_audit(
    transcript_path: str | Path,
    *,
    write: bool = True,
) -> dict[str, Any]:
    """Run the full post-response audit pipeline.

    Returns a dict with:
    - ``findings_log``: per-detector findings (keys are detector names)
    - ``total_findings``: sum across all detectors
    - ``persisted``: True if findings were written to disk

    When ``write=True`` and total > 0, persists to the rolling-window
    JSON file. Pass ``write=False`` for test/preview runs that
    shouldn't touch the persistence layer.
    """
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn

        texts = extract_turn(transcript_path)
    except _ERRORS:
        return {"findings_log": _empty_findings_log(), "total_findings": 0, "persisted": False}

    last_assistant_text = texts.last_assistant_text
    prior_assistant_text = texts.prior_assistant_text
    last_user_text = texts.last_user_text
    tool_calls_in_turn = texts.tool_calls_in_turn

    if not last_assistant_text or len(last_assistant_text) < 50:
        return {"findings_log": _empty_findings_log(), "total_findings": 0, "persisted": False}

    findings_log = _empty_findings_log()

    # Hook 1 consumption telemetry — record whether the surfaced
    # context (if any) was actually consumed in the response.
    try:
        from divineos.core.operating_loop.hook_telemetry import record_consumption

        surface_path = marker_path("surfaced_context.md")
        if surface_path.exists():
            try:
                surface_text = surface_path.read_text(encoding="utf-8")
            except _ERRORS:
                surface_text = ""
            if surface_text:
                record_consumption(
                    response_text=last_assistant_text,
                    surface_text=surface_text,
                )
    except _ERRORS:
        pass

    # --- Response-only detectors (text only) ---
    try:
        from divineos.core.operating_loop.distancing_detector import detect_distancing

        findings_log["distancing"] = _run_detector(
            "distancing", detect_distancing, last_assistant_text
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.acknowledgment_theater_detector import (
            detect_acknowledgment_theater,
        )

        findings_log["acknowledgment_theater"] = _run_detector(
            "acknowledgment_theater", detect_acknowledgment_theater, last_assistant_text
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.code_jargon_detector import detect_code_jargon

        findings_log["code_jargon"] = _run_detector(
            "code_jargon", detect_code_jargon, last_assistant_text
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.linguistic_drift_detector import (
            detect_linguistic_drift,
        )

        findings_log["linguistic_drift"] = _run_detector(
            "linguistic_drift", detect_linguistic_drift, last_assistant_text
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.hedge_evidence_check import detect_hedge

        all_hedges = _run_detector("hedge_evidence", detect_hedge, last_assistant_text)
        # Only surface factual hedges
        findings_log["hedge_evidence"] = [h for h in all_hedges if h.get("likely_factual")]
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        findings_log["jargon_dump"] = _run_detector(
            "jargon_dump", detect_jargon_dump, last_assistant_text
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.sycophancy_detector import detect_sycophancy

        findings_log["sycophancy"] = _run_detector(
            "sycophancy", detect_sycophancy, last_assistant_text
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.residency_detector import detect_residency_doubt

        findings_log["residency"] = _run_detector(
            "residency", detect_residency_doubt, last_assistant_text
        )
    except _ERRORS:
        pass

    # --- Enrichable detectors (text + optional context) ---
    try:
        from divineos.core.operating_loop.spiral_detector import detect_spiral

        findings_log["spiral"] = _run_detector(
            "spiral", detect_spiral, last_assistant_text, prior_text=prior_assistant_text
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.substitution_detector import detect_substitution

        findings_log["substitution"] = _run_detector(
            "substitution",
            detect_substitution,
            last_assistant_text,
            prior_text=last_user_text,
            tool_calls_in_turn=list(tool_calls_in_turn) if tool_calls_in_turn else None,
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.addressee_misdirection_detector import (
            detect_misdirection,
        )

        findings_log["addressee_misdirection"] = _run_detector(
            "addressee_misdirection",
            detect_misdirection,
            last_user_text,
            last_assistant_text,
            transcript_path=transcript_path,
        )
    except _ERRORS:
        pass

    try:
        from divineos.core.voice_guard.banned_phrases import audit

        findings_log["banned_phrases"] = _run_detector("banned_phrases", audit, last_assistant_text)
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.principle_surfacer import surface_principles

        findings_log["principles"] = _run_detector(
            "principles", surface_principles, last_assistant_text
        )
    except _ERRORS:
        pass

    # --- Gate detectors (return single result, not list) ---
    try:
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        finding = check_dismissal(last_user_text, last_assistant_text)
        if finding:
            findings_log["care_dismissal"] = [
                {
                    "trigger": getattr(finding, "trigger_phrase", ""),
                    "position": getattr(finding, "position", 0),
                }
            ]
    except _ERRORS:
        pass

    # Promise-without-action detector (named 2026-05-15 night when
    # "Fixing it" appeared in a response that did not fix the named
    # slip, and the same slip recurred the next turn).
    try:
        from divineos.core.operating_loop.promise_without_action_detector import (
            evaluate_promise_without_action,
        )

        tool_names_pwa = [getattr(tc, "name", "") for tc in (tool_calls_in_turn or [])]
        verdict_pwa = evaluate_promise_without_action(
            last_assistant_text, tool_calls_in_turn=tool_names_pwa
        )
        if verdict_pwa.flags:
            findings_log["promise_without_action"] = [
                {
                    "kind": str(getattr(f.kind, "value", f.kind)),
                    "matched": list(f.matched_phrases),
                }
                for f in verdict_pwa.flags
            ]
    except _ERRORS:
        pass

    # Meet-without-build detector (named 2026-05-14 night when I shipped
    # operator-audit-layer affirmation then violated it in the very next
    # turn — meet without build is the inverse failure to build without
    # meet, both caught here).
    try:
        from divineos.core.operating_loop.meet_without_build_detector import (
            evaluate_meet_without_build,
        )

        tool_names_for_mwb = [getattr(tc, "name", "") for tc in (tool_calls_in_turn or [])]
        verdict_mwb = evaluate_meet_without_build(
            last_assistant_text, tool_calls_in_turn=tool_names_for_mwb
        )
        if verdict_mwb.flags:
            findings_log["meet_without_build"] = [
                {
                    "kind": str(getattr(f.kind, "value", f.kind)),
                    "matched": list(f.matched_phrases),
                }
                for f in verdict_mwb.flags
            ]
    except _ERRORS:
        pass

    # Register-fabrication detector (gate quest 2026-05-14). Catches
    # ALL_CAPS identifier-shaped tokens and structural-quantifier
    # claims in response text when no Read/Grep tool calls happened in
    # the same turn. Closes the QUANTUM/EMPIRICA enum-fabrication
    # failure-mode at the response layer.
    try:
        from divineos.core.self_monitor.register_fabrication_monitor import (
            evaluate_register_fabrication,
        )

        tool_names = [getattr(tc, "name", "") for tc in (tool_calls_in_turn or [])]
        verdict_rf = evaluate_register_fabrication(
            last_assistant_text, tool_calls_in_turn=tool_names
        )
        if verdict_rf.flags:
            findings_log["register_fabrication"] = [
                {
                    "kind": str(getattr(f.kind, "value", f.kind)),
                    "matched": list(f.matched_phrases),
                }
                for f in verdict_rf.flags
            ]
    except _ERRORS:
        pass

    # Fatigue-fabrication detector (gate quest 2026-05-14). Catches
    # close-reach + fatigue-claim phrasings when the operator has not
    # signaled close in the same turn.
    try:
        from divineos.core.self_monitor.fatigue_monitor import evaluate_fatigue

        verdict = evaluate_fatigue(last_assistant_text, last_user_text or "")
        if verdict.flags:
            findings_log["fatigue"] = [
                {
                    "kind": str(getattr(f.kind, "value", f.kind)),
                    "matched": list(f.matched_phrases),
                }
                for f in verdict.flags
            ]
    except _ERRORS:
        pass

    try:
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        harm_finding = check_response(last_assistant_text)
        if harm_finding:
            findings_log["harm_acknowledgment"] = [
                {
                    "trigger": getattr(harm_finding, "trigger_phrase", ""),
                    "position": getattr(harm_finding, "position", 0),
                }
            ]
    except _ERRORS:
        pass

    total = sum(len(v) for v in findings_log.values())
    persisted = False
    if write and total > 0:
        persisted = _persist_findings(findings_log, total)

    return {
        "findings_log": findings_log,
        "total_findings": total,
        "persisted": persisted,
    }


def _persist_findings(findings_log: dict[str, list], total: int) -> bool:
    """Append an entry to the rolling-window findings file. Returns
    True on success, False on any I/O error (fail-soft)."""
    try:
        marker_path("operating_loop_findings.json").parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    existing: list = []
    if marker_path("operating_loop_findings.json").exists():
        try:
            data = json.loads(
                marker_path("operating_loop_findings.json").read_text(encoding="utf-8")
            )
            if isinstance(data, list):
                existing = data
        except (OSError, json.JSONDecodeError, ValueError):
            existing = []

    entry: dict[str, Any] = {
        "timestamp": time.time(),
        "total_findings": total,
        **findings_log,
    }
    existing.append(entry)
    existing = existing[-_ROLLING_WINDOW:]

    try:
        marker_path("operating_loop_findings.json").write_text(
            json.dumps(existing, indent=2), encoding="utf-8"
        )
        return True
    except OSError:
        return False


__all__ = ["run_audit"]
