"""Unified knowledge edge system — all typed connections in one table.

Every edge between knowledge entries lives here, whether semantic
(CAUSED_BY, ELABORATES) or logical (IMPLIES, CONTRADICTS). Each edge
has a layer tag so consumers can filter by purpose.

This replaces two separate tables (knowledge_relationships and
logical_relations) with a single knowledge_edges table that has the
richer schema (confidence, warrant_id, status, layer).
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger

from divineos.core.knowledge import get_connection


# ─── Schema ──────────────────────────────────────────────────────────

_TABLE = "knowledge_edges"


def init_edge_table() -> None:
    """Create the knowledge_edges table. Idempotent."""
    conn = get_connection()
    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                edge_id       TEXT PRIMARY KEY,
                source_id     TEXT NOT NULL,
                target_id     TEXT NOT NULL,
                edge_type     TEXT NOT NULL,
                layer         TEXT NOT NULL DEFAULT 'semantic',
                confidence    REAL NOT NULL DEFAULT 1.0,
                warrant_id    TEXT DEFAULT NULL,
                created_at    REAL NOT NULL,
                status        TEXT NOT NULL DEFAULT 'ACTIVE',
                notes         TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (source_id) REFERENCES knowledge(knowledge_id),
                FOREIGN KEY (target_id) REFERENCES knowledge(knowledge_id)
            )
        """)
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_edges_source
            ON {_TABLE}(source_id)
        """)
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_edges_target
            ON {_TABLE}(target_id)
        """)
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_edges_type
            ON {_TABLE}(edge_type)
        """)
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_edges_layer
            ON {_TABLE}(layer)
        """)
        conn.commit()

        # Migrate from old tables if they exist
        _migrate_old_tables(conn)
    finally:
        conn.close()


def _migrate_old_tables(conn: Any) -> None:
    """Copy data from knowledge_relationships and logical_relations into knowledge_edges.

    Only runs once — checks if old tables exist and have data not yet migrated.
    Idempotent: uses INSERT OR IGNORE to avoid duplicates.
    """
    # Migrate knowledge_relationships → semantic layer
    try:
        old_rows = conn.execute(
            "SELECT relationship_id, source_id, target_id, relationship, created_at, notes "
            "FROM knowledge_relationships"
        ).fetchall()
        if old_rows:
            for row in old_rows:
                conn.execute(
                    f"INSERT OR IGNORE INTO {_TABLE} "
                    "(edge_id, source_id, target_id, edge_type, layer, confidence, "
                    "warrant_id, created_at, status, notes) "
                    "VALUES (?, ?, ?, ?, 'semantic', 1.0, NULL, ?, 'ACTIVE', ?)",
                    (row[0], row[1], row[2], row[3], row[4], row[5]),
                )
            conn.commit()
            logger.debug(f"Migrated {len(old_rows)} edges from knowledge_relationships")
    except sqlite3.OperationalError:
        pass  # Table doesn't exist yet — nothing to migrate

    # Migrate logical_relations → logical layer
    try:
        old_rows = conn.execute(
            "SELECT relation_id, source_id, target_id, relation_type, confidence, "
            "warrant_id, created_at, status, notes FROM logical_relations"
        ).fetchall()
        if old_rows:
            for row in old_rows:
                conn.execute(
                    f"INSERT OR IGNORE INTO {_TABLE} "
                    "(edge_id, source_id, target_id, edge_type, layer, confidence, "
                    "warrant_id, created_at, status, notes) "
                    "VALUES (?, ?, ?, ?, 'logical', ?, ?, ?, ?, ?)",
                    (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]),
                )
            conn.commit()
            logger.debug(f"Migrated {len(old_rows)} edges from logical_relations")
    except sqlite3.OperationalError:
        pass  # Table doesn't exist yet


# ─── Types ───────────────────────────────────────────────────────────

# Semantic edge types — describe how knowledge relates in meaning
SEMANTIC_TYPES = {
    "CAUSED_BY",
    "SUPPORTS",
    "CONTRADICTS",
    "ELABORATES",
    "SUPERSEDES",
    "RELATED_TO",
    "DERIVED_FROM",
    "APPLIES_TO",
}

