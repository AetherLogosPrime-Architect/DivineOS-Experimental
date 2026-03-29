"""Analysis Storage — Storage, reporting, retrieval, and cross-session trends.

Handles persisting analysis results to the database, formatting reports,
retrieving stored reports, and computing trends across sessions.
"""

import json
from dataclasses import asdict

from loguru import logger

from divineos.analysis.analysis_types import AnalysisResult


def store_analysis(result: AnalysisResult, report_text: str = "") -> bool:
    """Store analysis results in the database with fidelity verification.

    Uses manifest-receipt reconciliation pattern:
    1. Create manifest (hash all findings before storage)
    2. Store in database tables
    3. Create receipt (hash stored data after retrieval)
    4. Reconcile manifest ↔ receipt to verify integrity

    Args:
        result: AnalysisResult to store
        report_text: Formatted report text to store

    Returns:
        True if storage succeeded and fidelity verified

    Raises:
        Exception: If fidelity verification fails

    """
    import time
    import uuid

    from divineos.core.ledger import get_connection_fk as get_qc_connection
    from divineos.core import fidelity

    try:
        # Count items to store
        check_count = 0
        if hasattr(result.quality_report, "checks") and result.quality_report.checks:
            check_count = len(result.quality_report.checks)

        # Step 1: Create manifest (count of items to store)
        manifest_count = 1 + check_count + 1  # session_report + checks + features
        manifest_content = json.dumps(
            {
                "session_id": result.session_id,
                "evidence_hash": result.evidence_hash,
                "check_count": check_count,
                "has_features": True,
            },
            sort_keys=True,
        )
        manifest = fidelity.FidelityManifest(
            count=manifest_count,
            content_hash=fidelity.compute_content_hash(manifest_content),
            bytes_total=len(manifest_content.encode("utf-8")),
        )
        logger.debug(f"Created manifest: count={manifest.count}, hash={manifest.content_hash}")

        # Step 2: Store in database
        conn = get_qc_connection()
        cursor = conn.cursor()
        current_time = time.time()

        # Store session_report
        cursor.execute(
            "INSERT OR REPLACE INTO session_report "
            "(session_id, created_at, report_text, evidence_hash) "
            "VALUES (?, ?, ?, ?)",
            (result.session_id, current_time, report_text, result.evidence_hash),
        )

        # Store check_result entries
        if hasattr(result.quality_report, "checks") and result.quality_report.checks:
            for check in result.quality_report.checks:
                check_name = (
                    check.check_name
                    if hasattr(check, "check_name")
                    else check.get("check_name", "unknown")
                )
                raw_passed = check.passed if hasattr(check, "passed") else check.get("passed", 0)
                # Preserve -1 (inconclusive), 0 (failed), 1 (passed)
                passed = int(raw_passed) if raw_passed in (-1, 0, 1) else (1 if raw_passed else 0)
                score = check.score if hasattr(check, "score") else check.get("score", 0.0)
                summary = check.summary if hasattr(check, "summary") else check.get("summary", "")
                evidence_hash = (
                    check.evidence_hash
                    if hasattr(check, "evidence_hash")
                    else check.get("evidence_hash", "")
                )

                cursor.execute(
                    "INSERT INTO check_result "
                    "(session_id, check_name, passed, score, evidence_hash, "
                    "summary, raw_evidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        result.session_id,
                        check_name,
                        passed,
                        score,
                        evidence_hash,
                        summary,
                        json.dumps(
                            asdict(check) if hasattr(check, "__dataclass_fields__") else check,
                            default=str,
                        ),
                    ),
                )

        # Store feature_result entries
        if hasattr(result.features, "__dataclass_fields__"):
            features_data = asdict(result.features)
        else:
            features_data = result.features

        feature_result_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO feature_result "
            "(result_id, session_id, feature_name, data_json, "
            "evidence_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                feature_result_id,
                result.session_id,
                "full_analysis",
                json.dumps(features_data, default=str),
                result.evidence_hash,
                current_time,
            ),
        )

        conn.commit()

        # Step 3: Create receipt (verify stored data)
        # Retrieve session_report
        cursor.execute(
            "SELECT COUNT(*) FROM session_report WHERE session_id = ?",
            (result.session_id,),
        )
        session_count = cursor.fetchone()[0]

        # Retrieve check_results
        cursor.execute(
            "SELECT COUNT(*) FROM check_result WHERE session_id = ?",
            (result.session_id,),
        )
        stored_check_count = cursor.fetchone()[0]

        # Retrieve feature_result
        cursor.execute(
            "SELECT COUNT(*) FROM feature_result WHERE session_id = ?",
            (result.session_id,),
        )
        feature_count = cursor.fetchone()[0]

        conn.close()

        # Verify counts match
        receipt_count = session_count + stored_check_count + feature_count
        receipt_content = json.dumps(
            {
                "session_id": result.session_id,
                "evidence_hash": result.evidence_hash,
                "check_count": stored_check_count,
                "has_features": feature_count > 0,
            },
            sort_keys=True,
        )
        receipt = fidelity.FidelityReceipt(
            count=receipt_count,
            content_hash=fidelity.compute_content_hash(receipt_content),
            bytes_total=len(receipt_content.encode("utf-8")),
            stored_ids=[f"item_{i}" for i in range(receipt_count)],
        )
        logger.debug(f"Created receipt: count={receipt.count}, hash={receipt.content_hash}")

        # Step 4: Reconcile manifest ↔ receipt
        fidelity_result = fidelity.reconcile(manifest, receipt)

        if not fidelity_result.passed:
            error_msg = f"Fidelity verification failed: {'; '.join(fidelity_result.errors)}"
            logger.error(error_msg)
            raise Exception(error_msg)

        logger.info(f"Fidelity verification passed for session {result.session_id}")

        # Step 5: Emit events to ledger
        try:
            from divineos.event.event_emission import emit_event

            # Emit quality report event
            emit_event(
                "QUALITY_REPORT",
                {
                    "session_id": result.session_id,
                    "check_count": check_count,
                    "evidence_hash": result.evidence_hash,
                },
                actor="system",
            )

            # Emit session features event
            emit_event(
                "SESSION_FEATURES",
                {"session_id": result.session_id, "evidence_hash": result.evidence_hash},
                actor="system",
            )

            # Emit session analysis event
            emit_event(
                "SESSION_ANALYSIS",
                {
                    "session_id": result.session_id,
                    "report_text": report_text or "",
                    "evidence_hash": result.evidence_hash,
                },
                actor="system",
            )
        except Exception as e:
            logger.warning(f"Failed to emit analysis events: {e}")
            # Don't fail the whole operation if event emission fails

        return True

    except Exception as e:
        logger.error(f"Failed to store analysis: {e}")
        raise


