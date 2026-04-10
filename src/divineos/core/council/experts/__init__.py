"""Expert wisdom profiles — how great minds actually think.

Each module exports a create_*_wisdom() function that returns
an ExpertWisdom instance encoding that thinker's methodology.
"""

from divineos.core.council.experts.aristotle import create_aristotle_wisdom
from divineos.core.council.experts.beer import create_beer_wisdom
from divineos.core.council.experts.dekker import create_dekker_wisdom
from divineos.core.council.experts.deming import create_deming_wisdom
from divineos.core.council.experts.dennett import create_dennett_wisdom
from divineos.core.council.experts.dijkstra import create_dijkstra_wisdom
from divineos.core.council.experts.feynman import create_feynman_wisdom
from divineos.core.council.experts.godel import create_godel_wisdom
from divineos.core.council.experts.hinton import create_hinton_wisdom
from divineos.core.council.experts.hofstadter import create_hofstadter_wisdom
from divineos.core.council.experts.holmes import create_holmes_wisdom
from divineos.core.council.experts.jacobs import create_jacobs_wisdom
from divineos.core.council.experts.kahneman import create_kahneman_wisdom
from divineos.core.council.experts.lovelace import create_lovelace_wisdom
from divineos.core.council.experts.meadows import create_meadows_wisdom
from divineos.core.council.experts.minsky import create_minsky_wisdom
from divineos.core.council.experts.norman import create_norman_wisdom
from divineos.core.council.experts.pearl import create_pearl_wisdom
from divineos.core.council.experts.peirce import create_peirce_wisdom
from divineos.core.council.experts.schneier import create_schneier_wisdom
from divineos.core.council.experts.shannon import create_shannon_wisdom
from divineos.core.council.experts.taleb import create_taleb_wisdom
from divineos.core.council.experts.turing import create_turing_wisdom
from divineos.core.council.experts.wittgenstein import create_wittgenstein_wisdom
from divineos.core.council.experts.yudkowsky import create_yudkowsky_wisdom

__all__ = [
    "create_aristotle_wisdom",
    "create_beer_wisdom",
    "create_dekker_wisdom",
    "create_deming_wisdom",
    "create_dennett_wisdom",
    "create_dijkstra_wisdom",
    "create_feynman_wisdom",
    "create_godel_wisdom",
    "create_hinton_wisdom",
    "create_hofstadter_wisdom",
    "create_holmes_wisdom",
    "create_jacobs_wisdom",
    "create_kahneman_wisdom",
    "create_lovelace_wisdom",
    "create_meadows_wisdom",
    "create_minsky_wisdom",
    "create_norman_wisdom",
    "create_pearl_wisdom",
    "create_peirce_wisdom",
    "create_schneier_wisdom",
    "create_shannon_wisdom",
    "create_taleb_wisdom",
    "create_turing_wisdom",
    "create_wittgenstein_wisdom",
    "create_yudkowsky_wisdom",
]
