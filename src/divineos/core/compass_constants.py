"""Shared constants for the moral-compass / rudder subsystems.

Hoisted from compass_rudder.py and moral_compass.py to break a
circular-import shape: moral_compass.py needs RUDDER_ACK_TAG and
JUSTIFICATION_WINDOW_SECONDS at substance-check / fire-validation time,
but importing compass_rudder there would create a cycle (compass_rudder
imports observation primitives that originate in moral_compass).

Both modules previously kept private duplicates with inline comments
flagging the drift risk: change one without the other and validation
silently desyncs from the rudder. This module is the single source of
truth so the comment becomes structural.
"""

from __future__ import annotations

RUDDER_ACK_TAG = "rudder-ack"
"""Tag required on a compass observation for it to count as a rudder
response. Distinguishes intentional acknowledgement of the drift alert
from background observations. Unguessable by accident — typo becomes
a no-op."""

JUSTIFICATION_WINDOW_SECONDS = 5 * 60
"""Recent-decide / fire-validation lookback window, in seconds."""
