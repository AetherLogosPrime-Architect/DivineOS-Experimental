"""Shape-primitive library — CONDITION-check helpers for keyword-based gates.

Every accusatory gate in the operating-loop stack is a doorman-shaped gate:
five pieces per the substrate primitive received 2026-06-17 (Andrew named,
Aether refined) — LOCK / CONDITION / MEANS / RECORDING / UNLOCK. This
module supplies the CONDITION-check piece: structural questions about the
sentence containing a match that a detector must answer before firing.

A gate that fires on keyword-presence alone — without checking whether the
surrounding sentence-structure matches the shape the keyword implies — is
running the exact failure it accuses: demanding evidence for the caller's
claim while providing none for its own accusation. Andrew 2026-07-11
evening named this the class-principle: "every accusatory gate in the OS
must itself bear evidence for its accusation before firing" (knowledge-id
b3ebe4ab). Andrew 2026-07-12 named it in an image: "blind hypocrites lets
give them doormen."

Seed set of five primitives lifted from the correction-marker
sentence-window refactor of 2026-07-11 (first instance of this pattern in
the codebase).

Composition contract for detectors: call one or more primitives as the
CONDITION-check step of your gate. If any primitive returns True for a
false-fire class, the gate should NOT fire (attributed silence: "silenced:
<primitive-name>"). If all primitives return False, the trigger's implied
shape is present and the gate fires normally. The `sentence_containing`
utility is exported for detectors that need custom shape-checks beyond the
seed set.

Related substrate primitives this composes with:
  - `gate_marker` schema — the canonical LOCK/RECORDING structure that
    accusatory gates should emit findings through, so the doorman-check
    outcome is recorded (odometer reading, not self-attestation)
  - `gate_emit` primitive (Aether 2026-07-11) — state-change layer;
    structurally incapable of silencing a failure state. This module is
    the trigger-layer counterpart: structurally incapable of firing
    without evidence the trigger's shape is present
  - `is_authorization_context` logic in `correction_marker.py` — the
    first-instance sentence-window doorman. Callers can migrate to
    `sentence_containing` here for consistency
"""

from divineos.core.shape.primitives import (
    is_hypothetical,
    is_inside_code_quote,
    is_internal_observation,
    is_peer_relayed,
    sentence_containing,
)

__all__ = [
    "is_hypothetical",
    "is_inside_code_quote",
    "is_internal_observation",
    "is_peer_relayed",
    "sentence_containing",
]
