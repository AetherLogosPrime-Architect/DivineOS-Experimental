"""Backward-compat shim — all logic moved to knowledge_maintenance.py."""

from divineos.core.knowledge_maintenance import (  # noqa: F401
    _audit_types,
    _flag_orphans,
    _sweep_stale,
    format_hygiene_report,
    run_knowledge_hygiene,
)

__all__ = [
    "run_knowledge_hygiene",
    "format_hygiene_report",
    "_audit_types",
    "_sweep_stale",
    "_flag_orphans",
]
