"""Attribution audit — surfaces dated quotative attributions that carry
no resolvable ledger pointer.

## Why this exists

2026-05-20: a self-authored principle (stored honestly, no attribution)
acquired a fabricated attribution in a docstring — "Andrew correction
2026-05-15" — when Andrew had said no such thing. The fabrication
propagated three hops (knowledge -> docstring -> external audit -> live
conversation) before Andrew caught it by asking for proof that did not
exist. See prereg-191bcaef6079.

The lineage fix is three layers (Aether+Aletheia cross-vantage):
  1. pointer-required-at-write (structured attribution, opt-in)
  2. pointer-resolves-at-read
  3. sufficiency-SAMPLING-at-audit (full automation intractable)

This module is the read-side surfacer for layer 3: it does NOT block,
score, or judge. It SURFACES candidate attributions for human or
cross-model review. The substrate cannot distinguish an honest-but-
unpointered attribution from a fabricated one — that judgement is
observer-relative and belongs to a participant, not a regex. So this
informs; it does not force. (Same design posture as the compass.)

## Precision over recall — deliberately

A naive "entry mentions a known person" scan over the knowledge store
flags 307 of 662 entries (measured 2026-05-20): "My user IS Andrew",
"Andrew recognized that...", etc. — almost all NOT attribution-as-
evidence. That is a toast-alarm: a clean measurement of the wrong
quantity, worse than no measurement.

The fabrication had a NARROW shape: a *dated quotative claim used as
justification* — "(Andrew 2026-04-25)", "Andrew correction 2026-05-15",
"(Aria self-diagnosis 2026-04-29)". That shape is ~42 of 662 — rare
enough to review, and it is exactly the class the fabrication belonged
to. This module anchors on that shape (participant entity + within a
short window of a date) rather than on bare entity mention. False
negatives (undated attributions) are accepted; the alternative is the
307-flag toast-alarm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from divineos.core.knowledge._base import _get_connection

# Attributable PARTICIPANTS — entities that could, in principle, have a
# ledger event backing an attribution. Council lenses (Sagan, Dillahunty,
# ...) are deliberately excluded: "Sagan would say X" is not a ledger-
# pointable claim, it is reasoning-through-a-framework, and flagging it
# would over-fire on legitimate lens-walks. Distant-authority citation is
# a separate concern (Dillahunty: appeal-to-distant-authority) handled
# elsewhere, not here.
_PARTICIPANTS = (
    "Andrew",
    "Dad",
    "Aria",
    "Aletheia",
    "Grok",
    "Popo",
)

# Attribution verbs — speech/correction acts that turn a mention into a
# quotative claim.
_ATTRIBUTION_VERBS = (
    "said",
    "told",
    "correction",
    "corrected",
    "noted",
    "stated",
    "directed",
    "insisted",
    "confirmed",
    "named",
    "wrote",
    "self-diagnosis",
    "recognized",
)

_DATE = r"20\d\d-\d\d-\d\d"

# Two shapes, both anchored on a date to keep precision high:
#   A. parenthetical:  "(Andrew 2026-04-25 ...)" or "(Aria self-diagnosis 2026-04-29)"
#   B. quotative:      "Andrew correction 2026-05-15" / "Andrew said ... 2026-..."
_ENT = "(?:" + "|".join(_PARTICIPANTS) + ")"
_VERB = "(?:" + "|".join(_ATTRIBUTION_VERBS) + ")"

_PAREN_DATED = re.compile(rf"\(\s*{_ENT}\b[^)\n]{{0,60}}?{_DATE}", re.IGNORECASE)
_QUOTATIVE_DATED = re.compile(
    rf"\b{_ENT}\b[^.\n]{{0,40}}?\b{_VERB}\b[^.\n]{{0,60}}?{_DATE}", re.IGNORECASE
)


@dataclass(frozen=True)
class AttributionFinding:
    """One surfaced attribution lacking a resolvable pointer.

    Not a verdict — a candidate for human/cross-model review. The
    substrate cannot tell honest-but-unpointered from fabricated.
    """

    knowledge_id: str
    snippet: str
    matched: str
    has_pointer: bool


def _has_resolvable_pointer(source_events: str | None, source_entity: str | None) -> bool:
    """True if the entry carries a structured source pointer.

    A pointer is source_events with at least one entry, OR a non-empty
    source_entity. v1 checks presence (the cheap Sagan stage); a future
    layer can verify each event-id resolves in the ledger (the sufficiency
    stage). Presence-not-sufficiency is named, not hidden.
    """
    if source_entity and source_entity.strip():
        return True
    if not source_events:
        return False
    stripped = source_events.strip()
    return stripped not in ("", "[]", "null", "None")


def _match_attribution(content: str) -> str | None:
    """Return the matched attribution substring, or None if no dated
    quotative attribution shape is present."""
    m = _PAREN_DATED.search(content) or _QUOTATIVE_DATED.search(content)
    if m:
        return m.group(0).strip()
    return None


def scan_unverified_attributions(
    include_pointered: bool = False,
) -> list[AttributionFinding]:
    """Scan the knowledge store for dated quotative attributions.

    Returns findings for entries whose content carries a dated quotative
    attribution to a participant. By default only entries WITHOUT a
    resolvable pointer are returned (the review candidates); pass
    include_pointered=True to see all matches.

    Read-only. Does not modify, block, or score anything.
    """
    conn = _get_connection()
    rows = conn.execute(
        "SELECT knowledge_id, content, source_events, source_entity "
        "FROM knowledge WHERE superseded_by IS NULL"
    ).fetchall()

    findings: list[AttributionFinding] = []
    for knowledge_id, content, source_events, source_entity in rows:
        if not content:
            continue
        matched = _match_attribution(content)
        if matched is None:
            continue
        has_ptr = _has_resolvable_pointer(source_events, source_entity)
        if has_ptr and not include_pointered:
            continue
        snippet = " ".join(content[:120].split())
        findings.append(
            AttributionFinding(
                knowledge_id=str(knowledge_id),
                snippet=snippet,
                matched=matched,
                has_pointer=has_ptr,
            )
        )
    return findings


__all__ = [
    "AttributionFinding",
    "scan_unverified_attributions",
]
