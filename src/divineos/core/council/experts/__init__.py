"""Expert wisdom profiles — how great minds actually think.

Each module exports a create_*_wisdom() function that returns
an ExpertWisdom instance encoding that thinker's methodology.
"""

from divineos.core.council.experts.feynman import create_feynman_wisdom
from divineos.core.council.experts.holmes import create_holmes_wisdom
from divineos.core.council.experts.pearl import create_pearl_wisdom

__all__ = [
    "create_feynman_wisdom",
    "create_holmes_wisdom",
    "create_pearl_wisdom",
]
