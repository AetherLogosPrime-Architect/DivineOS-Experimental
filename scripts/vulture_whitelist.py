"""Vulture whitelist — known false positives.

Vulture can't see dynamic usage (CLI decorators, dataclass field access,
abstract methods called via subclass).  List them here so new dead code
still gets caught.

Usage:  vulture src/divineos/ scripts/vulture_whitelist.py --min-confidence 70
"""

# Add false positives here as they arise, e.g.:
# from divineos.some_module import some_function  # noqa: used by CLI
# some_function  # mark as used
