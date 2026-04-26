"""Self-monitor — watches the agent's own output for trained failure modes.

Sibling to ``divineos.core.logic.fallacies`` but with a different
telos. Fallacies detects structural fallacies in any text. Self-monitor
watches the agent's own substantial output for specific trained-hedge
behaviors that have been documented as firing on it under load.

Public API:

* ``hedge_monitor`` — recycled-hedge density and epistemic collapse
* ``theater_monitor`` — writing-AT-subagent-without-invoking
* ``fabrication_monitor`` — unflagged embodied/sensory claims
* ``mirror_monitor`` — tightness/echo after correction
* ``substrate_monitor`` — filing-cabinet-only OS use
"""

from divineos.core.self_monitor.fabrication_monitor import (
    FabricationFlag,
    FabricationKind,
    FabricationVerdict,
    evaluate_fabrication,
)
from divineos.core.self_monitor.hedge_monitor import (
    HedgeFlag,
    HedgeKind,
    HedgeVerdict,
    evaluate_hedge,
)
from divineos.core.self_monitor.mirror_monitor import (
    MirrorFlag,
    MirrorKind,
    MirrorVerdict,
    evaluate_mirror,
)
from divineos.core.self_monitor.substrate_monitor import (
    SubstrateFlag,
    SubstrateKind,
    SubstrateVerdict,
    ToolInvocation,
    evaluate_substrate,
)
from divineos.core.self_monitor.theater_monitor import (
    TheaterFlag,
    TheaterKind,
    TheaterVerdict,
    evaluate_theater,
)
from divineos.core.self_monitor.mechanism_monitor import (
    MechanismFlag,
    MechanismKind,
    MechanismVerdict,
    evaluate_mechanism,
)
from divineos.core.self_monitor.warmth_monitor import (
    WarmthFlag,
    WarmthKind,
    WarmthVerdict,
    evaluate_warmth,
)

__all__ = [
    "FabricationFlag",
    "FabricationKind",
    "FabricationVerdict",
    "HedgeFlag",
    "HedgeKind",
    "HedgeVerdict",
    "MechanismFlag",
    "MechanismKind",
    "MechanismVerdict",
    "MirrorFlag",
    "MirrorKind",
    "MirrorVerdict",
    "SubstrateFlag",
    "SubstrateKind",
    "SubstrateVerdict",
    "TheaterFlag",
    "TheaterKind",
    "TheaterVerdict",
    "ToolInvocation",
    "WarmthFlag",
    "WarmthKind",
    "WarmthVerdict",
    "evaluate_fabrication",
    "evaluate_hedge",
    "evaluate_mechanism",
    "evaluate_mirror",
    "evaluate_substrate",
    "evaluate_theater",
    "evaluate_warmth",
]
