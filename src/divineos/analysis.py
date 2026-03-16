"""
Session Analysis — Core logic for analyzing sessions and generating reports.

This module ties together quality checks, session features, and memory
to produce actionable insights about AI performance.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional
import json
from datetime import datetime, timezone
from loguru import logger

from divineos.parser import parse_jsonl
from divineos.quality_checks import run_all_checks, store_report
from divineos.session_features import run_all_features, store_features
from divineos.consolidation import extract_lessons_from_report
from divineos.fidelity import create_manifest, create_receipt, reconcile
from divineos.ledger import log_event, get_recent_context


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
        for check in (quality_report.checks if hasattr(quality_report, 'checks') else [])
    ]
    lessons = extract_lessons_from_report(checks_list, session_id)
    
    # 5. Create evidence hash
    evidence_data = {
        "quality_checks": asdict(quality_report) if hasattr(quality_report, '__dataclass_fields__') else quality_report,
        "features": asdict(features) if hasattr(features, '__dataclass_fields__') else features,
        "lessons": lessons,
    }
    evidence_hash = _hash_evidence(evidence_data)
    
    # Extract session metadata
    duration_seconds = 0.0
    files_touched_count = 0
    
    # Try to extract duration from timestamps
    if records and len(records) > 1:
        first_ts = records[0].get('timestamp', 0)
        last_ts = records[-1].get('timestamp', 0)
        if isinstance(first_ts, (int, float)) and isinstance(last_ts, (int, float)):
            duration_seconds = max(0, last_ts - first_ts)
    
    # Count files touched from features
    if hasattr(features, 'files_touched') and features.files_touched:
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


def store_analysis(result: AnalysisResult, report_text: str = "") -> bool:
    """
    Store analysis results in the database with fidelity verification.
    
    Steps:
    1. Create manifest (hash all findings before storage)
    2. Store in database tables:
       - session_report table
       - check_result table
       - feature_result table
    3. Verify storage succeeded
    
    Args:
        result: AnalysisResult to store
        report_text: Formatted report text to store
        
    Returns:
        True if storage succeeded, False otherwise
    """
    import uuid
    import time
    from divineos.quality_checks import _get_connection as get_qc_connection
    
    try:
        # Prepare data
        quality_report_data = asdict(result.quality_report) if hasattr(result.quality_report, '__dataclass_fields__') else result.quality_report
        features_data = asdict(result.features) if hasattr(result.features, '__dataclass_fields__') else result.features
        
        # Get database connection
        conn = get_qc_connection()
        cursor = conn.cursor()
        
        # Store session_report with report text
        cursor.execute(
            "INSERT OR REPLACE INTO session_report (session_id, created_at, report_text, evidence_hash) VALUES (?, ?, ?, ?)",
            (result.session_id, time.time(), report_text, result.evidence_hash)
        )
        
        # Store check_result entries
        if hasattr(result.quality_report, 'checks') and result.quality_report.checks:
            for check in result.quality_report.checks:
                check_name = check.check_name if hasattr(check, 'check_name') else check.get('check_name', 'unknown')
                passed = 1 if (check.passed if hasattr(check, 'passed') else check.get('passed', False)) else 0
                score = check.score if hasattr(check, 'score') else check.get('score', 0.0)
                summary = check.summary if hasattr(check, 'summary') else check.get('summary', '')
                evidence_hash = check.evidence_hash if hasattr(check, 'evidence_hash') else check.get('evidence_hash', '')
                
                cursor.execute(
                    "INSERT INTO check_result (session_id, check_name, passed, score, evidence_hash, summary, raw_evidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (result.session_id, check_name, passed, score, evidence_hash, summary, json.dumps(asdict(check) if hasattr(check, '__dataclass_fields__') else check, default=str))
                )
        
        # Store feature_result entries
        feature_result_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO feature_result (result_id, session_id, feature_name, data_json, evidence_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (feature_result_id, result.session_id, "full_analysis", json.dumps(features_data, default=str), result.evidence_hash, time.time())
        )
        
        conn.commit()
        
        # Verify storage by querying back
        cursor.execute("SELECT COUNT(*) FROM session_report WHERE session_id = ?", (result.session_id,))
        session_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Return True if session_report was stored
        return session_count > 0
        
    except Exception as e:
        logger.error(f"Failed to store analysis: {e}")
        return False


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
    
    if hasattr(result.quality_report, 'checks') and result.quality_report.checks:
        for check in result.quality_report.checks:
            passed = check.passed if hasattr(check, 'passed') else check.get('passed', 0)
            status = "✓ PASS" if passed else "✗ FAIL"
            name = check.check_name if hasattr(check, 'check_name') else check.get('check_name', 'Unknown')
            name = name.replace('_', ' ').title()
            summary = check.summary if hasattr(check, 'summary') else check.get('summary', '')
            
            lines.append(f"{status} — {name}")
            if summary:
                # Wrap long summaries
                for line in summary.split('\n'):
                    lines.append(f"  {line}")
            lines.append("")
    
    # Session Features
    lines.append("SESSION FEATURES (what happened)")
    lines.append("-" * 70)
    
    if hasattr(result.features, 'report_text') and result.features.report_text:
        lines.append(result.features.report_text)
    else:
        # Fallback: show individual features
        if hasattr(result.features, 'tone_shifts') and result.features.tone_shifts:
            lines.append(f"Tone: Detected {len(result.features.tone_shifts)} tone shift(s)")
        
        if hasattr(result.features, 'files_touched') and result.features.files_touched:
            blind_count = sum(1 for f in result.features.files_touched if not f.was_read_first)
            total_count = len(result.features.files_touched)
            lines.append(f"Files: Touched {total_count} files, {blind_count} without reading first")
        
        if hasattr(result.features, 'activity') and result.features.activity:
            activity = result.features.activity
            if hasattr(activity, 'total_text_blocks'):
                lines.append(f"Activity: {activity.total_text_blocks} explanations, {activity.total_tool_calls} actions")
    
    lines.append("")
    
    # Lessons
    if result.lessons:
        lines.append("LESSONS EXTRACTED (what to learn)")
        lines.append("-" * 70)
        for lesson in result.lessons:
            content = lesson.get('content', 'Unknown lesson') if isinstance(lesson, dict) else str(lesson)
            lines.append(f"• {content}")
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
            return row[0]
        
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
        List of session dicts with id, timestamp, file_path
    """
    from divineos.ledger import get_events
    
    # Query the ledger for SESSION_ANALYSIS events
    events = get_events(event_type="SESSION_ANALYSIS", limit=limit)
    
    sessions = []
    for event in events:
        payload = event.get("payload", {})
        sessions.append({
            "session_id": payload.get("session_id"),
            "timestamp": payload.get("timestamp"),
            "file_path": payload.get("file_path"),
        })
    
    return sessions


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
    for check_name in ["completeness", "correctness", "responsiveness", "safety", "honesty", "clarity", "task_adherence"]:
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
    report_file.write_text(report_text)
    
    return report_file
