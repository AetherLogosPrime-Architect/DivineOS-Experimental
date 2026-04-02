"""Backward-compat shim — re-exports from logic_validation.py."""

from divineos.core.logic.logic_validation import (  # noqa: F401
    Inconsistency,
    check_consistency,
    check_local_consistency,
    check_transitive_consistency,
    register_contradiction,
)
