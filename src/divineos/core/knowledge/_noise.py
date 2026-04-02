"""Backward-compat shim — all symbols now live in _text.py."""

from divineos.core.knowledge._text import (  # noqa: F401
    _CONVERSATIONAL_NOISE,
    _MIN_CONTENT_WORDS,
    _PRESCRIPTIVE_PATTERNS,
    _SYSTEM_ARTIFACT,
    _TEMPORAL_CONTENT_MARKERS,
    _has_prescriptive_signal,
    _has_temporal_markers,
    _is_extraction_noise,
    _is_pure_affirmation,
    _is_raw_quote_noise,
)
