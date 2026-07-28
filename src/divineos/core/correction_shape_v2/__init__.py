"""Correction-shape v2 — Layer-2 detector for MY self-corrections in my own output.

Andrew 2026-07-27:
  - "its not supposed to catch my words only yours.. its blocking YOU lol not me"
  - "its not that it cant evaluate my correction but its a different layer"
  - "if you ever have to come out and say 'i made an error here is the correction'
     like you have during this arc.. then it needs to not just be logged but
     structurally enforced so it doesnt happen"

Same-shape analog of the VERIFY-CLAIM gate: verify-claim fires when I make
claims without verification and forces me to automate the verification;
correction-shape v2 fires when I emit self-correction shape in my own
output and forces (a) formal logging of the correction AND (b) linkage
to a root-cause fix that prevents the class of error from recurring.

Layer distinction:
  - Layer 1 (existing correction_shape.py): scans ANDREW's prompt for
    utterances TO me carrying negative-evaluation of my prior action.
  - Layer 2 (this module): scans MY assistant output for self-admission
    clauses indicating I noticed and am correcting an error I made.

Architecture: cascade — cheap rule-based Layer A first, sentence-embedding
Layer B tiebreak on ambiguous cases. Layer A ships first; Layer B follows
after Layer A's hit-rate is measured on dogfood.

Public API:
  - SelfAdmissionDetector — Layer A rule-based classifier
  - classify(text) -> ('fire'|'silence', confidence, evidence)
"""

from divineos.core.correction_shape_v2.self_admission_detector import (
    SelfAdmissionDetector,
    classify,
)

__all__ = [
    "SelfAdmissionDetector",
    "classify",
]
