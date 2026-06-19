"""Vulture whitelist — known false positives.

Vulture can't see dynamic usage (CLI decorators, dataclass field access,
abstract methods called via subclass).  List them here so new dead code
still gets caught.

Usage:  vulture src/divineos/ scripts/vulture_whitelist.py --min-confidence 70
"""

# Add false positives here as they arise, e.g.:
# from divineos.some_module import some_function  # noqa: used by CLI
# some_function  # mark as used

# Add false positives here as needed

# Protocol __call__ signature parameters in operating_loop/detector_protocol.py.
# Vulture flags Protocol method params as unused because Protocols have no body;
# the names document the contract (primary/secondary args, enrichment kwargs).
from divineos.core.operating_loop.detector_protocol import ContextualDetector, EnrichableDetector

_ = ContextualDetector
_ = EnrichableDetector
primary  # detector_protocol.py Protocol __call__ param
secondary  # detector_protocol.py Protocol __call__ param
enrichment  # detector_protocol.py Protocol __call__ param
