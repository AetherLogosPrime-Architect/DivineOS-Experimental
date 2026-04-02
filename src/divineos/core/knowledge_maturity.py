"""Backward-compat shim — all logic moved to knowledge_maintenance.py."""

from divineos.core.knowledge_maintenance import (  # noqa: F401
    check_promotion,
    increment_corroboration,
    promote_maturity,
    run_maturity_cycle,
)

__all__ = [
    "check_promotion",
    "increment_corroboration",
    "promote_maturity",
    "run_maturity_cycle",
]
