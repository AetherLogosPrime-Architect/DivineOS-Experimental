"""
Session Analysis — Core logic for analyzing sessions and generating reports.

This module ties together quality checks, session features, and memory
to produce actionable insights about AI performance.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional, cast
import json
from datetime import datetime, timezone
from loguru import logger

from divineos.parser import parse_jsonl
from divineos.quality_checks import run_all_checks
from divineos.session_features import run_all_features
from divineos.consolidation import extract_lessons_from_report
from divineos.ledger import get_verified_events


@dataclass
class AnalysisResult:
    """Complete analysis of a session."""

    session_id: str
    file_path: str
    timestamp: str
    quality_report: Any  # SessionReport from quality_checks
    features: Any  # FullSessionAnalysis from session_features
    lessons: list[dict]  # Extracted lessons
    evidence_hash: str  # Hash of all findings
    duration_seconds: float = 0.0  # Session duration
    files_touched_count: int = 0  # Number of files touched


def analyze_session(file_path: Path) -> AnalysisResult:
    """
    Analyze a session file completely.

    Steps:
    1. Parse the JSONL file
    2. Run quality checks (7 checks)
    3. Run session features (10 features)
    4. Extract lessons from findings
    5. Combine into AnalysisResult

    Args:
        file_path: Path to JSONL session file

    Returns:
        AnalysisResult with all findings

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is empty or malformed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Session file not found: {file_path}")

    # 1. Parse JSONL
    parse_result = parse_jsonl(file_path)

    if not parse_result.messages:
        raise ValueError(f"No messages found in {file_path}")

    # Convert to records format for analysis
    records = [msg.to_dict() for msg in parse_result.messages]

    # Generate session ID first
    session_id = _generate_session_id(file_path)

    # 2. Run quality checks
    quality_report = run_all_checks(file_path)

    # 3. Run session features
    features = run_all_features(file_path)

    # 4. Extract lessons
    checks_list = [
        {
            "name": check.check_name,
            "passed": check.passed,
            "score": check.score,
            "summary": check.summary,
        }
        for check in (quality_report.checks if hasattr(quality_report, "checks") else [])
    ]
    lessons_raw = extract_lessons_from_report(checks_list, session_id)
    lessons = cast(list[dict[Any, Any]], lessons_raw if isinstance(lessons_raw, list) else [])

    # 5. Create evidence hash
    evidence_data = {
        "quality_checks": asdict(quality_report)
        if hasattr(quality_report, "__dataclass_fields__")
        else quality_report,
        "features": asdict(features) if hasattr(features, "__dataclass_fields__") else features,
        "lessons": lessons,
    }
    evidence_hash = _hash_evidence(evidence_data)

    # Extract session metadata
    duration_seconds = 0.0
    files_touched_count = 0

    # Try to extract duration from timestamps
    if records and len(records) > 1:
        first_ts = records[0].get("timestamp", 0)
        last_ts = records[-1].get("timestamp", 0)
        if isinstance(first_ts, (int, float)) and isinstance(last_ts, (int, float)):
            duration_seconds = max(0, last_ts - first_ts)

    # Count files touched from features
    if hasattr(features, "files_touched") and features.files_touched:
        files_touched_count = len(features.files_touched)

    # 6. Create result
    result = AnalysisResult(
        session_id=session_id,
        file_path=str(file_path),
        timestamp=datetime.now(timezone.utc).isoformat(),
        quality_report=quality_report,
        features=features,
        lessons=lessons,
        evidence_hash=evidence_hash,
        duration_seconds=duration_seconds,
        files_touched_count=files_touched_count,
    )

    return result


def _generate_session_id(file_path: Path) -> str:
    """Generate a session ID from file path and timestamp."""
    import hashlib

    timestamp = datetime.now(timezone.utc).isoformat()
    combined = f"{file_path.name}:{timestamp}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _hash_evidence(data: dict) -> str:
    """Hash evidence data for fidelity verification."""
    import hashlib

    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


