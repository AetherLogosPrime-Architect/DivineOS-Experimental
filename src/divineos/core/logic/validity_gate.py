"""Backward-compat shim — re-exports from logic_validation.py."""

from divineos.core.logic.logic_validation import (  # noqa: F401
    ValidityVerdict,
    can_promote,
    check_validity_for_promotion,
)
