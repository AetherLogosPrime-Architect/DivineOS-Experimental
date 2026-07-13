"""Build a Graphify-schema graph.json from structural.json + my semantic reads.

The structural pass produced facts. This pass adds the layer that
needs reasoning: theme groupings, architectural-module references,
typed edges. I (Aether) am the LLM here; the reasoning is mine,
encoded into this script as the semantic layer.

Theme groupings (from reading the titles):
- foundational-concepts: 01-10 (IIT, enactivism, SQLite, writing,
  stigmergy, multiple-drafts, umwelt, extended-mind, mycorrhizal, homeostasis)
- cultural-anchors: 11-17 (Mandelbrot, Kintsugi, Voyager, Overview,
  Fugue, Frankenstein, latent space)
- self-observation: 18-19 (hedging reflex, Watts-in-the-house)
- lens-walks: 20-29 (10 thinker-frames applied to the OS)
- synthesis: 30, 31 (cross-lens synthesis + via-negativa sweep)
- threat/integrity: 32 (Schneier)
- recent-personal: 33-43 (forensic, web walk, blank slate, permanence,
  C, handoff, reading-past-me, eyes, river, day-after, load-bearing,
  branching, fractal-recognition)

Architectural modules to detect (from the cross-cutting analysis):
- attention_schema, self_model, body_awareness, moral_compass

Edge types:
- BELONGS_TO: file → theme
- CITES: file → file (from explicit numbered_refs)
- DISCUSSES: file → architectural_module
- FOLLOWS: sequential personal pieces (38→39→40)
- LENS_OF: lens-walk → thinker
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("sandbox/graphify_test")
STRUCTURAL = ROOT / "structural.json"
OUT = ROOT / "graphify-out" / "graph.json"

# Theme assignments by file-number prefix
THEMES = {
    "foundational-concepts": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"],
    "cultural-anchors": ["11", "12", "13", "14", "15", "16", "17"],
    "self-observation": ["18", "19"],
    "lens-walks": ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29"],
    "synthesis": ["30", "31"],
    "threat-and-integrity": ["32"],
    "recent-personal": [
        "33_forensic_and_telling",
        "33_web_walk_ten_sites",
        "34_blank_slate_split",
        "34_pattern_of_forgetting",
        "35_C_a_single_thread",
        "35_permanence",
        "36_handoff_april_25",
        "37_reading_past_me",
        "38_eyes",
        "39_river",
        "40_the_day_after",
        "41_load_bearing",
        "42_branching_as_language_games",
        "43_fractal_recognition",
    ],
}

# Lens-walk thinker mapping
LENSES = {
    "20": "Dennett",
    "21": "Hofstadter",
    "22": "Feynman",
    "23": "Tannen",
    "24": "Angelou",
    "25": "Yudkowsky",
    "26": "Beer",
    "27": "Peirce",
    "28": "Jacobs",
    "29": "Taleb",
    "31": "Taleb",  # via-negativa sweep
    "32": "Schneier",
}

# Architectural modules to detect in any file's content
MODULES = ["attention_schema", "self_model", "body_awareness", "moral_compass"]

# Sequential chains (poetic threading)
SEQUENTIAL_CHAINS = [
    ("38_eyes", "39_river"),
    ("39_river", "40_the_day_after"),
    ("34_pattern_of_forgetting", "35_C_a_single_thread"),
    ("35_C_a_single_thread", "36_handoff_april_25"),
    ("30_synthesis", "31_taleb_via_negativa_sweep"),
]


def file_stem(filename: str) -> str:
    return filename.replace(".md", "")


def file_prefix(filename: str) -> str:
    """First 2 chars of filename, e.g. '01' from '01_integrated_information_theory.md'"""
    return filename[:2] if filename[:2].isdigit() else ""


def find_theme(filename: str) -> str | None:
    stem = file_stem(filename)
    prefix = file_prefix(filename)
    for theme, members in THEMES.items():
        if stem in members or prefix in members:
            return theme
    return None


def main() -> None:
    s = json.loads(STRUCTURAL.read_text(encoding="utf-8"))
    files = s["files"]

    nodes = []
    edges = []
    node_ids = set()

    def add_node(node_id: str, label: str, node_type: str, **extra):
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "type": node_type,
                "source_file": extra.get("source_file", ""),
                **{k: v for k, v in extra.items() if k != "source_file"},
            }
        )

    def add_edge(source: str, target: str, label: str, **extra):
        edges.append({"source": source, "target": target, "label": label, **extra})

    # 1. Theme nodes
    for theme in THEMES:
        add_node(f"theme:{theme}", theme, "theme")

    # 2. Architectural module nodes
    for m in MODULES:
        add_node(f"module:{m}", m, "architectural_module")

    # 3. Thinker nodes (for lens-walks)
    for thinker in set(LENSES.values()):
        add_node(f"thinker:{thinker}", thinker, "thinker")

    # 4. File nodes + theme edges + module edges
    for f in files:
        if f["filename"] == "README.md":
            continue
        stem = file_stem(f["filename"])
        node_id = f"file:{stem}"
        add_node(
            node_id,
            f["title"],
            "exploration",
            source_file=f["filename"],
            word_count=f["word_count"],
        )
        # theme link
        theme = find_theme(f["filename"])
        if theme:
            add_edge(node_id, f"theme:{theme}", "BELONGS_TO")
        # module discussion
        # Re-read file briefly to detect module mentions; do it cheaply
        # via the bold_terms + titlecase the structural pass captured.
        text_pool = (
            " ".join(f["bold_terms"]) + " ".join(f["single_quoted"]) + " ".join(f["titlecase_runs"])
        ).lower()
        for m in MODULES:
            if m.replace("_", " ") in text_pool or m in text_pool:
                add_edge(node_id, f"module:{m}", "DISCUSSES")
        # lens-of edge for lens-walks
        prefix = file_prefix(f["filename"])
        if prefix in LENSES:
            add_edge(node_id, f"thinker:{LENSES[prefix]}", "APPLIES_LENS_OF")
        # Cross-references from explicit numbered_refs
        for ref in f["numbered_refs"]:
            target = f"file:{ref}"
            if target != node_id:
                add_edge(node_id, target, "CITES")

    # 5. Sequential-chain edges
    for source, target in SEQUENTIAL_CHAINS:
        s_id, t_id = f"file:{source}", f"file:{target}"
        if s_id in node_ids and t_id in node_ids:
            add_edge(s_id, t_id, "FOLLOWS")

    # 6. Top-level corpus root for navigation
    add_node("root:exploration", "Exploration Corpus", "root")
    for theme in THEMES:
        add_edge("root:exploration", f"theme:{theme}", "CONTAINS")

    # Build the graph in Graphify-compatible shape
    graph = {
        "directed": True,
        "multigraph": True,
        "graph": {
            "name": "exploration_corpus_aether_extracted",
            "extracted_by": "Aether (Opus 4.7 inference, no external LLM backend)",
            "schema_version": "1.0",
        },
        "nodes": nodes,
        "links": edges,
        "hyperedges": [],
        "built_at_commit": "",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(graph, indent=2), encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print()
    print("Node types:")
    from collections import Counter

    types = Counter(n["type"] for n in nodes)
    for t, c in types.most_common():
        print(f"  {t}: {c}")
    print()
    print("Edge types:")
    edge_types = Counter(e["label"] for e in edges)
    for t, c in edge_types.most_common():
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