def export_current_session_to_jsonl(limit: int = 100) -> Path:
    """
    Export the current session from the ledger to a JSONL file.

    This allows analyzing the live session without waiting for a file.
    Automatically excludes corrupted events from the export.
    Filters by session ID to ensure session isolation.

    Args:
        limit: Maximum number of events to export

    Returns:
        Path to the exported JSONL file

    Requirements:
        - Requirement 7.5: Prevent corrupted events from being used in analysis
        - Requirement 9.3: Session event correlation - filter by session_id
    """
    import tempfile
    from divineos.event_capture import get_session_tracker
    from pathlib import Path
    import json

    # Get current session ID for session isolation
    # Priority: database query (actual user/tool events) > file (current session) > session tracker (fallback)
    current_session_id = None

    # First, query database for most recent USER_INPUT or TOOL_CALL event (actual work events)
    # Skip analysis/report events which are metadata, not actual session work
    from divineos.ledger import _get_connection

    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT payload FROM system_events WHERE event_type IN ('USER_INPUT', 'TOOL_CALL', 'TOOL_RESULT') ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            payload = json.loads(row[0])
            current_session_id = payload.get("session_id")
            logger.debug(
                f"[DEBUG] Got session_id from database query for analysis: {current_session_id}"
            )
    finally:
        conn.close()

    # If no events in database, try to read from persistent file (current session)
    if not current_session_id:
        session_file = Path.home() / ".divineos" / "current_session.txt"
        if session_file.exists():
            try:
                current_session_id = session_file.read_text().strip()
                logger.debug(
                    f"[DEBUG] Read session_id from file for analysis: {current_session_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to read session_id file: {e}")
                current_session_id = None

    # Fallback to current session tracker if no events found and no file
    if not current_session_id:
        current_session_id = get_session_tracker().get_current_session_id()
        logger.debug(f"[DEBUG] Using session tracker session_id for analysis: {current_session_id}")

    # Get verified events from ledger (excludes corrupted events, filters by session)
    # Use a large limit to ensure we get events even if they're far back in the ledger
    verified_events, corrupted_events = get_verified_events(
        limit=10000,  # Increased from default 100 to ensure we find current session events
        skip_corrupted=True,
        session_id=current_session_id,
    )

    if corrupted_events:
        logger.warning(f"Excluded {len(corrupted_events)} corrupted events from analysis")
        for corrupted in corrupted_events:
            logger.debug(
                f"Corrupted event {corrupted['event_id']}: {corrupted.get('corruption_reason', 'unknown')}"
            )

    if not verified_events:
        raise ValueError("No valid events in ledger to export")

    # Convert ledger events to JSONL format (Claude Code format)
    jsonl_lines = []
    for event in verified_events:
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})

        # Convert to Claude Code message format
        if event_type == "USER_INPUT":
            msg = {
                "type": "user",
                "message": {"role": "user", "content": payload.get("content", "")},
            }
        elif event_type in ("ASSISTANT", "ASSISTANT_OUTPUT"):
            msg = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": payload.get("content", "")}],
                },
            }
        elif event_type == "TOOL_CALL":
            msg = {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": payload.get("tool_use_id", ""),
                            "name": payload.get("tool_name", ""),
                            "input": payload.get("tool_input", {}),
                        }
                    ],
                },
            }
        elif event_type == "TOOL_RESULT":
            msg = {
                "type": "tool",
                "message": {
                    "tool_use_id": payload.get("tool_use_id", ""),
                    "content": payload.get("result", ""),
                },
            }
        else:
            continue

        jsonl_lines.append(json.dumps(msg))

    # Write to temporary file in system temp directory
    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / "current_session.jsonl"
    temp_file.write_text("\n".join(jsonl_lines), encoding="utf-8")

    return temp_file


