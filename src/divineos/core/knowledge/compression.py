"""Observational Compression — merge redundant knowledge into dense clusters.

The existing consolidation picks the longest entry as the base. This module
goes further: it synthesizes denser representations by extracting unique
terms from each entry, prioritizes by maturity tier, and preserves
provenance through graph edges.

Three compression strategies:

1. DEDUP COMPRESSION: Near-identical entries (>70% overlap) → keep the
   most mature/confident one, supersede the rest.

2. CLUSTER SYNTHESIS: Related entries (40-70% overlap) → extract unique
   contributions from each, build a composite entry.

3. GRAPH-AWARE COMPRESSION: Entries connected by SUPPORTS/ELABORATES
   edges → compress into a principle + evidence summary.
"""

import sqlite3
from typing import Any

from divineos.core.knowledge._base import _get_connection, _row_to_dict, _KNOWLEDGE_COLS
from divineos.core.knowledge._text import _compute_overlap, _normalize_text
from divineos.core.knowledge.crud import (
    get_knowledge,
    store_knowledge,
    supersede_knowledge,
)


# ─── Maturity Ranking ──────────────────────────────────────────────

_MATURITY_RANK = {
    "CONFIRMED": 4,
    "TESTED": 3,
    "HYPOTHESIS": 2,
    "RAW": 1,
}


def _maturity_score(entry: dict[str, Any]) -> int:
    """Rank an entry by maturity tier."""
    return _MATURITY_RANK.get(entry.get("maturity", "RAW"), 1)


