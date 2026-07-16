"""Vulture whitelist — known false positives.

Vulture can't see dynamic usage (CLI decorators, dataclass field access,
abstract methods called via subclass).  List them here so new dead code
still gets caught.

Usage:  vulture src/divineos/ scripts/vulture_whitelist.py --min-confidence 70
"""

# Add false positives here as they arise, e.g.:
# from divineos.some_module import some_function  # noqa: F401 — used by CLI
# some_function  # mark as used

# Add false positives here as needed

# Protocol __call__ signature parameters in operating_loop/detector_protocol.py.
# Vulture flags Protocol method params as unused because Protocols have no body;
# the names document the contract (primary/secondary args, enrichment kwargs).
from divineos.core.operating_loop.detector_protocol import ContextualDetector, EnrichableDetector

_ = ContextualDetector
_ = EnrichableDetector
primary  # noqa: F821 — detector_protocol.py Protocol __call__ param (vulture whitelist by name)
secondary  # noqa: F821 — detector_protocol.py Protocol __call__ param (vulture whitelist by name)
enrichment  # noqa: F821 — detector_protocol.py Protocol __call__ param (vulture whitelist by name)

# Abstract-method signature parameters in evidence_bearing_stop_gate.py.
# Same class of false-positive as Protocol params above — abstract methods
# have no body; the names document the contract that concrete subclasses
# MUST implement. If removed, subclasses would inherit a wrong signature.
from divineos.hooks.evidence_bearing_stop_gate import (
    CrossTurnScan,
    EvidenceBearingStopGate,
    IntraTurnIntercept,
)

_ = EvidenceBearingStopGate
_ = IntraTurnIntercept
_ = CrossTurnScan
clearance  # noqa: F821 — record_clearance abstract-method param (vulture whitelist by name)
accumulated_state  # noqa: F821 — CrossTurnScan.scan abstract-method param
just_emitted_text  # noqa: F821 — CrossTurnScan.scan abstract-method param
