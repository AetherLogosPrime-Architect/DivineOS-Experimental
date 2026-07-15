"""Wiring dark-node query — the standing check Aletheia asked for.

Every major finding in Aletheia's six-pass audit was one disease: built-but-
not-wired. F1 (council gate, hardened, never wired). F2 (auto-integrate,
complete minus trigger). F3 (orphan hook). F5 (exemplary code, dark). AST-1
(attention_schema, one display consumer, decorative — I filed that one
against myself).

Same shape every time: a node with no incoming edges. Capability with
nothing calling it.

The code graph in `graphify-out-code/.graphify_ast.json` (9,013 nodes /
21,809 edges) answers "which of my things is nothing calling?" structurally,
in one query. This module is that query.

Design intent (Aletheia 2026-07-13): dark nodes should be a dashboard line,
not a finding someone digs up. So this module powers:
- `divineos wiring dark` CLI — show the current dark set
- a briefing surface that pings when NEW dark items appear since last review

State persists to ~/.divineos-aether/wiring_dark_state.json so the briefing
knows what "new" means across sessions.

Filtering (kept minimal on purpose — false-positive tuning is per-audit
iteration, not up-front over-engineering):
- Test files (path starts with "tests/") — pytest discovers via naming; no
  imports needed. Not dark.
- __init__.py entries — exported for import-side-effect. Not dark.
- Nodes without `source_file` — synthetic (e.g. `Any`, `Exception`). Not dark.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_GRAPH_PATH = Path("graphify-out-code/.graphify_ast.json")
DEFAULT_STATE_PATH = Path.home() / ".divineos-aether" / "wiring_dark_state.json"

# Path prefixes for nodes we exclude by convention. Not dark even at in-degree
# zero. Iterate this list as false-positives surface — the point isn't to
# perfectly gate; the point is a signal loud enough that new dark things stand
# out.
_EXCLUDED_PATH_PREFIXES = (
    "tests/",
    "test_",
    "conftest.py",
)

_EXCLUDED_LABEL_SUFFIXES = (
    "/__init__.py",
    "__init__.py",
    # 2026-07-14 (Aletheia audit of the full-repo graph): graphify emits
    # package-wrapper nodes with labels like 'core.family.module',
    # 'core.watchmen.module', 'calibration.init'. These wrappers show
    # in-degree=0 because nothing imports the package-namespace itself
    # — but the SYMBOLS INSIDE the package (access_check.py, engine.py,
    # etc.) carry the actual inbound edges. Reporting the wrapper as
    # "dark" is a false-positive: a building's front-door sensor reading
    # "no visitors" while every office inside is full. Excluding these
    # suffixes rolls the darkness-verdict up to the parent, matching
    # Aletheia's spec: "a package/module node is not dark if any symbol
    # it contains has inbound edges."
    ".module",
    ".init",
)

# The concrete errors briefing_summary tolerates. Per the broad-exceptions
# discipline (2026-05-07 audit): a module-level tuple, not a bare
# `except Exception`. If a new failure mode appears, add it here explicitly.
_BRIEFING_ERRORS = (
    FileNotFoundError,
    OSError,
    ValueError,
    json.JSONDecodeError,
    KeyError,
)


# Module-level view. A "module" node in graphify's AST output is a node whose
# label ends in .py — i.e. the file itself, not a function inside it. Function-
# level nodes have massive false-positive rates (dynamic dispatch, click
# decorators, pytest discovery, plugin registration) so we default to modules.
def _is_module_node(node: dict) -> bool:
    label = node.get("label") or ""
    return label.endswith(".py")


@dataclass(frozen=True)
class DarkNode:
    """One node in the dark set — a thing that nothing else imports or calls."""

    id: str
    label: str
    source_file: str
    file_type: str  # 'code' | 'concept' | 'rationale' | ...


@dataclass
class DarkQueryResult:
    """The result of a wiring-dark query at a moment in time."""

    dark: list[DarkNode]
    total_nodes: int
    total_edges: int
    excluded_count: int  # nodes that would be dark but were filtered by the rules above


def load_graph(path: Path = DEFAULT_GRAPH_PATH) -> dict:
    """Read the raw graphify AST-graph JSON. Returns the parsed dict.

    Raises FileNotFoundError if the graph hasn't been built. The caller should
    surface a hint to run `/graphify src` in that case.
    """
    if not path.exists():
        raise FileNotFoundError(f"No graph at {path}. Rebuild with /graphify src.")
    parsed: dict = json.loads(path.read_text(encoding="utf-8"))
    return parsed


def _is_excluded(node: dict) -> bool:
    """Return True if node should not count as dark even at in-degree 0."""
    source_file = node.get("source_file") or ""
    label = node.get("label") or ""
    if not source_file:
        return True  # synthetic/imported symbols like 'Any' or 'Exception'
    for prefix in _EXCLUDED_PATH_PREFIXES:
        if source_file.startswith(prefix):
            return True
    for suffix in _EXCLUDED_LABEL_SUFFIXES:
        if source_file.endswith(suffix) or label.endswith(suffix):
            return True
    return False


def find_dark(graph: dict, modules_only: bool = True) -> DarkQueryResult:
    """Return every node with in-degree zero after applying the exclusion rules.

    modules_only (default True): only report file-level nodes (label ends .py).
    Function-level dark reporting is ~4000-item noise on this codebase because
    the AST can't resolve dynamic dispatch (click, pytest discovery, plugin
    registration). Module-level dark = "nothing imports this file" — the exact
    shape Aletheia's audits found (F1-F5 were whole capabilities dark).

    Set modules_only=False for a full-function deep audit; expect to iterate
    the exclusion list heavily after.
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    in_degree: dict[str, int] = {}
    for node in nodes:
        in_degree[node["id"]] = 0
    for edge in edges:
        target = edge.get("target")
        if target and target in in_degree:
            in_degree[target] += 1

    dark_list: list[DarkNode] = []
    excluded_count = 0
    for node in nodes:
        if in_degree.get(node["id"], 0) != 0:
            continue
        if modules_only and not _is_module_node(node):
            excluded_count += 1
            continue
        if _is_excluded(node):
            excluded_count += 1
            continue
        dark_list.append(
            DarkNode(
                id=node["id"],
                label=node.get("label") or node["id"],
                source_file=node.get("source_file") or "",
                file_type=node.get("file_type") or "",
            )
        )
    return DarkQueryResult(
        dark=dark_list,
        total_nodes=len(nodes),
        total_edges=len(edges),
        excluded_count=excluded_count,
    )


