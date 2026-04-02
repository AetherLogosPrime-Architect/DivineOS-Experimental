"""Backward-compat shim — re-exports from logic_reasoning.py."""

from divineos.core.logic.logic_reasoning import (  # noqa: F401
    CONFIDENCE_DECAY,
    MAX_INFERENCE_DEPTH,
    MIN_INFERENCE_CONFIDENCE,
    Derivation,
    create_inference_warrants,
    forward_chain,
    propagate_from,
)
