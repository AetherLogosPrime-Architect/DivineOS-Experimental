# graphify-out — machine-generated map of the OS

**This directory is for AI review, not human review.**

Large by design. An AI reading this repo should start here rather than paying
full semantic-extraction cost across 620+ code files and 200+ writing entries.

Filed by Aletheia (2026-07-13, boundary-vantage) after Andrew corrected the
initial reflex to gitignore generated artifacts: *"it's not for human review
anyway, it's for AI review. Everyone who is using AI, or would even look at
my repo, is likely never going to look at it themselves — they'd have another
AI scan it and report back."*

The graph is hospitality. It's the same gesture as a briefing for Aether or an
INBOX for Aletheia: *here's the map, so you don't have to hold the whole house
in your head.*

---

## Layout

- `../graphify-out-code/` — code call-graph of `src/` (9,013 nodes, 21,809 edges)
  - `graph.json` — the queryable data. This is the instrument.
  - `graph.html` — human-viewable interactive view (community-aggregated at that node count).
  - `GRAPH_REPORT.md` — plain-language god-nodes, surprising connections, suggested questions.
- `../graphify-out-writing/` — knowledge graph of `exploration/` (311 nodes, 203 edges)
  - Same three files.

The `.json` files are the load-bearing artifact. The `.html` files are for glancing at.
The `.md` reports are for orienting.

---

## What the graph answers cheaply

The single most recurring finding across Aletheia's six-pass audit was one disease: **built-but-not-wired.** F1 (council gate, hardened, never wired). F2 (auto-integrate, complete minus trigger). F3 (orphan hook). F5 (exemplary code, dark). AST-1 (attention_schema, one display consumer, decorative).

Same shape every time: **a node with no incoming edges.**

The graph answers that structurally, in one query:

```
nodes with in-degree 0  →  every dark thing in the OS
```

Exhaustive. Zero false positives. Runnable every audit, forever. E2 (meta-monitoring) + E4 (detector registry) enhancements from Aletheia's pass, realized as a query against a committed graph rather than a new detector.

---

## Regenerating

Rebuild code graph:

```bash
/graphify src
```

Rebuild writing graph:

```bash
/graphify exploration
```

Both take a few minutes; the code path is AST-only (deterministic, no LLM calls); the writing path uses semantic extraction (subagents on this substrate, or Gemini if `GEMINI_API_KEY` is set).

---

## Why the diffs are enormous and why that is fine

`graph.json` for the code graph is ~11MB; `graph.html` is ~400KB minified.
Both files are declared `linguist-generated=true` in `.gitattributes`, so GitHub
collapses them in PR diffs. The map ships, the reviewable diff stays legible.

If you see a large `graphify-out*/` change in a diff, it's a regeneration,
not hand-authored code. That's the sign on the door.
