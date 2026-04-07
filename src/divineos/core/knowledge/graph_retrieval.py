"""Graph-Enhanced Retrieval — knowledge as clusters, not isolated facts.

The knowledge_edges table has been storing relationships since day one:
CAUSED_BY, SUPPORTS, CONTRADICTS, ELABORATES, SUPERSEDES, RELATED_TO,
DERIVED_FROM, APPLIES_TO. But retrieval never touched them — briefing
showed a flat list of disconnected entries.

This module activates the graph. When retrieving knowledge, we traverse
edges to cluster related entries together. A PRINCIPLE shown alongside
the OBSERVATIONS that SUPPORT it is worth more than either alone.
"""

from typing import Any

from divineos.core.knowledge._base import (
    _KNOWLEDGE_COLS,
    _get_connection,
    _row_to_dict,
)
from divineos.core.knowledge.edges import get_edges, get_edges_batch

_GRAPH_ERRORS = (OSError, Exception)

# Edge type labels for display — short, human-readable
_EDGE_LABELS: dict[str, str] = {
    "CAUSED_BY": "caused by",
    "SUPPORTS": "supports",
    "CONTRADICTS": "contradicts",
    "ELABORATES": "elaborates",
    "SUPERSEDES": "supersedes",
    "RELATED_TO": "related to",
    "DERIVED_FROM": "derived from",
    "APPLIES_TO": "applies to",
    "IMPLIES": "implies",
    "REQUIRES": "requires",
    "GENERALIZES": "generalizes",
    "SPECIALIZES": "specializes",
}


def _get_entry_by_id(knowledge_id: str) -> dict[str, Any] | None:
    """Fetch a single knowledge entry by ID."""
    conn = _get_connection()
    try:
        row = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def build_knowledge_cluster(
    knowledge_id: str,
    max_depth: int = 1,
    max_neighbors: int = 5,
) -> dict[str, Any]:
    """Build a cluster around a knowledge entry by traversing edges.

    Returns a dict with:
      - "seed": the central entry
      - "connections": list of {"entry": dict, "edge_type": str, "direction": str}
    """
    seed = _get_entry_by_id(knowledge_id)
    if not seed:
        return {"seed": None, "connections": []}

    connections: list[dict[str, Any]] = []
    seen: set[str] = {knowledge_id}

    # max_depth reserved for multi-hop BFS — currently single-hop only
    _ = max_depth

    edges = get_edges(knowledge_id, direction="both", layer="semantic")
    for edge in edges[:max_neighbors]:
        neighbor_id = edge.target_id if edge.source_id == knowledge_id else edge.source_id
        if neighbor_id in seen:
            continue
        seen.add(neighbor_id)

        neighbor = _get_entry_by_id(neighbor_id)
        if not neighbor or neighbor.get("superseded_by"):
            continue

        direction = "outgoing" if edge.source_id == knowledge_id else "incoming"
        connections.append(
            {
                "entry": neighbor,
                "edge_type": edge.edge_type,
                "direction": direction,
            }
        )

    return {"seed": seed, "connections": connections}


def cluster_for_briefing(
    entries: list[dict[str, Any]],
    max_clusters: int = 5,
) -> list[dict[str, Any]]:
    """Group briefing entries that are connected by edges.

    Returns a list of clusters. Each cluster has:
      - "seed": the highest-scored entry in the cluster
      - "connected_entries": list of other entries in the cluster with edge info
      - "standalone": False if this entry has connections

    Entries not connected to any other briefing entry appear as standalone.
    """
    entry_ids = {e["knowledge_id"] for e in entries}
    entry_map = {e["knowledge_id"]: e for e in entries}

    # Batch-load all edges for all briefing entries in one query
    all_edges = get_edges_batch(entry_ids, layer="semantic")

    clusters: list[dict[str, Any]] = []
    clustered: set[str] = set()
    cluster_count = 0

    for entry in entries:
        kid = entry["knowledge_id"]
        if kid in clustered:
            continue

        edges = all_edges.get(kid, [])
        connected: list[dict[str, Any]] = []

        for edge in edges:
            neighbor_id = edge.target_id if edge.source_id == kid else edge.source_id
            if neighbor_id in entry_ids and neighbor_id not in clustered:
                neighbor = entry_map[neighbor_id]
                direction = "outgoing" if edge.source_id == kid else "incoming"
                connected.append(
                    {
                        "entry": neighbor,
                        "edge_type": edge.edge_type,
                        "direction": direction,
                    }
                )
                clustered.add(neighbor_id)

        if connected and cluster_count < max_clusters:
            clustered.add(kid)
            clusters.append(
                {
                    "seed": entry,
                    "connected_entries": connected,
                    "standalone": False,
                }
            )
            cluster_count += 1
        elif kid not in clustered:
            clusters.append(
                {
                    "seed": entry,
                    "connected_entries": [],
                    "standalone": True,
                }
            )

    return clusters


def format_cluster_line(connection: dict[str, Any]) -> str:
    """Format a single connection line for display in briefing."""
    entry = connection["entry"]
    edge_type = connection["edge_type"]
    direction = connection["direction"]

    label = _EDGE_LABELS.get(edge_type, edge_type.lower())
    content = entry["content"].replace("\n", " ")
    if len(content) > 120:
        content = content[:117] + "..."

    # Format direction: "← supports" (incoming) vs "→ elaborates" (outgoing)
    arrow = "->" if direction == "outgoing" else "<-"
    return f"  {arrow} {label}: [{entry['confidence']:.2f}] {content}"


def get_graph_connections_for_recall(
    active_entries: list[dict[str, Any]],
    max_connections: int = 10,
) -> list[dict[str, Any]]:
    """Find graph-connected entries not already in active memory.

    For the recall() function: after getting active memory items,
    traverse edges to pull in connected items that add context.
    """
    active_ids = {e.get("knowledge_id", "") for e in active_entries}
    top_ids = {e.get("knowledge_id", "") for e in active_entries[:10]} - {""}
    connections: list[dict[str, Any]] = []
    seen: set[str] = set(active_ids)

    # Batch-load edges for top-10 active items in one query
    all_edges = get_edges_batch(top_ids, layer="semantic") if top_ids else {}

    for entry in active_entries[:10]:
        kid = entry.get("knowledge_id", "")
        if not kid:
            continue

        edges = all_edges.get(kid, [])
        for edge in edges[:3]:  # Max 3 connections per entry
            neighbor_id = edge.target_id if edge.source_id == kid else edge.source_id
            if neighbor_id in seen:
                continue
            seen.add(neighbor_id)

            neighbor = _get_entry_by_id(neighbor_id)
            if not neighbor or neighbor.get("superseded_by"):
                continue
            if neighbor.get("confidence", 0) < 0.3:
                continue

            connections.append(
                {
                    "entry": neighbor,
                    "edge_type": edge.edge_type,
                    "via": kid,
                }
            )

            if len(connections) >= max_connections:
                return connections

    return connections
