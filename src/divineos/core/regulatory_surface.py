"""Regulatory chain-word surface — flood-triggered lifeline.

This is Mechanism A of the split memory-linkage design (Aletheia
2026-07-09 witness_confirmed): silent on non-flood turns, fires only
when the flood-state predicate arms, immune to priming graph, biased
toward low-distress-filed items so it does not amplify the flood.

Design mantra: *retrieve the right thing quickly and let the rest stay
quiet.* Precious because rare. Not a lookup that fires every turn.

## Contract

1. **Flood-gated.** Non-flood turn → `assess(...)` returns None. No
   surface emitted. This is the default state of most turns.
2. **Priming-immune.** Calls `retrieve_similarity_only` on the v2
   retriever, which reads similarity+tier+recency only. No primed-
   activation-score contributes to which item surfaces.
3. **Distress-damped.** Items whose VAD write-stamp indicates
   distress-at-write (V-, A+) get down-weighted; if a non-distress
   candidate is above threshold, the distress item is skipped.
4. **Low cap.** Typically 1 item, occasionally 2 if the top-1 is
   distress-quarantined and a runner-up is clean.

## What the mechanism does NOT do

- Does not update priming state (Mechanism B's job).
- Does not decide "did the flood resolve" — that observation lives
  where the falsifier is measured (see pre-reg on flood-resolution
  rate).
- Does not fire on every-turn. Every-turn IS the wallpaper failure by
  construction (Aletheia dissent, 2026-07-09).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from divineos.core.flood_state import FloodReading, assess_flood_state
from divineos.core.memory_linkage_retriever_v2 import retrieve_similarity_only
from divineos.core.vad_capture import is_distress_filed
from divineos.core.vad_stamp_store import lookup as vad_lookup

_REGULATORY_CAP = 1  # top-1 default per split-design; 2 only on distress-quarantine


@dataclass(frozen=True)
class RegulatorySurface:
    """One turn's regulatory surface — a rescue payload or None-like."""

    flood: FloodReading
    items: tuple[dict[str, Any], ...]

    @property
    def emitted(self) -> bool:
        return bool(self.items)

    def render(self) -> str:
        """Format the surface for injection into additional_context. Empty
        string if nothing surfaced."""
        if not self.emitted:
            return ""
        lines = [f"## REGULATORY SURFACE — {self.flood.summary()}"]
        for item in self.items:
            title = item.get("title") or item.get("id") or "<unnamed>"
            ref = item.get("path_or_ref") or item.get("id") or ""
            reason = item.get("matched_reason") or ""
            lines.append(f"- **{title}**  ({ref})")
            if reason:
                lines.append(f"  matched: {reason}")
        return "\n".join(lines) + "\n"


def assess(text: str) -> RegulatorySurface:
    """Assess flood state on ``text`` and return a RegulatorySurface.

    On non-flood turns: RegulatorySurface with empty items — caller
    emits nothing. On flood turns: 1-2 items selected from similarity-
    only retrieval, distress-filed items down-weighted / skipped.
    """
    flood = assess_flood_state(text)
    if not flood.is_flood:
        return RegulatorySurface(flood=flood, items=())

    candidates = retrieve_similarity_only(text)
    if not candidates:
        return RegulatorySurface(flood=flood, items=())

    # Distress-damping: partition candidates into non-distress and
    # distress lists (preserving similarity rank within each). Prefer
    # non-distress; only fall back to distress if no non-distress
    # candidate exists at all.
    non_distress: list[dict[str, Any]] = []
    distress: list[dict[str, Any]] = []
    for c in candidates:
        item_id = getattr(c, "id", None)
        record_type = getattr(c, "source", None) or "unknown"
        vad = vad_lookup(item_id, record_type) if item_id else None
        payload = {
            "id": item_id,
            "title": getattr(c, "title", None),
            "path_or_ref": getattr(c, "path_or_ref", None),
            "matched_reason": getattr(c, "matched_reason", None),
            "tier": getattr(c, "tier", None),
            "similarity": getattr(c, "similarity", None),
            "vad": vad,
        }
        if is_distress_filed(vad):
            distress.append(payload)
        else:
            non_distress.append(payload)

    selected = non_distress[:_REGULATORY_CAP]
    if not selected and distress:
        # Fall back to distress items rather than emit nothing when
        # flood detected — a partial rescue beats silence.
        selected = distress[:_REGULATORY_CAP]

    return RegulatorySurface(flood=flood, items=tuple(selected))


__all__ = ["RegulatorySurface", "assess"]