def store_analysis(result: AnalysisResult, report_text: str = "") -> bool:
    """
    Store analysis results in the database with fidelity verification.

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
    import uuid
    import time
    from divineos.quality_checks import _get_connection as get_qc_connection
    from divineos import fidelity

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
            "INSERT OR REPLACE INTO session_report (session_id, created_at, report_text, evidence_hash) VALUES (?, ?, ?, ?)",
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
                passed = (
                    1
                    if (check.passed if hasattr(check, "passed") else check.get("passed", False))
                    else 0
                )
                score = check.score if hasattr(check, "score") else check.get("score", 0.0)
                summary = check.summary if hasattr(check, "summary") else check.get("summary", "")
                evidence_hash = (
                    check.evidence_hash
                    if hasattr(check, "evidence_hash")
                    else check.get("evidence_hash", "")
                )

                cursor.execute(
                    "INSERT INTO check_result (session_id, check_name, passed, score, evidence_hash, summary, raw_evidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
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
            "INSERT INTO feature_result (result_id, session_id, feature_name, data_json, evidence_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
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
            "SELECT COUNT(*) FROM session_report WHERE session_id = ?", (result.session_id,)
        )
        session_count = cursor.fetchone()[0]

        # Retrieve check_results
        cursor.execute(
            "SELECT COUNT(*) FROM check_result WHERE session_id = ?", (result.session_id,)
        )
        stored_check_count = cursor.fetchone()[0]

        # Retrieve feature_result
        cursor.execute(
            "SELECT COUNT(*) FROM feature_result WHERE session_id = ?", (result.session_id,)
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
            from divineos.event_dispatcher import emit_event

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
                    "report_text": report_text[:500] if report_text else "",  # First 500 chars
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
    """
    Format analysis results as a plain-English report.

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
            status = "✓ PASS" if passed else "✗ FAIL"
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
                    f"Activity: {activity.total_text_blocks} explanations, {activity.total_tool_calls} actions"
                )

    lines.append("")

    # Lessons
    if result.lessons:
        lines.append("LESSONS EXTRACTED (what to learn)")
        lines.append("-" * 70)

        # If lessons are knowledge IDs, try to retrieve the content
        from divineos.consolidation import get_knowledge

        for lesson_id in result.lessons:
            try:
                # Try to get the knowledge entry
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
                lines.append(f"• Lesson {lesson_id[:8]}...")

        lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append(f"Evidence Hash: {result.evidence_hash}")
    lines.append("All findings are traceable back to source records.")
    lines.append("=" * 70)

    return "\n".join(lines)


def get_stored_report(session_id: str) -> Optional[str]:
    """Retrieve a stored analysis report from the database.

    Args:
        session_id: The session ID to retrieve

    Returns:
        Report text if found, None otherwise
    """
    from divineos.quality_checks import _get_connection as get_qc_connection

    try:
        conn = get_qc_connection()
        cursor = conn.cursor()

        # Query the session_report table
        cursor.execute("SELECT report_text FROM session_report WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()

        if row and row[0]:
            conn.close()
            return cast(str, row[0])

        # If no report_text stored, check if checks/features exist
        cursor.execute("SELECT COUNT(*) FROM check_result WHERE session_id = ?", (session_id,))
        check_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM feature_result WHERE session_id = ?", (session_id,))
        feature_count = cursor.fetchone()[0]

        conn.close()

        if check_count > 0 or feature_count > 0:
            return f"Session {session_id}: Analysis stored"

        return None
    except Exception as e:
        logger.error(f"Failed to retrieve report: {e}")
        return None


def list_recent_sessions(limit: int = 10) -> list[dict]:
    """List recent analyzed sessions.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of session dicts with id, created_at, file_count
    """
    from divineos.quality_checks import _get_connection as get_qc_connection

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
                }
            )

        conn.close()
        return sessions
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return []


def compute_cross_session_trends(limit: int = 10) -> dict:
    """Compute trends across multiple sessions.

    Args:
        limit: Number of recent sessions to analyze

    Returns:
        Dict with trends and patterns
    """
    from divineos.quality_checks import get_check_history

    # Get check history for each check
    trends = {}
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
            check_results = get_check_history(check_name, limit=limit)

            if check_results:
                pass_count = sum(1 for h in check_results if h.get("passed"))
                total_count = len(check_results)
                pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0

                trends[check_name] = {
                    "pass_rate": pass_rate,
                    "pass_count": pass_count,
                    "total_count": total_count,
                    "results": check_results[:5],  # Last 5 results
                }
        except Exception:
            # If check history not available, skip
            pass

    return trends


def format_cross_session_report(trends: dict) -> str:
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

        # Determine trend
        if pass_rate >= 80:
            trend = "✓ Strong"
            color_hint = "(good)"
        elif pass_rate >= 60:
            trend = "→ Stable"
            color_hint = "(okay)"
        else:
            trend = "↓ Needs work"
            color_hint = "(needs improvement)"

        lines.append(f"{name}: {trend} {color_hint}")
        lines.append(f"  Pass rate: {pass_rate:.0f}% ({pass_count}/{total_count})")
        lines.append("")

    lines.append("=" * 70)
    lines.append("Trends based on recent sessions.")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_analysis_report(result: AnalysisResult, report_text: str) -> Path:
    """
    Save analysis report to file.

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