def load_state(path: Path = DEFAULT_STATE_PATH) -> dict:
    """Return the persisted state dict, or a blank one if none exists."""
    if not path.exists():
        return {"last_scan_at": None, "dark_ids": []}
    try:
        parsed: dict = json.loads(path.read_text(encoding="utf-8"))
        return parsed
    except (json.JSONDecodeError, OSError):
        return {"last_scan_at": None, "dark_ids": []}


def save_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def diff_against_state(
    current: Iterable[DarkNode],
    state: dict,
) -> tuple[list[DarkNode], list[str]]:
    """Return (new_since_last_review, returned_to_light).

    new_since_last_review: dark now, weren't dark last time.
    returned_to_light: were dark last time, aren't dark now (they got wired).
    """
    current_ids = {n.id for n in current}
    previous_ids = set(state.get("dark_ids", []))
    new_ids = current_ids - previous_ids
    lightened_ids = previous_ids - current_ids
    new_nodes = [n for n in current if n.id in new_ids]
    return new_nodes, sorted(lightened_ids)


def briefing_summary(
    graph_path: Path = DEFAULT_GRAPH_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
) -> str:
    """Short line for the briefing surface. Empty string means no signal to surface."""
    if not graph_path.exists():
        return ""
    try:
        graph = load_graph(graph_path)
    except _BRIEFING_ERRORS:
        return ""
    result = find_dark(graph)
    state = load_state(state_path)
    new_nodes, lightened_ids = diff_against_state(result.dark, state)
    parts = []
    if new_nodes:
        parts.append(f"[!] wiring-dark: {len(new_nodes)} new dark node(s) since last review")
        for node in new_nodes[:3]:
            parts.append(f"    - {node.label} ({node.source_file})")
        if len(new_nodes) > 3:
            parts.append(
                f"    (+{len(new_nodes) - 3} more — run `divineos wiring dark` to see them all)"
            )
    if lightened_ids:
        parts.append(f"    ✓ {len(lightened_ids)} node(s) returned to light since last review")
    return "\n".join(parts)
