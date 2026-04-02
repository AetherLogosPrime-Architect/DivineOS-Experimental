"""Backward-compat shim — re-exports from logic_validation.py."""

from divineos.core.logic.logic_validation import (  # noqa: F401
    check_defeat_pattern,
    record_defeat_lesson,
    scan_defeated_only_entries,
)
