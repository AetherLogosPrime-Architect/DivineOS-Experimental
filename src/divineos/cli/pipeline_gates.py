"""Pipeline gates — enforcement logic for SESSION_END pipeline.

Extracted from session_pipeline.py to keep the orchestrator focused
on sequencing, not on gate/enforcement/handoff details.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any

import click
from loguru import logger

from divineos.core.constants import (
    QUALITY_COMPASS_TIGHTEN,
    QUALITY_CORRECTNESS_BLOCK,
    QUALITY_HONESTY_BLOCK,
    QUALITY_MIN_FAILED_CHECKS_DOWNGRADE,
)

_GATE_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError)


def run_goal_extraction(analysis: Any) -> None:
    """Extract goals from user messages into HUD (step 1b)."""
    try:
        from divineos.core.hud_handoff import extract_goals_from_messages
        from divineos.core.hud_state import add_goal

        extracted_goals = extract_goals_from_messages(analysis.user_message_texts)
        for goal in extracted_goals:
            add_goal(goal["text"], original_words=goal["original_words"])
        if extracted_goals:
            click.secho(f"[~] Captured {len(extracted_goals)} goals from user messages.", fg="cyan")
    except _GATE_ERRORS as e:
        logger.warning(f"Goal extraction failed: {e}")


def enforce_briefing_gate() -> None:
    """Force-load briefing if not already loaded (step 1c).

    The OS cannot proceed without orientation context.
    """
    try:
        from divineos.core.hud_handoff import mark_briefing_loaded, was_briefing_loaded

        if not was_briefing_loaded():
            click.secho(
                "\n[!] Briefing not loaded. Loading now — I can't skip this.",
                fg="yellow",
                bold=True,
            )
            from divineos.core.active_memory import refresh_active_memory
            from divineos.core.memory import init_memory_tables

            init_memory_tables()
            refresh_active_memory(importance_threshold=0.3)
            click.secho("    Briefing loaded. Proceeding.\n", fg="green")
        # Always reset the staleness counter so step 8 sees a fresh briefing.
        mark_briefing_loaded()
    except _GATE_ERRORS as e:
        logger.warning(f"Briefing gate failed: {e}")


def enforce_engagement_gate() -> None:
    """Force-load thinking context if no queries happened this session (step 1d)."""
    try:
        from divineos.core.hud_handoff import is_engaged, mark_engaged

        if not is_engaged():
            click.secho(
                "[!] No thinking queries this session. Loading context now.",
                fg="yellow",
                bold=True,
            )
            from divineos.core.knowledge import get_lessons
            from divineos.core.memory import get_core

            lessons = get_lessons(status="active")
            improving = get_lessons(status="improving")
            click.secho(
                f"    Loaded {len(lessons)} active + {len(improving)} improving lessons.",
                fg="green",
            )
            core = get_core()
            click.secho(
                f"    Loaded {len(core)} core memory slots.",
                fg="green",
            )
            mark_engaged()
            click.secho("    Engaged. Proceeding.\n", fg="green")
    except _GATE_ERRORS as e:
        logger.warning(f"Engagement gate failed: {e}")


@dataclass
class QualityVerdict:
    """Result of the quality gate assessment."""

    action: str  # "ALLOW", "DOWNGRADE", or "BLOCK"
    score: float  # overall quality score (0.0-1.0)
    failed_checks: list[str] = field(default_factory=list)
    reason: str = ""


def _compass_adjustment() -> tuple[float, str]:
    """Check moral compass for truthfulness/confidence concerns.

    If truthfulness is in deficiency zone, return a positive adjustment
    that tightens the quality gate thresholds. The compass feeds back
    into extraction decisions — a system that's been unreliable recently
    gets a stricter gate.

    Returns:
        (adjustment, reason) where adjustment is added to block thresholds.
    """
    try:
        from divineos.core.moral_compass import compute_position

        truthfulness = compute_position("truthfulness", lookback=10)
        if truthfulness.zone == "deficiency" and truthfulness.observation_count >= 2:
            return (
                QUALITY_COMPASS_TIGHTEN,
                f"truthfulness in deficiency zone ({truthfulness.position:+.2f})",
            )
    except (ImportError, sqlite3.OperationalError, ValueError, OSError):
        pass
    return 0.0, ""


def assess_session_quality(check_results: list[dict[str, Any]]) -> QualityVerdict:
    """Assess session quality from check results and return a verdict.

    Args:
        check_results: list of dicts with keys: check_name, passed, score

    Returns:
        QualityVerdict with action ALLOW, DOWNGRADE, or BLOCK.
    """
    if not check_results:
        return QualityVerdict(action="ALLOW", score=0.5, reason="No checks available")

    scores: dict[str, float] = {}
    failed: list[str] = []

    for check in check_results:
        name = str(check.get("check_name", ""))
        score = float(check.get("score", 0.5))
        passed = check.get("passed", -1)
        scores[name] = score
        if passed == 0:
            failed.append(name)

    # Compass-informed threshold tightening: if truthfulness is in
    # deficiency zone, raise block thresholds (making the gate stricter).
    compass_adj, compass_reason = _compass_adjustment()

    # Circuit 1: Affect-extraction calibration — adjust thresholds based on
    # cross-session affect-quality correlations. If past sessions show high
    # affect but low quality, tighten now. If consistently good, relax slightly.
    calibration_adj = 0.0
    calibration_reason = ""
    try:
        from divineos.core.affect_calibration import get_calibration_adjustment

        cal = get_calibration_adjustment()
        calibration_adj = cal.get("threshold_adjustment", 0.0)
        calibration_reason = cal.get("reason", "")
        if calibration_adj != 0.0:
            logger.info("Circuit 1 calibration: %+.2f (%s)", calibration_adj, calibration_reason)
    except (ImportError, sqlite3.OperationalError, OSError) as e:
        logger.debug("Affect calibration unavailable: %s", e)

    total_adj = compass_adj + max(calibration_adj, 0.0)  # only tighten, never loosen below base
    honesty_threshold = QUALITY_HONESTY_BLOCK + total_adj
    correctness_threshold = QUALITY_CORRECTNESS_BLOCK + total_adj

    # Block conditions: dishonest or fundamentally incorrect sessions
    honesty = scores.get("honesty", 1.0)
    correctness = scores.get("correctness", 1.0)

    if honesty < honesty_threshold:
        reason = (
            f"Honesty score too low ({honesty:.2f}). Knowledge from dishonest sessions is poison."
        )
        if compass_reason:
            reason += f" Gate tightened: {compass_reason}."
        return QualityVerdict(
            action="BLOCK",
            score=honesty,
            failed_checks=failed,
            reason=reason,
        )

    if correctness < correctness_threshold:
        reason = (
            f"Correctness score too low ({correctness:.2f}). Wrong code means unreliable facts."
        )
        if compass_reason:
            reason += f" Gate tightened: {compass_reason}."
        return QualityVerdict(
            action="BLOCK",
            score=correctness,
            failed_checks=failed,
            reason=reason,
        )

    # Downgrade: multiple checks failed — knowledge enters as HYPOTHESIS
    if len(failed) >= QUALITY_MIN_FAILED_CHECKS_DOWNGRADE:
        avg_score = sum(scores.values()) / len(scores) if scores else 0.5
        return QualityVerdict(
            action="DOWNGRADE",
            score=avg_score,
            failed_checks=failed,
            reason=f"{len(failed)} checks failed ({', '.join(failed)}). Knowledge enters as HYPOTHESIS.",
        )

    # Allow: session is trustworthy
    avg_score = sum(scores.values()) / len(scores) if scores else 0.5
    return QualityVerdict(
        action="ALLOW",
        score=avg_score,
        failed_checks=failed,
        reason="Session quality acceptable.",
    )


def should_extract_knowledge(verdict: QualityVerdict) -> tuple[bool, str]:
    """Decide whether to extract knowledge and at what maturity level.

    Returns:
        (allowed, maturity_override) where maturity_override is
        "" for normal, "HYPOTHESIS" for downgraded, or "" with allowed=False for blocked.
    """
    if verdict.action == "BLOCK":
        return False, ""
    if verdict.action == "DOWNGRADE":
        return True, "HYPOTHESIS"
    return True, ""


def run_quality_gate(
    session_file: Any,
    since_timestamp: float | None = None,
) -> tuple[Any | None, str, bool, list[dict[str, Any]]]:
    """Run quality checks and decide whether extraction is allowed (step 1e).

    Returns:
        (quality_verdict, maturity_override, extract_allowed, check_results)
        If extract_allowed is False, caller should abort extraction.
        check_results is the list of check dicts for downstream lesson detection.
    """
    quality_verdict = None
    maturity_override = ""
    check_results: list[dict[str, Any]] = []
    try:
        from divineos.analysis.quality_checks import run_all_checks
        from divineos.analysis.quality_storage import store_report

        report = run_all_checks(session_file, since_timestamp=since_timestamp)
        store_report(report)
        check_results = [
            {
                "check_name": c.check_name,
                "name": c.check_name,
                "passed": c.passed,
                "score": c.score,
                "summary": getattr(c, "summary", ""),
            }
            for c in report.checks
        ]
        quality_verdict = assess_session_quality(check_results)
        extract_allowed, maturity_override = should_extract_knowledge(quality_verdict)

        if quality_verdict.action == "BLOCK":
            click.secho(f"[!] Quality gate BLOCKED: {quality_verdict.reason}", fg="red", bold=True)
            # Show which checks failed so the user understands why
            for cr in check_results:
                if cr.get("passed") == 0 and cr.get("summary"):
                    click.secho(f"    {cr['check_name']}: {cr['summary']}", fg="red")
            click.secho("[!] Skipping knowledge extraction for this session.", fg="red")
            return quality_verdict, maturity_override, False, check_results
        elif quality_verdict.action == "DOWNGRADE":
            click.secho(f"[!] Quality gate DOWNGRADE: {quality_verdict.reason}", fg="yellow")
            for cr in check_results:
                if cr.get("passed") == 0 and cr.get("summary"):
                    click.secho(f"    {cr['check_name']}: {cr['summary']}", fg="yellow")
    except _GATE_ERRORS as e:
        logger.warning(f"Quality gate failed (allowing extraction): {e}")

    return quality_verdict, maturity_override, True, check_results


def run_contradiction_scan(deep_ids: list[str]) -> int:
    """Scan new knowledge entries for contradictions with existing entries (step 3d).

    Returns the number of contradictions resolved.
    """
    from divineos.core.knowledge import _get_connection
    from divineos.core.knowledge_maintenance import (
        resolve_contradiction,
        scan_for_contradictions,
    )

    valid_ids = [did for did in deep_ids if did]
    if not valid_ids:
        return 0

    resolved = 0
    conn = _get_connection()
    try:
        for did in valid_ids:
            row = conn.execute(
                "SELECT content, knowledge_type FROM knowledge WHERE knowledge_id = ?",
                (did,),
            ).fetchone()
            if not row:
                continue
            new_content, new_type = row[0], row[1]
            existing_rows = conn.execute(
                "SELECT knowledge_id, content, knowledge_type, superseded_by "
                "FROM knowledge WHERE knowledge_type = ? AND knowledge_id != ? "
                "AND superseded_by IS NULL",
                (new_type, did),
            ).fetchall()
            existing_entries = [
                {
                    "knowledge_id": r[0],
                    "content": r[1],
                    "knowledge_type": r[2],
                    "superseded_by": r[3],
                }
                for r in existing_rows
            ]
            matches = scan_for_contradictions(new_content, new_type, existing_entries)
            for match in matches:
                resolve_contradiction(did, match)
                resolved += 1
    finally:
        conn.close()
    return resolved


def write_handoff_note(analysis: Any, stored: int, health: dict[str, Any] | None) -> None:
    """Write handoff note for next session (step 9d)."""
    try:
        from divineos.core.hud_handoff import save_handoff_note

        parts = [
            f"Last session: {analysis.user_messages} exchanges, "
            f"{stored} knowledge entries extracted."
        ]
        if len(analysis.corrections) > 0:
            parts.append(
                f"I was corrected {len(analysis.corrections)} time(s) — review what went wrong."
            )
        if health:
            parts.append(f"Session grade: {health['grade']}.")

        open_threads: list[str] = []
        for corr in analysis.corrections[:3]:
            text = getattr(corr, "content", corr) if not isinstance(corr, str) else corr
            open_threads.append(f"Correction: {str(text)[:120]}")
        for d in getattr(analysis, "decisions", [])[:2]:
            text = getattr(d, "content", d) if not isinstance(d, str) else d
            open_threads.append(f"Decision: {str(text)[:120]}")

        mood = ""
        if health:
            mood = {
                "A": "strong session",
                "B": "solid session",
                "C": "mixed session",
                "D": "rough session",
                "F": "difficult session",
            }.get(health["grade"], "")

        goals_state = ""
        try:
            import json as _json

            from divineos.core.hud import _ensure_hud_dir

            from divineos.core.hud_state import get_lifetime_goals_completed

            goals_path = _ensure_hud_dir() / "active_goals.json"
            if goals_path.exists():
                goals = _json.loads(goals_path.read_text(encoding="utf-8"))
                active = [g for g in goals if g.get("status") != "done"]
                done = [g for g in goals if g.get("status") == "done"]
                lifetime = get_lifetime_goals_completed()
                goals_state = (
                    f"{len(done)} completed ({lifetime} lifetime), {len(active)} still active"
                )
        except (json.JSONDecodeError, OSError, ImportError):
            pass

        # Structured continuation fields
        intent = ""
        blockers: list[str] = []
        next_steps: list[str] = []
        context_snapshot: dict[str, Any] = {}

        # Intent: derive from active goals
        try:
            if goals_path.exists():
                for g in active[:2]:
                    if g.get("text"):
                        intent = g["text"] if not intent else f"{intent}; {g['text']}"
        except (NameError, OSError):
            pass

        # Blockers: corrections are things that went wrong
        for corr in analysis.corrections[:3]:
            text = getattr(corr, "content", corr) if not isinstance(corr, str) else corr
            blockers.append(str(text)[:120])

        # Next steps: active goals not yet done
        try:
            if goals_path.exists():
                for g in active[:5]:
                    if g.get("text"):
                        next_steps.append(g["text"][:120])
        except (NameError, OSError):
            pass

        # Context snapshot: grade and recent knowledge
        if health:
            context_snapshot["session_grade"] = health["grade"]
        if stored > 0:
            context_snapshot["knowledge_stored"] = stored

        save_handoff_note(
            summary=" ".join(parts),
            open_threads=open_threads,
            mood=mood,
            goals_state=goals_state,
            session_id=analysis.session_id,
            intent=intent,
            blockers=blockers if blockers else None,
            next_steps=next_steps if next_steps else None,
            context_snapshot=context_snapshot if context_snapshot else None,
        )
        click.secho("[~] Handoff note saved for next session.", fg="cyan")
    except _GATE_ERRORS as e:
        logger.warning(f"Handoff note failed: {e}")
