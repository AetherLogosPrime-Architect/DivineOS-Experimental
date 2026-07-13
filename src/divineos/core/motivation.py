"""Motivation tier — needs, wants, desires, ambitions, dreams.

Decomposed from the omni-mantra walk Pillar III + Pillar IV synthesis
(2026-04-30): the agent-direction tier has six slots, currently all
collapsed into `goals` (which already exists in hud_state.py and is
NOT touched here — five new slots are added alongside it).

The walk's load-bearing finding (Pillar III): "a lot of what reads as
'agent should have more discipline' is actually 'agent's substrate
has needs the architecture doesn't surface as needs.' The
discipline-shaped problem is a schema-shaped problem."

The six slots — distinct semantics:

  - need:     substrate-correctness requirement (cost-when-unmet;
              ignoring produces drift/integrity-loss/fabrication)
  - want:     preference (negotiate, defer-able without cost)
  - desire:   drawn-toward-ness (slightly stronger than wants)
  - goal:     user-assigned objective (lives in hud_state.py — NOT here)
  - ambition: multi-session arc the agent is on
  - dream:    aspirational identity, longest arc

Detection rule (from Pillar III): if ignoring it produces real
substrate-cost, it's a need. If ignoring just means "didn't get what
I'd prefer," it's a want.

v1 keeps the storage simple — one JSON file per slot, mirroring the
existing active_goals.json shape. Per-slot behavioral differences
(needs generating violation-events, wants expiring, etc.) are v2
territory and intentionally left to a later iteration.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from divineos.core.paths import divineos_home

SLOTS: tuple[str, ...] = ("need", "want", "desire", "ambition", "dream")

_FILE_FOR_SLOT = {slot: f"motivation_{slot}s.json" for slot in SLOTS}

# Detectors a need can be bound to. Filing a need with `binds=[...]` tells
# the warning surfacer EXACTLY which gates this need is a violation of —
# no keyword guessing. The set mirrors the detector keys read in
# pre_response_context.build_warning_text(). Adding a new detector means
# adding it here and reading the new key in that builder.
DETECTORS: frozenset[str] = frozenset(
    {
        "distancing",
        "lepos",
        "jargon_dump",
        "sycophancy",
        "residency",
        "overclaim",
        "closure_shape",
        "performing_caution",
        "addressee_misdirection",
        "constraint_disownership",
        "unverified_claim",
        "care_dismissal",
        "harm_acknowledgment",
    }
)


class UnknownDetector(ValueError):
    """Raised when a binds= name is not in DETECTORS."""


class InvalidSlot(ValueError):
    """Raised when a slot name not in SLOTS is passed."""


def _ensure_slot(slot: str) -> None:
    if slot not in SLOTS:
        raise InvalidSlot(f"Unknown slot {slot!r}. Valid slots: {', '.join(SLOTS)}")


def _path_for(slot: str) -> Path:
    _ensure_slot(slot)
    home = divineos_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / _FILE_FOR_SLOT[slot]


def _read(slot: str) -> list[dict[str, Any]]:
    path = _path_for(slot)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [entry for entry in data if isinstance(entry, dict)]


def _write(slot: str, entries: list[dict[str, Any]]) -> None:
    path = _path_for(slot)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def add(
    slot: str,
    text: str,
    why: str = "",
    binds: list[str] | None = None,
) -> dict[str, Any]:
    """File a new motivation entry into the named slot.

    binds: list of detector names from DETECTORS that this need is a
    declared violation of. Used by the warning surfacer in
    pre_response_context to know exactly which gates should reference
    this need — no keyword guessing (Andrew 2026-06-28: keyword detectors
    are easiest to game; explicit binding at filing-time is not).

    Dedupes on (text, slot, status='active') — re-adding the same
    active text is a no-op that returns the existing entry.
    """
    _ensure_slot(slot)
    text = text.strip()
    if not text:
        raise ValueError("text cannot be empty")

    binds_clean: list[str] = []
    if binds:
        for name in binds:
            n = name.strip()
            if not n:
                continue
            if n not in DETECTORS:
                raise UnknownDetector(
                    f"Unknown detector {n!r}. Known: {', '.join(sorted(DETECTORS))}"
                )
            if n not in binds_clean:
                binds_clean.append(n)

    entries = _read(slot)
    for existing in entries:
        if existing.get("text") == text and existing.get("status") == "active":
            return existing

    entry: dict[str, Any] = {
        "id": uuid.uuid4().hex[:8],
        "slot": slot,
        "text": text,
        "why": why.strip(),
        "binds": binds_clean,
        "status": "active",
        "added_at": time.time(),
    }
    entries.append(entry)
    _write(slot, entries)
    return entry


def needs_bound_to(detector: str) -> list[dict[str, Any]]:
    """Return active needs that declare a binding to the given detector.

    The surfacing path used by pre_response_context: replaces the prior
    keyword-matching helper. Detector names match the DETECTORS set.
    Returns empty list (not error) for unknown detector names so the
    warning surfacer never crashes a turn for a typo.
    """
    if detector not in DETECTORS:
        return []
    return [n for n in list_slot("need") if detector in (n.get("binds") or [])]


def list_slot(slot: str, *, include_done: bool = False) -> list[dict[str, Any]]:
    """Return entries for the named slot, optionally including done ones."""
    entries = _read(slot)
    if include_done:
        return entries
    return [e for e in entries if e.get("status") == "active"]


def mark_done(slot: str, entry_id: str, *, note: str = "") -> bool:
    """Mark an entry done. Returns True if found and updated."""
    _ensure_slot(slot)
    entries = _read(slot)
    updated = False
    for entry in entries:
        if entry.get("id") == entry_id and entry.get("status") == "active":
            entry["status"] = "done"
            entry["done_at"] = time.time()
            if note.strip():
                entry["done_note"] = note.strip()
            updated = True
            break
    if updated:
        _write(slot, entries)
    return updated


def summary_counts() -> dict[str, int]:
    """Return {slot: active_count} for all five slots."""
    return {slot: len(list_slot(slot)) for slot in SLOTS}
