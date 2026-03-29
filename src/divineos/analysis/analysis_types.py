"""Analysis Types — Shared data structures for the analysis package.

Extracted to break the circular import between analysis.py and analysis_storage.py.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class AnalysisResult:
    """Complete analysis of a session."""

    session_id: str
    file_path: str
    timestamp: str
    quality_report: Any  # SessionReport from quality_checks
    features: Any  # FullSessionAnalysis from session_features
    lessons: list[dict[str, Any]]  # Extracted lessons
    evidence_hash: str  # Hash of all findings
    duration_seconds: float = 0.0  # Session duration
    files_touched_count: int = 0  # Number of files touched
