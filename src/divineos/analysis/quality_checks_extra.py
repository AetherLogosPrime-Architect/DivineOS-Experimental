"""Quality Checks (Extra) — Backward-compatibility shim.

All symbols have been merged into quality_checks.py.
This module re-exports them for any external imports.
"""

from divineos.analysis.quality_checks import (  # noqa: F401
    JARGON_TERMS,
    _generate_report_text,
    check_clarity,
    check_task_adherence,
)
