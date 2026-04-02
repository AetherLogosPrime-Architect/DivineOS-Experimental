"""Backward-compat shim — real implementation lives in affect.py."""

from divineos.core.affect import (  # noqa: F401
    _affect_row_to_dict,
    count_affect_entries,
    describe_affect,
    get_affect_history,
    get_affect_summary,
    get_recent_affect,
    init_affect_log,
    log_affect,
)
