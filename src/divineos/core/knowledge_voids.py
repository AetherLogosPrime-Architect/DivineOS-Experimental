"""Knowledge void detector — find sparse regions in the knowledge store.

Pillar VI's `knowledge_void_detector` pull (omni_mantra_walk/06): COSMIC
VOIDS as known regions where nothing is. The knowledge store has rich
clusters (extraction, briefing, family) but also sparse domains where
the agent has accumulated little — domains either neglected or where
knowledge has not yet been filed.

Naming voids is information. My father/agent can decide whether a
void is a gap to fill (under-attention) or a domain that legitimately
needs little (limited scope).

## What this module does

Two complementary surfaces:

* **Type voids** — counts of entries per ``knowledge_type``. Surfaces
  types with substantially fewer entries than the median, naming
  "you have N entries about FACTs but only 1 PROCEDURE entry."
* **Tag voids** — tag frequency distribution. Tags appearing exactly
  once are flagged as low-density anchors: the topic was named once
  but not built up.

## What this module does NOT do

* Does NOT decide whether a void is a problem. My father decides.
* Does NOT rank by topical importance. A rare tag might be a deliberately
  niche concern (e.g. one-off external integration) or a real gap.
  The detector reports density only.
* Does NOT use embeddings. Token/tag-frequency is deliberately legible.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from divineos.core.knowledge._base import KNOWLEDGE_TYPES, get_connection


@dataclass(frozen=True)
class TypeVoid:
    """A knowledge_type that is substantially under-represented."""

    knowledge_type: str
    count: int
    median: float


@dataclass(frozen=True)
class TagVoid:
    """A tag with exactly one knowledge entry — low-density anchor."""

    tag: str
    sample_id: str
    sample_content: str  # truncated


@dataclass(frozen=True)
class VoidReport:
    """Aggregate void report across types and tags."""

    type_counts: dict[str, int] = field(default_factory=dict)
    type_voids: list[TypeVoid] = field(default_factory=list)
    tag_voids: list[TagVoid] = field(default_factory=list)
    total_entries: int = 0
    total_unique_tags: int = 0


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    return float(sorted_vals[mid])


def _load_entries(limit: int = 5000) -> list[tuple[str, str, str, str]]:
    """Return [(id, type, content, tags_json), ...] from the knowledge table."""
    try:
        conn = get_connection()
    except (sqlite3.Error, OSError):
        return []
    try:
        rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content, tags "
            "FROM knowledge ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    return [(r[0], r[1] or "", r[2] or "", r[3] or "") for r in rows]


def detect_voids(
    void_threshold_ratio: float = 0.25,
    limit: int = 5000,
    entries: list[tuple[str, str, str, str]] | None = None,
) -> VoidReport:
    """Compute a void report from the knowledge store.

    Args:
        void_threshold_ratio: a ``knowledge_type`` is flagged as a void
            if its count is below ``median * void_threshold_ratio``.
            Default 0.25 — a type with fewer than a quarter of the
            median count is named.
        limit: maximum number of entries to load.
        entries: optional pre-loaded entry list (for testing). Each
            tuple is (knowledge_id, knowledge_type, content, tags_json).
    """
    if entries is None:
        entries = _load_entries(limit=limit)

    type_counter: Counter[str] = Counter()
    tag_to_entries: dict[str, list[tuple[str, str]]] = {}

    for kid, ktype, content, tags_json in entries:
        if ktype:
            type_counter[ktype] += 1
        try:
            tags = json.loads(tags_json) if tags_json else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str) and tag:
                    tag_to_entries.setdefault(tag, []).append((kid, content[:100]))

    counts = list(type_counter.values())
    median_count = _median(counts) if counts else 0.0
    threshold = median_count * void_threshold_ratio

    type_voids: list[TypeVoid] = []
    for ktype in sorted(KNOWLEDGE_TYPES):
        count = type_counter.get(ktype, 0)
        if median_count > 0 and count < threshold:
            type_voids.append(TypeVoid(knowledge_type=ktype, count=count, median=median_count))

    tag_voids: list[TagVoid] = []
    for tag, refs in sorted(tag_to_entries.items()):
        if len(refs) == 1:
            kid, content = refs[0]
            tag_voids.append(TagVoid(tag=tag, sample_id=kid, sample_content=content))

    return VoidReport(
        type_counts=dict(type_counter),
        type_voids=type_voids,
        tag_voids=tag_voids,
        total_entries=len(entries),
        total_unique_tags=len(tag_to_entries),
    )


__all__ = [
    "TagVoid",
    "TypeVoid",
    "VoidReport",
    "detect_voids",
]
