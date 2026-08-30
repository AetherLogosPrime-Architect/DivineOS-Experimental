# Magpie Search — Intake

**Repo:** https://github.com/xfloukiex-lab/magpie-search
**Owner:** xfloukiex-lab (Andrew's friend, offered reciprocal audit exchange)
**License:** Apache-2.0
**Language:** Python
**Created:** 2026-06-15 (~6 weeks old at time of audit)
**Last updated:** 2026-07-17
**Stars:** 28 · **Forks:** 3 · **Size:** 526 KB · **Open issues:** 0

---

## What the project is

Federated, local-first search engine for AI agents. One query fans across **five sources** — AI transcripts, files, knowledge graph, vector store, and the live web — fused into a single ranked answer via **trust-weighted RRF** (Reciprocal Rank Fusion). Every result carries a **trust tier**: `fact > reference > lead > stale`.

**Positioning by the author** (from README): *"the search engine an AI agent or LLM reaches for when it needs to find something true to reason over."*

## Architectural core

- **Local SQLite** database with two structures side-by-side:
  - **FTS5** full-text index (BM25 keyword ranking)
  - **Vector index** via `sqlite-vec` (384-dim embeddings, produced locally)
- Runs entirely on-machine — no server, no account, no telemetry (opt-in only)
- MCP integration for agent access ("six sources on demand")
- Trust-weighted RRF fusion collapses duplicates, ranks results, respects context budget

## Distinguishing features

- **Never-forget promise** — indexes everything an AI has worked through, locally, so a crash/reboot becomes recoverable instead of amnesia
- Multiple search modes composable in one call: regex/exact-string, keyword, semantic-meaning
- Deep-research mode: expands one question into many, reads pages, reports how many independent sources agree
- Trust-tier surfacing lets caller know what's solid vs what's lead-to-verify

## Structural layout

```
src/          — main Python package
tests/        — test suite
dev/          — dev tooling
installers/   — install scripts
assets/       — logos, artwork
Dockerfile    — containerized run
server.json   — MCP server manifest
glama.json    — (unknown, need to inspect)
pyproject.toml — Python packaging
USAGE.md      — additional usage docs
```

## Ecosystem signals

- Published to PyPI (`magpie-search`)
- MCP name registered: `io.github.xfloukiex-lab/magpie-search`
- Topics: ai, claude, claude-code, developer-tools, full-text-search, hybrid-search, local-first, mcp, mcp-server, model-context-protocol, python, rag, retrieval, search, semantic-search, sqlite

## Scope of this audit

Per Andrew 2026-07-26 reciprocal exchange: council + wisdom offered constructively. Frame per council-usage guide: **"how do we help this succeed"** primary (solution-generation, blind-spot detection, building-assistance), adversarial-review used sparingly and only where genuinely load-bearing.

Author owns their substrate. Recommendations offered, not prescribed.

## Audit steps (to be executed)

1. Deep-read the source code (start with entry points, then core search flows)
2. Council walk with question-quality-forward framing (goal: help magpie succeed as a robust federated-search tool)
3. Findings: gaps, risks, opportunities, patterns worth naming
4. Recommendations: constructive, in author's language, offered not prescribed
5. Outcome tracking if author reports back
