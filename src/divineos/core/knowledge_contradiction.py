"""Backward-compat shim — all logic moved to knowledge_maintenance.py."""

from divineos.core.knowledge_maintenance import (  # noqa: F401
    ContradictionMatch,
    increment_contradiction_count,
    resolve_contradiction,
    scan_for_contradictions,
)

__all__ = [
    "ContradictionMatch",
    "increment_contradiction_count",
    "resolve_contradiction",
    "scan_for_contradictions",
]