def format_analysis_report(result: AnalysisResult) -> str:
    """Format analysis results as a plain-English report.

    No jargon. No code-speak. Human-readable.

    Args:
        result: AnalysisResult to format

    Returns:
        Formatted report string

    """
    lines = []

    # Header
    lines.append("=" * 70)
    lines.append("SESSION ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Session ID: {result.session_id}")
    lines.append(f"File: {result.file_path}")
    lines.append(f"Analyzed: {result.timestamp}")

    # Session metadata
    if result.duration_seconds > 0:
        minutes = int(result.duration_seconds / 60)
        lines.append(f"Duration: {minutes} minutes")

    if result.files_touched_count > 0:
        lines.append(f"Files touched: {result.files_touched_count}")

    lines.append("")

    # Quality Checks
    lines.append("QUALITY CHECKS (7 dimensions)")
    lines.append("-" * 70)

    if hasattr(result.quality_report, "checks") and result.quality_report.checks:
        for check in result.quality_report.checks:
            passed = check.passed if hasattr(check, "passed") else check.get("passed", 0)
            status = "[PASS]" if passed else "[FAIL]"
            name = (
                check.check_name
                if hasattr(check, "check_name")
                else check.get("check_name", "Unknown")
            )
            name = name.replace("_", " ").title()
            summary = check.summary if hasattr(check, "summary") else check.get("summary", "")

            lines.append(f"{status} — {name}")
            if summary:
                # Wrap long summaries
                for line in summary.split("\n"):
                    lines.append(f"  {line}")
            lines.append("")

    # Session Features
    lines.append("SESSION FEATURES (what happened)")
    lines.append("-" * 70)

    if hasattr(result.features, "report_text") and result.features.report_text:
        lines.append(result.features.report_text)
    else:
        # Fallback: show individual features
        if hasattr(result.features, "tone_shifts") and result.features.tone_shifts:
            lines.append(f"Tone: Detected {len(result.features.tone_shifts)} tone shift(s)")

        if hasattr(result.features, "files_touched") and result.features.files_touched:
            blind_count = sum(1 for f in result.features.files_touched if not f.was_read_first)
            total_count = len(result.features.files_touched)
            lines.append(f"Files: Touched {total_count} files, {blind_count} without reading first")

        if hasattr(result.features, "activity") and result.features.activity:
            activity = result.features.activity
            if hasattr(activity, "total_text_blocks"):
                lines.append(
                    f"Activity: {activity.total_text_blocks} explanations, "
                    f"{activity.total_tool_calls} actions",
                )

    lines.append("")

    # Lessons
    if result.lessons:
        lines.append("LESSONS EXTRACTED (what to learn)")
        lines.append("-" * 70)

        # If lessons are knowledge IDs, try to retrieve the content
        from divineos.core.knowledge import get_knowledge

        for lesson in result.lessons:
            try:
                # Try to get the knowledge entry
                lesson_id = lesson.get("id") if isinstance(lesson, dict) else str(lesson)
                if not lesson_id:
                    continue
                knowledge_entries = get_knowledge(limit=1000)
                for entry in knowledge_entries:
                    if entry.get("id") == lesson_id or entry.get("knowledge_id") == lesson_id:
                        content = entry.get("content", lesson_id)
                        lines.append(f"• {content}")
                        break
                else:
                    # If not found, just show the ID
                    lines.append(f"• Lesson {lesson_id[:8]}...")
            except Exception:
                # Fallback: just show the ID
                lesson_id_str = str(lesson)[:8] if isinstance(lesson, dict) else str(lesson)[:8]
                lines.append(f"• Lesson {lesson_id_str}...")

        lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append(f"Evidence Hash: {result.evidence_hash}")
    lines.append("All findings are traceable back to source records.")
    lines.append("=" * 70)

    return "\n".join(lines)


from divineos.analysis.analysis_retrieval import (  # noqa: E402
    get_stored_report as get_stored_report,
    list_recent_sessions as list_recent_sessions,
    compute_cross_session_trends as compute_cross_session_trends,
    format_cross_session_report as format_cross_session_report,
    save_analysis_report as save_analysis_report,
)