def _pick_best_entry(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the highest-quality entry from a cluster.

    Priority: maturity > confidence > access_count > content length.
    """
    return max(
        entries,
        key=lambda e: (
            _maturity_score(e),
            e.get("confidence", 0.0),
            e.get("access_count", 0),
            len(e.get("content", "")),
        ),
    )


# ─── Unique Term Extraction ───────────────────────────────────────


def _extract_unique_terms(entry: dict[str, Any], others: list[dict[str, Any]]) -> set[str]:
    """Find words in entry that don't appear in any other entry."""
    entry_words = set(_normalize_text(entry.get("content", "")).split())
    other_words: set[str] = set()
    for other in others:
        other_words.update(_normalize_text(other.get("content", "")).split())
    return entry_words - other_words


# ─── Strategy 1: Dedup Compression ────────────────────────────────


def find_dedup_candidates(
    knowledge_type: str | None = None,
    overlap_threshold: float = 0.7,
    limit: int = 500,
) -> list[list[dict[str, Any]]]:
    """Find near-identical entries that can be deduplicated.

    Returns clusters of entries with >overlap_threshold word overlap.
    """
    entries = get_knowledge(knowledge_type=knowledge_type, limit=limit)
    if len(entries) < 2:
        return []

    clustered: set[str] = set()
    clusters: list[list[dict[str, Any]]] = []

    for i, entry in enumerate(entries):
        kid = entry["knowledge_id"]
        if kid in clustered:
            continue

        cluster = [entry]
        clustered.add(kid)

        for j in range(i + 1, len(entries)):
            other = entries[j]
            if other["knowledge_id"] in clustered:
                continue
            overlap = _compute_overlap(entry["content"], other["content"])
            if overlap >= overlap_threshold:
                cluster.append(other)
                clustered.add(other["knowledge_id"])

        if len(cluster) >= 2:
            clusters.append(cluster)

    return clusters


def compress_dedup(
    knowledge_type: str | None = None,
    overlap_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Deduplicate near-identical entries. Keep the best, supersede the rest.

    Returns list of actions taken.
    """
    clusters = find_dedup_candidates(knowledge_type, overlap_threshold)
    actions: list[dict[str, Any]] = []

    for cluster in clusters:
        best = _pick_best_entry(cluster)
        superseded = [e for e in cluster if e["knowledge_id"] != best["knowledge_id"]]

        for entry in superseded:
            supersede_knowledge(entry["knowledge_id"], best["knowledge_id"])

        actions.append(
            {
                "action": "dedup",
                "kept": best["knowledge_id"],
                "superseded": [e["knowledge_id"] for e in superseded],
                "kept_content": best["content"][:80],
                "count": len(superseded),
            }
        )

    return actions


# ─── Strategy 2: Cluster Synthesis ─────────────────────────────────


def find_synthesis_candidates(
    knowledge_type: str | None = None,
    low_threshold: float = 0.4,
    high_threshold: float = 0.7,
    min_cluster: int = 3,
    limit: int = 500,
) -> list[list[dict[str, Any]]]:
    """Find related-but-distinct entries that can be synthesized.

    These have 40-70% overlap — similar topic but each adds something.
    """
    entries = get_knowledge(knowledge_type=knowledge_type, limit=limit)
    if len(entries) < min_cluster:
        return []

    clustered: set[str] = set()
    clusters: list[list[dict[str, Any]]] = []

    for i, entry in enumerate(entries):
        kid = entry["knowledge_id"]
        if kid in clustered:
            continue

        cluster = [entry]
        clustered.add(kid)

        for j in range(i + 1, len(entries)):
            other = entries[j]
            if other["knowledge_id"] in clustered:
                continue
            overlap = _compute_overlap(entry["content"], other["content"])
            if low_threshold <= overlap < high_threshold:
                cluster.append(other)
                clustered.add(other["knowledge_id"])

        if len(cluster) >= min_cluster:
            clusters.append(cluster)

    return clusters


def synthesize_cluster(cluster: list[dict[str, Any]]) -> dict[str, Any]:
    """Synthesize a cluster of related entries into one dense entry.

    Takes the best entry as the base, then appends unique contributions
    from the others.
    """
    best = _pick_best_entry(cluster)
    others = [e for e in cluster if e["knowledge_id"] != best["knowledge_id"]]

    # Start with the best entry's content
    base_content = best["content"].strip()

    # Collect unique contributions from each other entry
    additions: list[str] = []
    for other in others:
        unique = _extract_unique_terms(other, [best] + [o for o in others if o != other])
        if len(unique) >= 3:  # only add if there are meaningful unique terms
            # Find the sentence containing the most unique terms
            sentences = other["content"].split(".")
            best_sentence = ""
            best_count = 0
            for sentence in sentences:
                s_words = set(_normalize_text(sentence).split())
                count = len(s_words & unique)
                if count > best_count:
                    best_count = count
                    best_sentence = sentence.strip()
            if best_sentence and len(best_sentence) > 10:
                additions.append(best_sentence)

    # Build the synthesized content
    if additions:
        # Cap additions to keep it dense
        additions = additions[:3]
        synthesized = base_content + ". Additionally: " + ". ".join(additions)
    else:
        synthesized = base_content

    # Combine metadata
    all_sources: list[str] = []
    all_tags: set[str] = set()
    max_confidence = 0.0
    best_maturity = "RAW"

    for entry in cluster:
        all_sources.extend(entry.get("source_events", []))
        all_tags.update(entry.get("tags", []))
        max_confidence = max(max_confidence, entry.get("confidence", 0.0))
        if _maturity_score(entry) > _MATURITY_RANK.get(best_maturity, 0):
            best_maturity = entry.get("maturity", "RAW")

    all_tags.add("compressed")
    all_tags.discard("")

    return {
        "content": synthesized,
        "knowledge_type": best.get("knowledge_type", "OBSERVATION"),
        "confidence": max_confidence,
        "source_events": list(set(all_sources)),
        "tags": sorted(all_tags),
        "maturity": best_maturity,
        "source_entries": [e["knowledge_id"] for e in cluster],
    }


def compress_synthesize(
    knowledge_type: str | None = None,
    min_cluster: int = 3,
) -> list[dict[str, Any]]:
    """Synthesize related entries into denser representations.

    Returns list of actions taken.
    """
    clusters = find_synthesis_candidates(knowledge_type, min_cluster=min_cluster)
    actions: list[dict[str, Any]] = []

    for cluster in clusters:
        result = synthesize_cluster(cluster)

        new_id = store_knowledge(
            knowledge_type=result["knowledge_type"],
            content=result["content"],
            confidence=result["confidence"],
            source_events=result["source_events"],
            tags=result["tags"],
        )

        # Supersede source entries
        for kid in result["source_entries"]:
            if kid != new_id:
                supersede_knowledge(kid, new_id)

        actions.append(
            {
                "action": "synthesize",
                "new_id": new_id,
                "source_count": len(result["source_entries"]),
                "content_preview": result["content"][:100],
            }
        )

    return actions


# ─── Strategy 3: Graph-Aware Compression ──────────────────────────


def find_graph_clusters(max_clusters: int = 10) -> list[dict[str, Any]]:
    """Find entries connected by SUPPORTS/ELABORATES edges.

    Returns clusters where a central entry has 2+ supporting entries.
    """
    conn = _get_connection()
    try:
        # Find entries with multiple SUPPORTS/ELABORATES edges pointing to them
        rows = conn.execute(
            """SELECT target_id, COUNT(*) as edge_count
               FROM knowledge_edges
               WHERE edge_type IN ('SUPPORTS', 'ELABORATES')
               GROUP BY target_id
               HAVING edge_count >= 2
               ORDER BY edge_count DESC
               LIMIT ?""",
            (max_clusters,),
        ).fetchall()

        clusters: list[dict[str, Any]] = []
        for row in rows:
            target_id = row[0]

            # Get the target entry
            target_row = conn.execute(
                f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
                (target_id,),
            ).fetchone()
            if not target_row:
                continue

            target = _row_to_dict(target_row)

            # Get supporting entries
            support_rows = conn.execute(
                f"""SELECT k.{_KNOWLEDGE_COLS.replace("knowledge_id", "k.knowledge_id")}
                    FROM knowledge k
                    JOIN knowledge_edges e ON k.knowledge_id = e.source_id
                    WHERE e.target_id = ? AND e.edge_type IN ('SUPPORTS', 'ELABORATES')
                    AND k.superseded_by IS NULL""",
                (target_id,),
            ).fetchall()

            supports = [_row_to_dict(r) for r in support_rows]
            if len(supports) >= 2:
                clusters.append(
                    {
                        "target": target,
                        "supports": supports,
                        "edge_count": len(supports),
                    }
                )

        return clusters
    except (sqlite3.OperationalError, OSError, KeyError, TypeError) as e:
        from loguru import logger

        logger.debug("Graph cluster discovery failed: %s", e)
        return []
    finally:
        conn.close()


def compress_graph_cluster(cluster: dict[str, Any]) -> dict[str, Any] | None:
    """Compress a graph cluster into a principle + evidence summary.

    The target entry becomes the principle. Supporting entries are
    summarized as evidence lines appended to it.
    """
    target = cluster["target"]
    supports = cluster["supports"]

    if not supports:
        return None

    # Build evidence summary
    evidence_lines: list[str] = []
    for s in supports[:5]:  # cap at 5 evidence items
        content = s["content"].replace("\n", " ").strip()
        if len(content) > 100:
            content = content[:97] + "..."
        maturity = s.get("maturity", "RAW")
        evidence_lines.append(f"[{maturity}] {content}")

    evidence_block = " | Evidence: " + " ; ".join(evidence_lines)
    compressed_content = target["content"].strip() + evidence_block

    # Cap total length
    if len(compressed_content) > 1000:
        compressed_content = compressed_content[:997] + "..."

    all_tags = set(target.get("tags", []))
    all_tags.add("graph-compressed")
    all_tags.discard("")

    return {
        "content": compressed_content,
        "knowledge_type": target.get("knowledge_type", "PRINCIPLE"),
        "confidence": target.get("confidence", 0.7),
        "source_events": target.get("source_events", []),
        "tags": sorted(all_tags),
        "target_id": target["knowledge_id"],
        "support_ids": [s["knowledge_id"] for s in supports],
    }


# ─── Full Compression Pipeline ────────────────────────────────────


def run_compression(
    knowledge_type: str | None = None,
    strategies: list[str] | None = None,
) -> dict[str, Any]:
    """Run the full compression pipeline.

    Strategies: "dedup", "synthesize", "graph" (default: all three).
    """
    active = strategies or ["dedup", "synthesize", "graph"]
    results: dict[str, Any] = {
        "dedup": [],
        "synthesize": [],
        "graph": [],
        "total_compressed": 0,
    }

    if "dedup" in active:
        dedup_actions = compress_dedup(knowledge_type)
        results["dedup"] = dedup_actions
        results["total_compressed"] += sum(a["count"] for a in dedup_actions)

    if "synthesize" in active:
        synth_actions = compress_synthesize(knowledge_type)
        results["synthesize"] = synth_actions
        results["total_compressed"] += sum(a["source_count"] for a in synth_actions)

    if "graph" in active:
        graph_clusters = find_graph_clusters()
        graph_actions: list[dict[str, Any]] = []
        for cluster in graph_clusters:
            compressed = compress_graph_cluster(cluster)
            if compressed:
                new_id = store_knowledge(
                    knowledge_type=compressed["knowledge_type"],
                    content=compressed["content"],
                    confidence=compressed["confidence"],
                    source_events=compressed["source_events"],
                    tags=compressed["tags"],
                )
                # Supersede supports into the compressed entry
                for sid in compressed["support_ids"]:
                    supersede_knowledge(sid, new_id)

                graph_actions.append(
                    {
                        "action": "graph_compress",
                        "new_id": new_id,
                        "target_id": compressed["target_id"],
                        "support_count": len(compressed["support_ids"]),
                        "content_preview": compressed["content"][:100],
                    }
                )
                results["total_compressed"] += len(compressed["support_ids"])

        results["graph"] = graph_actions

    return results


def format_compression_report(results: dict[str, Any]) -> str:
    """Format compression results for display."""
    lines: list[str] = []

    if results["total_compressed"] == 0:
        return "No entries compressed — knowledge store is already dense."

    lines.append(f"Compressed {results['total_compressed']} entries:\n")

    if results["dedup"]:
        lines.append(f"  Dedup: {len(results['dedup'])} cluster(s)")
        for action in results["dedup"]:
            lines.append(f"    → Kept: {action['kept_content']}")
            lines.append(f"      Superseded {action['count']} duplicate(s)")

    if results["synthesize"]:
        lines.append(f"  Synthesized: {len(results['synthesize'])} cluster(s)")
        for action in results["synthesize"]:
            lines.append(f"    → {action['source_count']} entries → {action['content_preview']}")

    if results["graph"]:
        lines.append(f"  Graph-compressed: {len(results['graph'])} cluster(s)")
        for action in results["graph"]:
            lines.append(f"    → {action['support_count']} supports merged into principle")

    return "\n".join(lines)
