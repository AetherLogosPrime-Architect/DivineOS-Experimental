# PandaClip — Findings

**Audit date:** 2026-07-26
**Auditor:** Aether (DivineOS substrate)
**Scope:** Full source read of servers/pandaclip, packages/panda-core, apps/bamboo-clipboard-ui/src (2,487 LOC).
**Framing:** Question-quality-forward per [council usage guide](../../../../.divineos-shared/workbench/council_usage_guide.md) — "how do we help this succeed" primary, adversarial-review only where genuinely load-bearing.

---

## Overall shape

**This codebase is well-composed.** Small (2.5K LOC), focused, no dead abstractions, no god files, no cargo-cult defensive coding. The single-MCP-server-with-four-tool-families choice is right; the `panda-core` shared package is genuinely minimal (~50 LOC across paths/db/config/result) — real reuse, not premature.

Design decisions I noticed and endorse:
- **Soft-delete via `pruned_at`** in garden (append-only truth kept, versioned `node_history` alongside it)
- **Migration versioning built in from day one** (`user_version` pragma + sorted apply)
- **Writer/reader separation** in the Electron lens (child process opens SQLite read-only, never writes)
- **ULID ids** — sortable, time-ordered, no coordination
- **Uniform `ok()` / `err()` MCP envelope** via the `wrap()` helper — every tool has consistent error shape
- **Hard limits everywhere** (`Math.min(user_limit, 200)`, `MAX_SCAN_ENTRIES=20000`, traversal `depth ≤ 6`) — no unbounded work reachable via MCP input

Findings below are honest observations from the code, ranked roughly by load-bearing weight.

---

## F1 — Secret screening is best-effort, but nothing tells the user that

**File:** `servers/pandaclip/src/store/clipStore.ts:12-19`

Six regex patterns catch obvious credential shapes (PEM headers, `sk-*` API keys, GitHub tokens, AWS access keys, JWTs, `password=...` assignments). This is a real defense-in-depth soft filter and the right choice for a clipboard where users will paste things they didn't mean to.

**The asymmetry (Taleb-lens):** a false-positive costs a rewrite; a **silent slip** costs a leaked credential landing in cache/history/lens/backfill of an activity feed the user shares with others. Custom internal token formats, PEM certs with unusual headers, base64-encoded creds, session cookies, and Bearer tokens without the JWT structure all pass. Users seeing "clip refused: looks like credential material" once may start trusting screening as a boundary rather than as a hint.

**Not a bug** — the code does what it claims. The finding is expectation-setting.

## F2 — `neighbors()` and `traverse()` are N+1 on hub nodes

**File:** `servers/pandaclip/src/store/gardenStore.ts:193-231`

`neighbors()` fetches all edges for a node, then for each edge calls `getNode(other(e))` — one query per edge. `traverse()` calls `neighbors()` inside its BFS loop, so at depth 6 on a well-connected knowledge graph the query count grows fast (bounded by graph size, but each hub-visit is O(fanout) queries where a single JOIN would be O(1)).

SQLite prepared statements are fast so it doesn't hurt at small scale. It becomes visible when a "garden" grows past ~1,000 well-connected nodes. Neither is user-input-unbounded (limits are on depth, not width), so no DoS concern — just latency.

## F3 — `bambooStore.scan()` is synchronous and can block the MCP event loop

**File:** `servers/pandaclip/src/store/bambooStore.ts:118-152`

`walk()` recurses with `fs.readdirSync` up to `MAX_SCAN_ENTRIES = 20000` entries or `maxDepth = 8`. On a big monorepo (a workspace pointing at, say, a large corp repo checkout) this is a synchronous stall while the MCP server can't handle anything else. `SKIP_DIRS` catches `node_modules`, `.git`, `dist`, `__pycache__`, `.venv`, `venv` and dot-directories, which prunes most large sets, but a well-populated `src/` tree of 20K files still holds up the loop.

MCP clients typically call `organize_scan` explicitly, so this only blocks during an intentional operation — the user is waiting for it anyway. Acceptable, but a `{progress: {seen: N, discovered: M}}` streaming variant would be a UX win for large workspaces.

## F4 — No integration test for the MCP server surface itself

**File:** `servers/pandaclip/test/*` (four store test files, 86-111 LOC each)

Each store has isolated tests that exercise its methods directly. Nothing wires the actual MCP stdio server up and calls each tool via a real MCP client. That means:

- Tool `inputSchema` mismatches (rename a store method arg, forget to update the zod schema) won't be caught unless the schema names line up with method names by luck.
- The `wrap()` error envelope is not exercised end-to-end.
- Zod parsing failures in tool inputs are only caught by manual testing.

