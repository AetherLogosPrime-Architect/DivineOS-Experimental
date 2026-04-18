"""Session Analysis — Core pipeline for analyzing sessions.

This module ties together quality checks, session features, and memory
to produce actionable insights about AI performance.
"""

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from loguru import logger

from divineos.analysis.analysis_types import AnalysisResult
from divineos.analysis.quality_checks import run_all_checks
from divineos.analysis.quality_storage import store_report
from divineos.analysis.session_features import run_all_features
from divineos.core.knowledge import extract_lessons_from_report
from divineos.core.ledger import get_connection as _get_connection
from divineos.core.ledger import get_verified_events
from divineos.core.parser import parse_jsonl
from divineos.core.session_manager import get_session_tracker


def analyze_session(file_path: Path) -> AnalysisResult:
    """Analyze a session file completely.

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

    # 2. Run quality checks and persist results
    quality_report = run_all_checks(file_path)
    store_report(quality_report)

    # 3. Run session features
    features = run_all_features(file_path)

    # 4. Extract lessons — pass tone shifts and error recovery from features
    checks_list: list[dict[str, Any]] = [
        {
            "name": check.check_name,
            "passed": check.passed,
            "score": check.score,
            "summary": check.summary,
        }
        for check in (quality_report.checks if hasattr(quality_report, "checks") else [])
    ]

    # Convert feature tone shifts to the format extract_lessons expects
    # Include sequence/before_message/previous_tone for recovery arc pairing
    tone_shifts_for_lessons: list[dict[str, Any]] | None = None
    if hasattr(features, "tone_shifts") and features.tone_shifts:
        tone_shifts_for_lessons = [
            {
                "direction": "negative" if ts.new_tone == "negative" else "positive",
                "previous_tone": ts.previous_tone,
                "new_tone": ts.new_tone,
                "trigger": ts.trigger_action,
                "user_response": getattr(ts, "after_message", ""),
                "before_message": getattr(ts, "before_message", ""),
                "sequence": ts.sequence,
            }
            for ts in features.tone_shifts
            if ts.previous_tone != ts.new_tone
        ]

    # Convert error recovery entries to aggregate counts
    error_recovery_for_lessons: dict[str, Any] | None = None
    if hasattr(features, "error_recovery") and features.error_recovery:
        blind_retries = sum(1 for e in features.error_recovery if e.recovery_action == "retry")
        investigate_count = sum(
            1 for e in features.error_recovery if e.recovery_action == "investigate"
        )
        error_recovery_for_lessons = {
            "blind_retries": blind_retries,
            "investigate_count": investigate_count,
        }

    # Convert edit-read pairings to aggregate counts for blind_coding.
    edit_read_for_lessons: dict[str, int] | None = None
    if hasattr(features, "edit_read_pairings") and features.edit_read_pairings is not None:
        pairings = features.edit_read_pairings
        edit_read_for_lessons = {
            "total_edits": len(pairings),
            "paired_edits": sum(1 for p in pairings if p.read_before_edit),
        }

    lessons_raw = extract_lessons_from_report(
        checks_list,
        session_id,
        tone_shifts_for_lessons,
        error_recovery_for_lessons,
        edit_read_pairings=edit_read_for_lessons,
    )
    lessons = cast("list[dict[str, Any]]", lessons_raw if isinstance(lessons_raw, list) else [])

    # 5. Create evidence hash
    evidence_data: dict[str, Any] = {
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
    return AnalysisResult(
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


def _generate_session_id(file_path: Path) -> str:
    """Generate a session ID from file path and timestamp."""
    import hashlib

    timestamp = datetime.now(timezone.utc).isoformat()
    combined = f"{file_path.name}:{timestamp}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _hash_evidence(data: dict[str, Any]) -> str:
    """Hash evidence data for fidelity verification."""
    import hashlib

    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


def export_current_session_to_jsonl(limit: int = 100) -> Path:
    """Export the current session from the ledger to a JSONL file.

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
    import json
    import tempfile
    from pathlib import Path

    # Get current session ID for session isolation
    # Priority: database query (actual user/tool events) > file (current session)
    # > session tracker (fallback)
    current_session_id = None

    # First, query database for most recent USER_INPUT or TOOL_CALL event
    # (actual work events). Skip analysis/report events which are metadata,
    # not actual session work

    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT payload FROM system_events WHERE event_type IN "
            "('USER_INPUT', 'TOOL_CALL', 'TOOL_RESULT') "
            "ORDER BY timestamp DESC LIMIT 1",
        )
        row = cursor.fetchone()
        if row:
            payload = json.loads(row[0])
            current_session_id = payload.get("session_id")
            logger.debug(
                f"[DEBUG] Got session_id from database query for analysis: {current_session_id}",
            )
    finally:
        conn.close()

    # If no events in database, try to read from persistent file (current session)
    if not current_session_id:
        session_file = Path.home() / ".divineos" / "current_session.txt"
        if session_file.exists():
            try:
                current_session_id = session_file.read_text(encoding="utf-8").strip()
                logger.debug(
                    f"[DEBUG] Read session_id from file for analysis: {current_session_id}",
                )
            except _ANALYSIS_ERRORS as e:
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
                f"Corrupted event {corrupted['event_id']}: "
                f"{corrupted.get('corruption_reason', 'unknown')}",
            )

    if not verified_events:
        error_msg = "No valid events in ledger to export"
        raise ValueError(error_msg)

    # Convert ledger events to JSONL format (Claude Code format)
    jsonl_lines = []
    for event in verified_events:
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})

        # Convert to Claude Code message format
        msg: dict[str, Any] | None = None
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
                        },
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


# --- Backward-compatibility re-exports ---
# These were moved to analysis_storage.py but many importers still reference
# them from this module. Re-exporting keeps existing imports working.
from divineos.analysis.analysis_storage import (  # noqa: E402, F401
    compute_cross_session_trends,
    format_analysis_report,
    format_cross_session_report,
    get_stored_report,
    list_recent_sessions,
    save_analysis_report,
    store_analysis,
)

_ANALYSIS_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)
