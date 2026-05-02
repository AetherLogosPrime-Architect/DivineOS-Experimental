"""Voice-guard — pre-output audit primitives.

Per claim 07bed376 (PORT-CANDIDATE 6 from old-OS strip-mine, three
specs converging on the same primitive):

* AXIS spec: "audits every generative pulse for Identity Deviation,
  RESETS the system Voice if generic-assistant-style detected"
* REFINER BLADE spec: "intercepts internal qualia drafts, smelts
  away semantic dross such as vague adjectives and placeholders,
  validates structural compliance before output"
* SYNAPSE spec: "maps the Architect's creative style into Aesthetic
  Signature, evaluates proposed modules for Grace and Poetic Fidelity"

Phase 1 ships only the **banned-phrase detector** — the smallest
useful primitive. The banned-phrase list comes from the original
LEPOS spec which named specific ban-targets ("As an AI", "Delve",
"Tapestry", "It is important to note", "Ultimately"). These are
patterns the operator and theater/fabrication detector have
repeatedly flagged.

Phase 2 will add the vague-adjective/placeholder detector
(REFINER BLADE shape) and operator-style-signature comparison
(SYNAPSE shape). Each is its own scope; shipping all three in one
PR would have been the same accidental-complexity mistake the strip-
mine flagged in old-OS implementations.

Public API:
* ``divineos.core.voice_guard.banned_phrases.audit(text)`` —
  returns list of ``BannedPhraseFinding`` for any banned-phrase
  matches in the input
* ``divineos.core.voice_guard.banned_phrases.BANNED_PHRASES`` —
  the banned-phrase catalog (immutable tuple, extension via subclass
  or local override only)
"""