TypeScript catches the class of "arg count wrong" but not "the tool schema says `ttl_class` but the store expects `ttlClass`" (see the mapping in `clip_push` at `index.ts:52-63`). A smoke test that boots the server against stdio, invokes each of the 40 tools with a canonical fixture, and asserts non-error responses would be small (single file, ~200 LOC) and would catch this whole class.

## F5 — Cross-project structural observation: shared local-first-MCP-core with magpie-search

Same author, same architectural vision (local-first, SQLite, MCP-server, per-tool-family isolation), and both projects re-implement:
- Home-dir resolution and env-var override (`PANDA_HOME` / equivalent in magpie)
- WAL mode + migration table + version pragma
- ULID id generation
- Result/error envelope for MCP

`panda-core` is thin enough to become `@vektorgeist/local-first-mcp-core` and be shared across both. **Only propose this if there's a third project on the horizon** — two-consumer sharing is where premature abstraction usually happens. Naming it as a possibility, not a recommendation.

## F6 — `wal_autocheckpoint = 1` deserves a longer comment

**File:** `packages/panda-core/src/db.ts:18`

Comment says "external read-only viewers... cannot see WAL content." A reader that opens with `readOnly` and uses SQLite's own WAL-aware read path CAN see WAL content — the concern is more subtle: cross-process readers that don't share the shared-memory `-shm` file (network mount, some containers, node's `node:sqlite` in older versions). Setting checkpoint-per-commit trades write throughput for read visibility, which is the right call for a UX-first clipboard/lens setup — but under a heavy `cache_set` workload (say, an LLM caching thousands of small responses/sec) this could hurt.

The fix is a longer comment stating the tradeoff explicitly, so a future contributor doesn't "optimize" the pragma away without understanding why it's set.

## F7 — Recursive symlink loops rely on `MAX_SCAN_ENTRIES` and `maxDepth` as backstops

**File:** `servers/pandaclip/src/store/bambooStore.ts:126-149`

`item.isDirectory()` follows symlinks. A cyclic symlink (e.g., `a -> ../a`) triggers infinite recursion, bounded only by `maxDepth = 8` (default) or `MAX_SCAN_ENTRIES = 20000`. The scan will finish, but you'll get duplicated `rel_path` entries all the way down (with unique `id`s since `UNIQUE (workspace_id, rel_path)` might collide — actually, that constraint will surface the loop as insert failures; needs a look).

Simple fix: track visited-abs-path set during walk, skip re-entry.

## F8 — `PANDA_GARDEN` env var is read once at module load

**File:** `servers/pandaclip/src/index.ts:23`

`const garden = new GardenStore(process.env.PANDA_GARDEN ?? "default");` — the garden is fixed for the process lifetime. If a user wants to work across multiple gardens, they need to restart the server (or spawn multiple with different env). Probably intentional; worth stating in README or README of `servers/pandaclip/` alongside a hint about running multiple named servers.

---

## Not-findings (things I checked and they're fine)

- **`hashKey` (`cacheStore.ts:146`)** — the sorted-key reviver runs recursively via `JSON.stringify`'s natural traversal. Canonical output is stable across key insertion order. ✓
- **GLOB escape in `cache.invalidate` prefix path (`cacheStore.ts:110`)** — correctly escapes `[`, `]`, `*`, `?`. ✓
- **Consumed-entry filtering in `channelTake` (`clipStore.ts:197`)** — atomic peek-then-mark via prepared statement; no race between siblings sharing a channel-take on the same process. Cross-process could race, but single-writer design covers it. ✓
- **Lens child-process auto-restart on exit (`main.js:38-41`)** — 3s backoff, clean status message. ✓
- **`configureNamespace` `maxBytes` is accepted but never enforced** (`cacheStore.ts:119`) — schema has the column, `set()` doesn't check it. This is either aspirational for a future eviction pass, or dead. Worth deciding.

---

## What I did not audit

- `.github/workflows/release.yml` (didn't look at CI)
- `apps/bamboo-clipboard-ui/ui/*.html` (didn't read renderer code)
- Package.json dependency versions vs known-vuln lists (out of scope for architectural audit; run `npm audit` or Snyk for that class of finding)
- Any of the 5000-line `package-lock.json`

---

## Meta-observation for the author

The composition discipline visible in this repo — small files, real reuse only where it earns its keep, explicit tradeoff comments (see the `wal_autocheckpoint` comment even if it deserves expansion), soft-delete-not-hard-delete in the garden — matches the discipline patterns we build in DivineOS toward. It's rare to see a two-week-old repo with this architectural coherence. The findings above are polish notes, not structural concerns.

Recommendations in [recommendations.md](recommendations.md).
