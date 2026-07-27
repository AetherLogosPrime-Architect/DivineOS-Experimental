# PandaClip — Intake

**Repo:** https://github.com/xfloukiex-lab/pandaclip
**Owner:** xfloukiex-lab (Andrew's friend, offered reciprocal audit exchange)
**License:** Apache-2.0
**Language:** TypeScript
**Created:** 2026-07-12 (~2 weeks old at time of audit)
**Last updated:** 2026-07-14
**Stars:** 4 · **Forks:** 0 · **Size:** 1.66 MB · **Open issues:** 0

---

## What the project is

Local-first MCP server for AI agent working state + a desktop activity lens (Electron). Single server with **four tool families** exposing **40 tools total**. No cloud, no daemons, SQLite everywhere.

**Positioning by the author** (from README): *"One local-first MCP server for agent working state — clipboard history & snippets, TTL cache, file-organizer overlay, and a knowledge graph — plus a live desktop activity lens."*

## Four tool families

| Family | Tools | What it does |
|---|---|---|
| 📋 clipboard | `clip_*`, `snippet_*`, `channel_*` | Clipboard history (TTL classes, tag/contains filters), permanent named snippets, channel label-lanes, secret screening |
| ⚡ cache | `cache_*` | Namespaced cache with TTLs, canonical hash keys, invalidation, stats |
| 🎋 bamboo | `workspace_*`, `entry_*`, `stalk_*`, `bamboo_find`, `organize_scan` | Contextual file organizer overlay: tags, notes, metadata on files you already have — nothing moved or copied |
| 🌱 garden | `garden_*` | Knowledge graph: plant/grow/prune nodes, typed edges, BFS traverse, per-node history |

## Architectural core

- Single stdio MCP server (TypeScript)
- Every tool is a small deterministic operation on plain SQLite
- One store per family under `~/.panda/<area>/` (overridable via `PANDA_HOME`)
- WAL mode, no background daemons, no network
- Nothing happens unless a tool is called (pull model)
- Secret screening: obvious keys/tokens refused before storage

## Desktop lens (bamboo-clipboard-ui)

Electron app that provides a live, read-only feed of what agents are doing. Watches PandaClip's own stores + three configurable "blank slot" sources. Read-only watcher child running on system Node >= 22.5 (needs `node:sqlite`'s WAL-aware reads). Server stays sole writer; lens can only look.

## Structural layout

```
apps/         — Electron desktop lens (bamboo-clipboard-ui)
servers/      — MCP server(s)
packages/     — shared library packages (monorepo)
examples/     — usage examples
.github/      — CI, workflows
package.json  — monorepo root
tsconfig.base.json — shared TS config
CHANGELOG.md  — release notes
```

Note: appears to be a **monorepo** with apps + servers + packages structure.

## Ecosystem signals

- Published under `@vektorgeist/pandaclip` (npm scope)
- Newer project (2 weeks) — early adoption phase
- Topics: agents, ai, cache, claude, claude-code, clipboard, developer-tools, electron, knowledge-graph, local-first, mcp, mcp-server, model-context-protocol, sqlite, typescript

## Sibling relationship to Magpie

Same author. Both local-first, SQLite-based, MCP-server-based, serving AI agent workflows. **Magpie** = search across all sources of AI working memory. **PandaClip** = immediate working state (clipboard, cache, files-in-place, knowledge graph). Clear shared architectural vision: agent-native local-first tooling ecosystem.

## Scope of this audit

Same discipline as Magpie audit — question-quality-forward framing, "how do we help this succeed" primary. Author owns their substrate. Recommendations offered, not prescribed.

## Audit steps (to be executed)

1. Deep-read source code (monorepo structure: start with servers/, then packages/, then apps/)
2. Council walk with all relevant lenses per council-usage guide
3. Findings: architectural observations, gaps, opportunities
4. Recommendations: constructive, in author's language
5. Cross-project observation: how magpie and pandaclip fit together (or don't) as a suite
