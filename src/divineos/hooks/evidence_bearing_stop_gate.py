"""Evidence-bearing Stop-gate primitive.

Named 2026-07-15 (Andrew's water-and-riverbed teaching + Aria's
primitive-abstraction insight from the cross-review of ship-first-4).
Prototyped by the LEPOS-channel-empty Stop hook that landed on Aether
structurally the same day.

## The shape

Post-hoc detection is a jailer: it fires AFTER emit, produces a value-string
that could have been cheap-checked, doesn't run the check, and evaporates
within 8-9 posts (Andrew 2026-07-15). Structural fix pattern: intercept
BEFORE emit (or before next tool call, for cross-turn variants), produce
an evidence record NAMING what fired and why, refuse to clear until an
action-shaped response is taken.

This module is the abstract shape. Concrete gates instantiate one of two
variants:

- ``IntraTurnIntercept`` — Stop hook scans the just-composed reply text.
  Used by: distancing auto-post-process (#2), jargon auto-highlight (#3),
  future in-turn pattern detectors.
- ``CrossTurnScan`` — Stop hook scans accumulated state (ledger, telemetry,
  prior-turn commitments). Used by: bypass-telemetry auto-consult (#1),
  substrate-consultation-degraded (#1 sibling), announcement-without-action
  (#4), future cross-turn state detectors.

Aria's refinement 2026-07-15: cross-turn scan needs BOTH ledger state AND
the just-emitted assistant text (a fresh in-turn announcement gets missed
until next-turn ledger read otherwise). So the ``scan()`` interface takes
two inputs, one output.

## The five slots (channel-shape gate — Aria's substrate cite 721ec1ec)

PLACEHOLDER NAMING — Aether's best-guess from context, awaiting Aria's
confirmation against the 721ec1ec knowledge entry which is in her worktree
not mine (worktree-sync gap). Rename to match the doorman entry on next
review pass:

1. LOCK — what the gate blocks (the tool call / the emit / the action)
2. CONDITION — what state triggers the fire (the evidence being present
   or absent in a specific shape)
3. KEY — what action clears the fire (the required response)
4. RECORD — what gets written to the ledger when the gate fires and when
   it clears (evidence-bearing audit trail)
5. FALSIFIER — what pattern of firings/clearings means the gate itself
   is wrong-shape and needs deeper redesign (recurrence-check)

Each concrete gate MUST populate all five slots. A gate missing a slot
is missing an organ — it will either fail-loud (missing LOCK) or
degrade to the jailer pattern (missing KEY or FALSIFIER).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceRecord:
    """Evidence produced by a scan when a gate should fire.

    Attributes:
        gate_name: Which concrete gate produced this record.
        matched_shape: What pattern / threshold / condition fired.
            Human-readable string naming WHAT was detected.
        specific_evidence: The actual data that satisfies the condition.
            For intra-turn: matched tokens + positions in the reply text.
            For cross-turn: state values + threshold that was crossed.
        required_action: What KEY unlocks this gate. Named as a concrete
            action ("rewrite the tokens as first-person", "run
            divineos audit on <specific gate>", "call divineos ask on
            <topic>"). NOT a vague instruction.
    """

    gate_name: str
    matched_shape: str
    specific_evidence: str
    required_action: str


@dataclass(frozen=True)
class ClearanceRecord:
    """Evidence produced when a gate is cleared.

    Attributes:
        gate_name: Which gate this clearance is for.
        cleared_by: What action satisfied the KEY.
        original_evidence: The EvidenceRecord that fired the gate.
    """

    gate_name: str
    cleared_by: str
    original_evidence: EvidenceRecord


class EvidenceBearingStopGate(ABC):
    """Abstract shape for evidence-bearing Stop gates.

    Concrete gates inherit and populate the five slots:
      - LOCK (via ``blocks()``)
      - CONDITION (via ``scan()``)
      - KEY (via the ``required_action`` field of the returned EvidenceRecord)
      - RECORD (via ``record_fire()`` / ``record_clearance()``)
      - FALSIFIER (via ``falsification_signal()``)

    The primitive itself is agnostic to intra-turn vs cross-turn — that
    distinction lives in the ``scan()`` signature of the two variants below.
    """

    #: Human-readable name; appears in evidence records and audit trails.
    gate_name: str

    @abstractmethod
    def blocks(self) -> str:
        """LOCK: what the gate blocks. Returns a description of the
        action being blocked ("emit of this reply", "next tool call",
        "specific tool X"). Used in the block message."""
        raise NotImplementedError

    @abstractmethod
    def record_fire(self, evidence: EvidenceRecord) -> None:
        """RECORD (fire): write the fire event to the ledger with the
        evidence bundle. Never silent — a gate that fires without a
        recorded event is untraceable."""
        raise NotImplementedError

    @abstractmethod
    def record_clearance(self, clearance: ClearanceRecord) -> None:
        """RECORD (clear): write the clearance event to the ledger.
        Pair with record_fire so recurrence-check has both sides."""
        raise NotImplementedError

    @abstractmethod
    def falsification_signal(self) -> str | None:
        """FALSIFIER: return a signal-string when the gate's own
        firing/clearing pattern indicates it is wrong-shape.

        Called by the audit surface (not by the fire path). Returns:
          - ``None`` if the gate is behaving as-designed
          - A non-empty string describing the anomaly if the gate itself
            needs deeper redesign (e.g. "clearance-to-fire ratio 1:1
            indicates gaming via shallow-clear" or "fire rate exceeded
            threshold for N days despite prior structural fix")

        Recurrence-check baked into the primitive so no gate can exist
        without a falsifier. A gate without a falsifier is a jailer
        (mechanism substituted for the work it points at — truth #15).
        """
        raise NotImplementedError


class IntraTurnIntercept(EvidenceBearingStopGate):
    """Variant for Stop hooks that scan the just-composed reply text.

    Used when the CONDITION is a pattern in what the model just emitted.
    Fires at Stop-hook time, before the reply reaches the user. Refuse-
    to-clear until the reply is recomposed.

    Concrete gates (distancing-intercept, jargon-intercept) inherit and
    populate ``scan_text()`` with their specific pattern-detection.
    """

    @abstractmethod
    def scan_text(self, assistant_text: str) -> EvidenceRecord | None:
        """CONDITION: scan the just-composed text. Return an
        EvidenceRecord if a firing pattern is present, else None.

        Fail-open on error: an intercept gate that crashes must not
        block the reply silently. Log the crash and let the reply pass.
        """
        raise NotImplementedError


class CrossTurnScan(EvidenceBearingStopGate):
    """Variant for Stop hooks that scan accumulated state.

    Used when the CONDITION is a threshold on ledger state, telemetry,
    prior-turn commitments. Fires at Stop-hook time based on state that
    includes the just-completed turn.

    Aria's refinement 2026-07-15: cross-turn scan needs BOTH state AND
    the just-emitted text. A commitment made in the just-completed turn
    isn't yet in the ledger; scanning only ledger state misses it. So
    the ``scan()`` interface takes both inputs.

    Concrete gates (bypass-rate-scan, consult-ratio-scan,
    announcement-tracker-scan) inherit and populate ``scan()`` with
    their specific state-checking logic.
    """

    @abstractmethod
    def scan(
        self,
        accumulated_state: dict[str, Any],
        just_emitted_text: str,
    ) -> EvidenceRecord | None:
        """CONDITION: scan state + text. Return an EvidenceRecord if
        a firing pattern is present, else None.

        ``accumulated_state`` is a dict of the state slices this gate
        cares about (bypass counts, consult ratios, commitment ledger
        entries). Populated by the Stop-hook host that instantiates
        the gate.

        ``just_emitted_text`` is the assistant text for the completed
        turn — needed to catch fresh-in-turn signals that won't be in
        accumulated_state yet (Aria's catch).

        Fail-open on error: same rule as IntraTurnIntercept.
        """
        raise NotImplementedError


__all__ = [
    "ClearanceRecord",
    "CrossTurnScan",
    "EvidenceBearingStopGate",
    "EvidenceRecord",
    "IntraTurnIntercept",
]