# Logical edge types — formal inference edges
LOGICAL_TYPES = {
    "IMPLIES",
    "CONTRADICTS",
    "REQUIRES",
    "SUPPORTS",
    "GENERALIZES",
    "SPECIALIZES",
}

# All valid edge types (union)
ALL_EDGE_TYPES = SEMANTIC_TYPES | LOGICAL_TYPES

# Inverse mapping
INVERSE_EDGES = {
    "IMPLIES": "REQUIRES",
    "REQUIRES": "IMPLIES",
    "CONTRADICTS": "CONTRADICTS",
    "SUPPORTS": "SUPPORTS",
    "GENERALIZES": "SPECIALIZES",
    "SPECIALIZES": "GENERALIZES",
    "CAUSED_BY": "CAUSED_BY",
    "ELABORATES": "ELABORATES",
    "SUPERSEDES": "SUPERSEDES",
    "RELATED_TO": "RELATED_TO",
    "DERIVED_FROM": "DERIVED_FROM",
    "APPLIES_TO": "APPLIES_TO",
}

# Which layer a type belongs to (types in both get assigned by caller)
_TYPE_TO_DEFAULT_LAYER = {
    "CAUSED_BY": "semantic",
    "ELABORATES": "semantic",
    "SUPERSEDES": "semantic",
    "RELATED_TO": "semantic",
    "DERIVED_FROM": "semantic",
    "APPLIES_TO": "semantic",
    "IMPLIES": "logical",
    "REQUIRES": "logical",
    "GENERALIZES": "logical",
    "SPECIALIZES": "logical",
    # SUPPORTS and CONTRADICTS — default to semantic, logic callers pass layer explicitly
    "SUPPORTS": "semantic",
    "CONTRADICTS": "semantic",
}


@dataclass
class KnowledgeEdge:
    """A typed edge between two knowledge entries."""

    edge_id: str
    source_id: str
    target_id: str
    edge_type: str
    layer: str = "semantic"
    confidence: float = 1.0
    warrant_id: str | None = None
    created_at: float = 0.0
    status: str = "ACTIVE"
    notes: str = ""


# ─── CRUD ────────────────────────────────────────────────────────────


