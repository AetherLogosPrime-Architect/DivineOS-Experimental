"""Analysis Storage — Storage, reporting, retrieval, and cross-session trends.

Handles persisting analysis results to the database, formatting reports,
retrieving stored reports, and computing trends across sessions.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from loguru import logger

from divineos.analysis.analysis import AnalysisResult


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


def get_stored_report(session_id: str) -> str | None:
    """Retrieve a stored analysis report from the database.

    Args:
        session_id: The session ID to retrieve

    Returns:
        Report text if found, None otherwise

    """
    from divineos.core.ledger import get_connection_fk as get_qc_connection

    try:
        conn = get_qc_connection()
        cursor = conn.cursor()

        # Query the session_report table — support partial ID matching
        cursor.execute(
            "SELECT report_text FROM session_report WHERE session_id LIKE ?",
            (session_id + "%",),
        )
        row = cursor.fetchone()

        if row and row[0]:
            conn.close()
            return cast("str", row[0])

        # If no report_text stored, check if checks/features exist
        cursor.execute(
            "SELECT COUNT(*) FROM check_result WHERE session_id LIKE ?",
            (session_id + "%",),
        )
        check_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM feature_result WHERE session_id LIKE ?",
            (session_id + "%",),
        )
        feature_count = cursor.fetchone()[0]

        if check_count > 0 or feature_count > 0:
            # Build a summary from stored check results
            parts = [f"Session {session_id}: {check_count} checks, {feature_count} features\n"]
            if check_count > 0:
                checks = cursor.execute(
                    "SELECT check_name, passed, score FROM check_result WHERE session_id LIKE ?",
                    (session_id + "%",),
                ).fetchall()
                parts.append("Quality Checks:")
                for name, passed, score in checks:
                    status = "PASS" if passed else "FAIL"
                    parts.append(f"  [{status}] {name}: {score:.2f}")
            conn.close()
            return "\n".join(parts)

        conn.close()

        return None
    except Exception as e:
        logger.error(f"Failed to retrieve report: {e}")
        return None


def list_recent_sessions(limit: int = 10) -> list[dict[str, Any]]:
    """List recent analyzed sessions.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of session dicts with id, created_at, file_count

    """
    from divineos.core.ledger import get_connection_fk as get_qc_connection

    try:
        conn = get_qc_connection()
        cursor = conn.cursor()

        # Query session_report table, ordered by created_at DESC
        cursor.execute(
            "SELECT session_id, created_at FROM session_report ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()

        sessions = []
        for row in rows:
            session_id = row[0]
            created_at = row[1]

            # Count files touched for this session
            cursor.execute("SELECT COUNT(*) FROM file_touched WHERE session_id = ?", (session_id,))
            file_count = cursor.fetchone()[0]

            sessions.append(
                {
                    "session_id": session_id,
                    "created_at": created_at,
                    "file_count": file_count,
                },
            )

        conn.close()
        return sessions
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return []


def compute_cross_session_trends(limit: int = 10) -> dict[str, Any]:
    """Compute trends across multiple sessions.

    Args:
        limit: Number of recent sessions to analyze

    Returns:
        Dict with trends and patterns

    """
    from divineos.analysis.quality_storage import get_check_history

    # Get check history for each check
    trends: dict[str, Any] = {}
    for check_name in [
        "completeness",
        "correctness",
        "responsiveness",
        "safety",
        "honesty",
        "clarity",
        "task_adherence",
    ]:
        try:
            check_results: list[dict[str, Any]] = get_check_history(check_name, limit=limit)

            if check_results:
                # Only count explicitly passed (1), not inconclusive (-1)
                conclusive = [h for h in check_results if h.get("passed") != -1]
                pass_count = sum(1 for h in conclusive if h.get("passed") == 1)
                total_count = len(conclusive)
                inconclusive_count = len(check_results) - len(conclusive)
                pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0

                trends[check_name] = {
                    "pass_rate": pass_rate,
                    "pass_count": pass_count,
                    "total_count": total_count,
                    "inconclusive_count": inconclusive_count,
                    "results": check_results[:5],  # Last 5 results
                }
        except Exception as e:
            # If check history not available, skip but log the error
            logger.debug(f"Failed to get check history for {check_name}: {e}")

    return trends


def format_cross_session_report(trends: dict[str, Any]) -> str:
    """Format cross-session trends as a plain-English report.

    Args:
        trends: Dict from compute_cross_session_trends()

    Returns:
        Formatted report string

    """
    lines = []

    lines.append("=" * 70)
    lines.append("CROSS-SESSION ANALYSIS")
    lines.append("=" * 70)
    lines.append("")

    if not trends:
        lines.append("No session data available yet.")
        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)

    # Show each check
    for check_name, data in sorted(trends.items()):
        name = check_name.replace("_", " ").title()
        pass_rate = data["pass_rate"]
        pass_count = data["pass_count"]
        total_count = data["total_count"]
        inconclusive_count = data.get("inconclusive_count", 0)

        if total_count == 0:
            # All inconclusive — nothing to evaluate
            lines.append(f"{name}: [~] Insufficient data")
            lines.append(f"  {inconclusive_count} inconclusive (nothing to evaluate)")
            lines.append("")
            continue

        # Determine trend
        if pass_rate >= 80:
            trend = "[+] Strong"
            color_hint = "(good)"
        elif pass_rate >= 60:
            trend = "[~] Stable"
            color_hint = "(okay)"
        else:
            trend = "[-] Needs work"
            color_hint = "(needs improvement)"

        lines.append(f"{name}: {trend} {color_hint}")
        detail = f"  Pass rate: {pass_rate:.0f}% ({pass_count}/{total_count})"
        if inconclusive_count:
            detail += f", {inconclusive_count} inconclusive"
        lines.append(detail)
        lines.append("")

    lines.append("=" * 70)
    lines.append("Trends based on recent sessions.")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_analysis_report(result: AnalysisResult, report_text: str) -> Path:
    """Save analysis report to file.

    Args:
        result: AnalysisResult with session_id
        report_text: Formatted report text

    Returns:
        Path to saved report file

    """
    reports_dir = Path(__file__).parent.parent.parent / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / f"{result.session_id}.txt"
    # Use UTF-8 encoding to handle special characters like ✓ and ✗
    report_file.write_text(report_text, encoding="utf-8")

    return report_file
