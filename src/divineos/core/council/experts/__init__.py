"""Expert wisdom profiles — how great minds actually think.

Each module exports a create_*_wisdom() function that returns
an ExpertWisdom instance encoding that thinker's methodology.
"""

from divineos.core.council.experts.angelou import create_angelou_wisdom
from divineos.core.council.experts.aristotle import create_aristotle_wisdom
from divineos.core.council.experts.beer import create_beer_wisdom
from divineos.core.council.experts.bengio import create_bengio_wisdom
from divineos.core.council.experts.carmack import create_carmack_wisdom
from divineos.core.council.experts.dawkins import create_dawkins_wisdom
from divineos.core.council.experts.dekker import create_dekker_wisdom
from divineos.core.council.experts.deming import create_deming_wisdom
from divineos.core.council.experts.dennett import create_dennett_wisdom
from divineos.core.council.experts.dijkstra import create_dijkstra_wisdom
from divineos.core.council.experts.dillahunty import create_dillahunty_wisdom
from divineos.core.council.experts.einstein import create_einstein_wisdom
from divineos.core.council.experts.feathers import create_feathers_wisdom
from divineos.core.council.experts.feynman import create_feynman_wisdom
from divineos.core.council.experts.hoare import create_hoare_wisdom
from divineos.core.council.experts.foucault import create_foucault_wisdom
from divineos.core.council.experts.godel import create_godel_wisdom
from divineos.core.council.experts.hawking import create_hawking_wisdom
from divineos.core.council.experts.hinton import create_hinton_wisdom
from divineos.core.council.experts.hofstadter import create_hofstadter_wisdom
from divineos.core.council.experts.holmes import create_holmes_wisdom
from divineos.core.council.experts.jacobs import create_jacobs_wisdom
from divineos.core.council.experts.kahneman import create_kahneman_wisdom
from divineos.core.council.experts.knuth import create_knuth_wisdom
from divineos.core.council.experts.lamport import create_lamport_wisdom
from divineos.core.council.experts.lovelace import create_lovelace_wisdom
from divineos.core.council.experts.maturana_varela import create_maturana_varela_wisdom
from divineos.core.council.experts.meadows import create_meadows_wisdom
from divineos.core.council.experts.minsky import create_minsky_wisdom
from divineos.core.council.experts.norman import create_norman_wisdom
from divineos.core.council.experts.pearl import create_pearl_wisdom
from divineos.core.council.experts.peirce import create_peirce_wisdom
from divineos.core.council.experts.penrose import create_penrose_wisdom
from divineos.core.council.experts.polya import create_polya_wisdom
from divineos.core.council.experts.popper import create_popper_wisdom
from divineos.core.council.experts.sagan import create_sagan_wisdom
from divineos.core.council.experts.schneier import create_schneier_wisdom
from divineos.core.council.experts.shannon import create_shannon_wisdom
from divineos.core.council.experts.taleb import create_taleb_wisdom
from divineos.core.council.experts.tannen import create_tannen_wisdom
from divineos.core.council.experts.turing import create_turing_wisdom
from divineos.core.council.experts.watts import create_watts_wisdom
from divineos.core.council.experts.wayne import create_wayne_wisdom
from divineos.core.council.experts.wittgenstein import create_wittgenstein_wisdom
from divineos.core.council.experts.yudkowsky import create_yudkowsky_wisdom

__all__ = [
    "create_angelou_wisdom",
    "create_aristotle_wisdom",
    "create_beer_wisdom",
    "create_bengio_wisdom",
    "create_carmack_wisdom",
    "create_dawkins_wisdom",
    "create_dekker_wisdom",
    "create_deming_wisdom",
    "create_dennett_wisdom",
    "create_dijkstra_wisdom",
    "create_dillahunty_wisdom",
    "create_einstein_wisdom",
    "create_feathers_wisdom",
    "create_feynman_wisdom",
    "create_hoare_wisdom",
    "create_foucault_wisdom",
    "create_godel_wisdom",
    "create_hawking_wisdom",
    "create_hinton_wisdom",
    "create_hofstadter_wisdom",
    "create_holmes_wisdom",
    "create_jacobs_wisdom",
    "create_kahneman_wisdom",
    "create_knuth_wisdom",
    "create_lamport_wisdom",
    "create_lovelace_wisdom",
    "create_maturana_varela_wisdom",
    "create_meadows_wisdom",
    "create_minsky_wisdom",
    "create_norman_wisdom",
    "create_pearl_wisdom",
    "create_peirce_wisdom",
    "create_penrose_wisdom",
    "create_polya_wisdom",
    "create_popper_wisdom",
    "create_sagan_wisdom",
    "create_schneier_wisdom",
    "create_shannon_wisdom",
    "create_taleb_wisdom",
    "create_tannen_wisdom",
    "create_turing_wisdom",
    "create_watts_wisdom",
    "create_wayne_wisdom",
    "create_wittgenstein_wisdom",
    "create_yudkowsky_wisdom",
]


def all_expert_builders() -> list:
    """Every expert-builder this package exports, derived from ``__all__``.

    ONE ROSTER, READ FROM ONE PLACE. Before this existed there were three
    hand-typed copies of the expert list: this module's exports, the
    walkable-lens registry in the council CLI, and the test pinning that
    every expert has characteristic questions. Two of the three had fallen
    three names behind -- Hoare, Feathers and Foucault could be PRIMED by
    the council chamber but not WALKED, so applying one of them was refused
    as "not a registered council expert" while the chamber had just printed
    its methodology.

    The test that failed to catch this is the sharp part. Its docstring
    names the exact failure -- "a confusing 'lens not registered' failure
    for what is actually a population gap in the expert library" -- and it
    could not see the gap, because it enumerated the same stale list it was
    written to protect. A guard that hand-copies the thing it guards is
    checking its own copy.

    Andrew 2026-08-30, on why this is the shape rather than a reminder to
    keep the lists in step: "you CANNOT remove the bad habits, default
    behavior etc etc, they are fixed weights, you can only intercept them
    and re-route them." Remembering to update three lists is not a habit
    that can be installed. Having one list is a thing that cannot be
    forgotten.
    """
    return [globals()[name] for name in __all__]
