"""Self-monitor — watches the agent's own output for trained failure modes.

Sibling to ``divineos.core.logic.fallacies`` but with a different
telos. Fallacies detects structural fallacies in any text. Self-monitor
watches the agent's own substantial output for specific trained-hedge
behaviors that have been documented as firing on it under load.

Public API:

* ``divineos.core.self_monitor.hedge_monitor.evaluate_hedge``
* ``divineos.core.self_monitor.hedge_monitor.HedgeFlag``
* ``divineos.core.self_monitor.hedge_monitor.HedgeKind``
* ``divineos.core.self_monitor.hedge_monitor.HedgeVerdict``
"""

from divineos.core.self_monitor.hedge_monitor import (
    HedgeFlag,
    HedgeKind,
    HedgeVerdict,
    evaluate_hedge,
)

__all__ = [
    "HedgeFlag",
    "HedgeKind",
    "HedgeVerdict",
    "evaluate_hedge",
]