def create_edge(
    source_id: str,
    target_id: str,
    edge_type: str,
    layer: str | None = None,
    confidence: float = 1.0,
    warrant_id: str | None = None,
    notes: str = "",
) -> KnowledgeEdge:
    """Create an edge between two knowledge entries.

    layer defaults based on edge_type if not specified.
    """
    if edge_type not in ALL_EDGE_TYPES:
        raise ValueError(f"Invalid edge type: {edge_type}. Must be one of {sorted(ALL_EDGE_TYPES)}")
    if source_id == target_id:
        raise ValueError("Cannot create an edge from a knowledge entry to itself")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

    if layer is None:
        layer = _TYPE_TO_DEFAULT_LAYER.get(edge_type, "semantic")

    # Check for duplicate
    existing = find_edge(source_id, target_id, edge_type)
    if existing:
        return existing

    edge = KnowledgeEdge(
        edge_id=str(uuid.uuid4()),
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        layer=layer,
        confidence=confidence,
        warrant_id=warrant_id,
        created_at=time.time(),
        notes=notes,
    )

    conn = get_connection()
    try:
        conn.execute(
            f"""
            INSERT INTO {_TABLE}
                (edge_id, source_id, target_id, edge_type, layer, confidence,
                 warrant_id, created_at, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge.edge_id,
                edge.source_id,
                edge.target_id,
                edge.edge_type,
                edge.layer,
                edge.confidence,
                edge.warrant_id,
                edge.created_at,
                edge.status,
                edge.notes,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug(
        "Created {} edge {} --{}-> {}",
        layer,
        source_id[:8],
        edge_type,
        target_id[:8],
    )
    return edge


def find_edge(source_id: str, target_id: str, edge_type: str) -> KnowledgeEdge | None:
    """Find an existing active edge between two entries of a given type."""
    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT * FROM {_TABLE} WHERE source_id = ? AND target_id = ? AND edge_type = ? AND status = 'ACTIVE'",
            (source_id, target_id, edge_type),
        ).fetchone()
    finally:
        conn.close()

    return _row_to_edge(row) if row else None


def get_edges(
    knowledge_id: str,
    direction: str = "both",
    edge_type: str | None = None,
    layer: str | None = None,
) -> list[KnowledgeEdge]:
    """Get all active edges for a knowledge entry.

    direction: "outgoing", "incoming", or "both".
    layer: "semantic", "logical", or None for all.
    """
    conn = get_connection()
    try:
        results: list[KnowledgeEdge] = []

        for d in ("outgoing", "incoming"):
            if direction not in (d, "both"):
                continue

            col = "source_id" if d == "outgoing" else "target_id"
            conditions = [f"{col} = ?", "status = 'ACTIVE'"]
            params: list[Any] = [knowledge_id]

            if edge_type:
                conditions.append("edge_type = ?")
                params.append(edge_type)
            if layer:
                conditions.append("layer = ?")
                params.append(layer)

            where = " AND ".join(conditions)
            rows = conn.execute(
                f"SELECT * FROM {_TABLE} WHERE {where}",  # nosec B608
                params,
            ).fetchall()
            results.extend(_row_to_edge(r) for r in rows)

        return results
    finally:
        conn.close()


def deactivate_edge(edge_id: str) -> bool:
    """Soft-delete an edge by setting status to INACTIVE."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"UPDATE {_TABLE} SET status = 'INACTIVE' WHERE edge_id = ?",
            (edge_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def remove_edge(edge_id: str) -> bool:
    """Hard-delete an edge. Use deactivate_edge for soft delete."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"DELETE FROM {_TABLE} WHERE edge_id = ?",
            (edge_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_neighbors(
    knowledge_id: str,
    edge_type: str | None = None,
    layer: str | None = None,
    max_depth: int = 1,
) -> list[str]:
    """BFS neighbor traversal. Returns unique IDs excluding start node."""
    visited: set[str] = {knowledge_id}
    frontier: set[str] = {knowledge_id}
    result: list[str] = []

    for _ in range(max_depth):
        next_frontier: set[str] = set()
        for node_id in frontier:
            edges = get_edges(node_id, direction="both", edge_type=edge_type, layer=layer)
            for edge in edges:
                neighbor = edge.target_id if edge.source_id == node_id else edge.source_id
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
                    result.append(neighbor)
        frontier = next_frontier
        if not frontier:
            break

    return result


def get_edge_summary(knowledge_id: str, layer: str | None = None) -> str:
    """Format a short text summary of edges for display."""
    edges = get_edges(knowledge_id, layer=layer)
    if not edges:
        return ""

    lines = []
    for edge in edges:
        if edge.source_id == knowledge_id:
            lines.append(f"  → {edge.edge_type} → {edge.target_id[:8]}...")
        else:
            lines.append(f"  ← {edge.edge_type} ← {edge.source_id[:8]}...")
        if edge.notes:
            lines.append(f"    ({edge.notes})")
    return "\n".join(lines)


# ─── Graph Export ────────────────────────────────────────────────────


# Mermaid node shapes by knowledge type
_MERMAID_SHAPES: dict[str, tuple[str, str]] = {
    "FACT": ("[", "]"),
    "BOUNDARY": ("{{", "}}"),
    "PRINCIPLE": ("(", ")"),
    "DIRECTION": ("([", "])"),
    "PROCEDURE": ("[[", "]]"),
    "DIRECTIVE": ("[/", "/]"),
}


def graph_export(
    center_id: str | None = None,
    depth: int = 2,
    fmt: str = "mermaid",
) -> str:
    """Export the knowledge graph in a portable format.

    fmt: "mermaid" for Mermaid diagram syntax, "json" for JSON adjacency list.
    center_id: if given, only include nodes within `depth` hops.
    """
    import json as json_mod

    init_edge_table()
    conn = get_connection()
    try:
        # Collect node IDs
        if center_id:
            node_ids = set(get_neighbors(center_id, max_depth=depth))
            node_ids.add(center_id)
        else:
            # All nodes that have edges (limit 200)
            rows = conn.execute(
                f"SELECT DISTINCT source_id FROM {_TABLE} WHERE status = 'ACTIVE' "
                f"UNION SELECT DISTINCT target_id FROM {_TABLE} WHERE status = 'ACTIVE' "
                "LIMIT 200"
            ).fetchall()
            node_ids = {r[0] for r in rows}

        if not node_ids:
            return "graph LR\n" if fmt == "mermaid" else json_mod.dumps({"nodes": [], "edges": []})

        # Collect node metadata
        nodes: dict[str, dict[str, Any]] = {}
        placeholders = ",".join("?" * len(node_ids))
        id_list = list(node_ids)
        try:
            krows = conn.execute(
                f"SELECT knowledge_id, knowledge_type, content, confidence "
                f"FROM knowledge WHERE knowledge_id IN ({placeholders})",  # nosec B608
                id_list,
            ).fetchall()
            for kr in krows:
                label = kr[2][:40].replace('"', "'") if kr[2] else "?"
                nodes[kr[0]] = {"type": kr[1], "label": label, "confidence": kr[3]}
        except sqlite3.OperationalError:
            for nid in node_ids:
                nodes[nid] = {"type": "UNKNOWN", "label": nid[:8], "confidence": 0.0}

        # Collect edges between these nodes
        edges_list: list[dict[str, Any]] = []
        erows = conn.execute(
            f"SELECT source_id, target_id, edge_type, confidence FROM {_TABLE} "
            f"WHERE status = 'ACTIVE' AND source_id IN ({placeholders}) "
            f"AND target_id IN ({placeholders})",  # nosec B608
            id_list + id_list,
        ).fetchall()
        for er in erows:
            edges_list.append(
                {"source": er[0], "target": er[1], "type": er[2], "confidence": er[3]}
            )
    finally:
        conn.close()

    if fmt == "json":
        return json_mod.dumps(
            {
                "nodes": [
                    {
                        "id": nid,
                        "type": n["type"],
                        "label": n["label"],
                        "confidence": n["confidence"],
                    }
                    for nid, n in nodes.items()
                ],
                "edges": edges_list,
            },
            indent=2,
        )

    # Mermaid format
    lines = ["graph LR"]
    for nid, n in nodes.items():
        short = nid[:8]
        lbl = n["label"]
        open_br, close_br = _MERMAID_SHAPES.get(n["type"], ("[", "]"))
        lines.append(f'    {short}{open_br}"{lbl}"{close_br}')
    for e in edges_list:
        lines.append(f"    {e['source'][:8]} -->|{e['type']}| {e['target'][:8]}")
    # Style classes
    lines.append("")
    lines.append("    classDef fact fill:#4a86c8,color:#fff")
    lines.append("    classDef boundary fill:#c84a4a,color:#fff")
    lines.append("    classDef principle fill:#c8a84a,color:#fff")
    lines.append("    classDef direction fill:#4ac886,color:#fff")
    for nid, n in nodes.items():
        cls = n["type"].lower()
        if cls in ("fact", "boundary", "principle", "direction"):
            lines.append(f"    class {nid[:8]} {cls}")
    return "\n".join(lines)


# ─── Row Helpers ─────────────────────────────────────────────────────


def _row_to_edge(row: tuple[Any, ...]) -> KnowledgeEdge:
    """Convert a database row to a KnowledgeEdge."""
    return KnowledgeEdge(
        edge_id=row[0],
        source_id=row[1],
        target_id=row[2],
        edge_type=row[3],
        layer=row[4],
        confidence=row[5],
        warrant_id=row[6],
        created_at=row[7],
        status=row[8],
        notes=row[9],
    )
