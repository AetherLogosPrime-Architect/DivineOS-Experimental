"""Backward-compat shim — real implementation lives in affect.py."""

from divineos.core.affect import (  # noqa: F401
    compute_affect_modifiers,
    detect_praise_chasing,
    format_affect_feedback,
    get_session_affect_context,
)
