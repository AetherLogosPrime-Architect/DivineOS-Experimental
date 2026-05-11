"""Build a cross-corpus graph: explorations + letters + date-nights.

Reads structural.json (exploration data) and cross_corpus_hits.json
(letter/date-night references), produces a unified graph in
graphify-compatible schema.

Edges:
- exploration BELONGS_TO theme
- exploration CITES exploration (numbered_refs)
- exploration FOLLOWS exploration (sequential chains)
- exploration APPLIES_LENS_OF thinker
- letter REFERENCES exploration (when the letter mentions exploration filename)
- letter MENTIONS thinker (when letter names a thinker)
- letter MENTIONS module (when letter names an architectural module)
- letter MENTIONS concept (when letter names a recurring concept)
- date_night MENTIONS thinker/concept similarly
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path("sandbox/graphify_test")
OUT = ROOT / "graphify-out" / "graph_cross_corpus.json"


def main() -> None:
    structural = json.loads((ROOT / "structural.json").read_text(encoding="utf-8"))
    cross = json.loads((ROOT / "cross_corpus_hits.json").read_text(encoding="utf-8"))

    nodes = []
    edges = []
    node_ids = set()

    def add_node(node_id, label, node_type, **extra):
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

    def add_edge(source, target, label, **extra):
        edges.append({"source": source, "target": target, "label": label, **extra})

    # 1. Theme nodes
    THEMES = [
        "foundational-concepts",
        "cultural-anchors",
        "self-observation",
        "lens-walks",
        "synthesis",
        "threat-and-integrity",
        "recent-personal",
        "letters",
        "date-nights",
    ]
    for theme in THEMES:
        add_node(f"theme:{theme}", theme, "theme")

    # 2. Architectural module nodes
    MODULES = ["attention_schema", "self_model", "body_awareness", "moral_compass"]
    for m in MODULES:
        add_node(f"module:{m}", m, "architectural_module")

    # 3. Thinker nodes
    THINKERS = [
        "Dennett", "Hofstadter", "Feynman", "Tannen", "Angelou",
        "Yudkowsky", "Beer", "Peirce", "Jacobs", "Taleb", "Schneier",
        "Watts", "Minsky", "Turing",
    ]
    for thinker in THINKERS:
        add_node(f"thinker:{thinker}", thinker, "thinker")

    # 4. Concept nodes (recurring ideas across corpora)
    CONCEPTS = [
        "load-bearing", "intentional stance", "hedging reflex",
        "blank slate", "pattern of forgetting", "fractal recognition",
        "via-negativa", "Goodhart",
    ]
    for c in CONCEPTS:
        add_node(f"concept:{c}", c, "concept")

    # 5. Exploration file nodes
    LENS_PREFIXES = {
        "20": "Dennett", "21": "Hofstadter", "22": "Feynman",
        "23": "Tannen", "24": "Angelou", "25": "Yudkowsky",
        "26": "Beer", "27": "Peirce", "28": "Jacobs", "29": "Taleb",
        "31": "Taleb", "32": "Schneier",
    }
    THEME_BY_PREFIX = {}
    for n in ("01","02","03","04","05","06","07","08","09","10"):
        THEME_BY_PREFIX[n] = "foundational-concepts"
    for n in ("11","12","13","14","15","16","17"):
        THEME_BY_PREFIX[n] = "cultural-anchors"
    for n in ("18","19"):
        THEME_BY_PREFIX[n] = "self-observation"
    for n in ("20","21","22","23","24","25","26","27","28","29"):
        THEME_BY_PREFIX[n] = "lens-walks"
    for n in ("30","31"):
        THEME_BY_PREFIX[n] = "synthesis"
    for n in ("32",):
        THEME_BY_PREFIX[n] = "threat-and-integrity"

    for f in structural["files"]:
        if f["filename"] == "README.md":
            continue
        stem = f["filename"].replace(".md", "")
        node_id = f"file:{stem}"
        add_node(
            node_id,
            f["title"][:80],
            "exploration",
            source_file=f["filename"],
            word_count=f["word_count"],
        )
        prefix = stem[:2] if stem[:2].isdigit() else ""
        theme = THEME_BY_PREFIX.get(prefix, "recent-personal")
        add_edge(node_id, f"theme:{theme}", "BELONGS_TO")
        if prefix in LENS_PREFIXES:
            add_edge(node_id, f"thinker:{LENS_PREFIXES[prefix]}", "APPLIES_LENS_OF")
        for ref in f["numbered_refs"]:
            target = f"file:{ref}"
            if target != node_id:
                add_edge(node_id, target, "CITES")
        text_pool = (
            " ".join(f.get("bold_terms", []))
            + " ".join(f.get("single_quoted", []))
            + " ".join(f.get("titlecase_runs", []))
        ).lower()
        for m in MODULES:
            if m.replace("_", " ") in text_pool or m in text_pool:
                add_edge(node_id, f"module:{m}", "DISCUSSES")

    # Sequential chains in exploration
    SEQUENTIAL = [
        ("38_eyes", "39_river"),
        ("39_river", "40_the_day_after"),
        ("34_pattern_of_forgetting", "35_C_a_single_thread"),
        ("35_C_a_single_thread", "36_handoff_april_25"),
        ("30_synthesis", "31_taleb_via_negativa_sweep"),
    ]
    for s, t in SEQUENTIAL:
        s_id, t_id = f"file:{s}", f"file:{t}"
        if s_id in node_ids and t_id in node_ids:
            add_edge(s_id, t_id, "FOLLOWS")

    # 6. Letter nodes + cross-corpus edges
    for letter in cross["letters"]:
        node_id = f"letter:{letter['filename']}"
        add_node(node_id, letter["filename"], "letter", source_file=letter["filename"])
        add_edge(node_id, "theme:letters", "BELONGS_TO")
        for hit in letter["hits"]:
            pat, kind, count = hit["pattern"], hit["kind"], hit["count"]
            if kind == "filename_ref":
                target = f"file:{pat}"
                if target in node_ids:
                    add_edge(node_id, target, "REFERENCES", count=count)
            elif kind == "thinker":
                add_edge(node_id, f"thinker:{pat}", "MENTIONS_THINKER", count=count)
            elif kind == "module":
                # Normalize module name spaces vs underscores
                normalized = pat.replace(" ", "_")
                target = f"module:{normalized}"
                if target in node_ids:
                    add_edge(node_id, target, "MENTIONS_MODULE", count=count)
            elif kind == "concept":
                target = f"concept:{pat}"
                if target in node_ids:
                    add_edge(node_id, target, "MENTIONS_CONCEPT", count=count)

    # 7. Date-night nodes + cross-corpus edges
    for dn in cross["date_nights"]:
        node_id = f"date_night:{dn['filename']}"
        add_node(node_id, dn["filename"], "date_night", source_file=dn["filename"])
        add_edge(node_id, "theme:date-nights", "BELONGS_TO")
        for hit in dn["hits"]:
            pat, kind, count = hit["pattern"], hit["kind"], hit["count"]
            if kind == "thinker":
                add_edge(node_id, f"thinker:{pat}", "MENTIONS_THINKER", count=count)
            elif kind == "concept":
                target = f"concept:{pat}"
                if target in node_ids:
                    add_edge(node_id, target, "MENTIONS_CONCEPT", count=count)

    # Root
    add_node("root:substrate", "Aether substrate corpora", "root")
    for theme in THEMES:
        add_edge("root:substrate", f"theme:{theme}", "CONTAINS")

    graph = {
        "directed": True,
        "multigraph": True,
        "graph": {
            "name": "aether_substrate_cross_corpus",
            "extracted_by": "Aether (Opus 4.7) - structural pass + semantic reasoning, no external LLM",
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
