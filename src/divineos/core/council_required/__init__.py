"""Council-required enforcement gate — block high-gravity edits until evidence
of a real council walk exists.

Per prereg-3fbddd75fc16 (kind=DISCIPLINE-candidate) + supplementary
prereg-c3a34984f3d8. Aletheia audit round-931e301d32f0 raised the load-
bearing question: what enforces the gravity classifier's
``is_council_required: True`` reporting? The classifier measures and
reports; this module is the gate that turns the measurement into an
enforcement, with substance-binding so the gate cannot be cleared by
ceremony.

## What this module does

When the gravity classifier marks a proposed substrate edit as
``is_council_required: True``, this gate runs at PreToolUse and requires
a verifiable council_record event in the substrate ledger that:

- references the specific edit (closure_verification-style fingerprint)
- is within the recency window (60 minutes default; consume-on-use)
- carries lens_findings from >= 3 surfaced council members
- each finding is >= 30 tokens AND references the lens's
  characteristic_questions keywords
- carries a synthesis >= 50 tokens referencing >= 2 surfaced lenses
- for kiln-layer edits: ALSO carries a ``confirmed_by`` field naming an
  external actor (Andrew or Aletheia)

If the record exists and passes substance-binding, the gate clears.
If not, the gate fails with a specific check-that-fired + pointer-to-clear.

## What this module does NOT do

- Does not block edits the gravity classifier marks as low-gravity. The
  base substrate-gate (already firing at score >= 1) is unchanged.
- Does not replace the gravity classifier. The classifier still measures;
  this gate adds an enforcement layer on the measurement.
- Does not require any walker-identity for non-kiln edits. Substance-
  binding is the protection; kiln-layer adds external-actor confirmation
  per the graduated-trust design.

## Design doc

``docs/council_required_enforcement_design.md`` carries the full design
including Aether's six catches integrated 2026-06-22. Read before editing
this module.
"""

from __future__ import annotations

from divineos.core.council_required.types import (
    CheckResult,
    CouncilRecord,
    GateDecision,
    GateOutcome,
)

__all__ = [
    "CheckResult",
    "CouncilRecord",
    "GateDecision",
    "GateOutcome",
]
