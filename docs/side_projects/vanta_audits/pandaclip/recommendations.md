# PandaClip — Recommendations

Constructive, in your language, offered not prescribed. Ordered by cost-to-value.

---

## R1 — Add a README section: "Secret screening is a hint, not a boundary"

**Cost:** 15 min · **Value:** high asymmetric (silent-slip prevention)

Right after the "Screen obvious credential material" paragraph, add:

> Screening catches the six most common credential shapes (PEM keys, provider `sk-*` keys, GitHub `gh*_` tokens, AWS access-key IDs, JWTs, and `password=` assignments). It **will not** catch: custom internal token formats, session cookies, `Authorization: Bearer` values without JWT structure, base64-encoded creds, or anything not in that pattern list. Treat screening as a safety net for slips, not as an authorization boundary. If you paste secrets regularly, use `clip_delete` immediately or, better, don't paste them.

The value is expectation-calibration, not code change.

## R2 — Add an MCP-server-surface smoke test

**Cost:** 4-6 hrs · **Value:** high (catches schema drift the type system misses)

A single test file that:
1. Spawns the server as a child process
2. Speaks MCP stdio via `@modelcontextprotocol/sdk`
3. Calls each of the 40 tools with a canonical fixture (mostly happy-path)
4. Asserts each response is non-error and matches the expected top-level shape

Would live at `servers/pandaclip/test/server.integration.test.ts`. Would catch the "the tool schema says `ttl_class` but the store expects `ttlClass`" class of bug that ships silently today.

## R3 — Cycle detection in `bambooStore.scan()`

**Cost:** 30 min · **Value:** medium (prevents dup-entry storms on cyclic symlinks)

Track `Set<string>` of already-visited absolute paths (`fs.realpathSync`); skip re-entry. Prevents both infinite recursion (currently backstopped by `maxDepth`/`MAX_SCAN_ENTRIES`) and duplicate rel_path entries.

```ts
const seenAbs = new Set<string>();
const walk = (dir, depth) => {
  const real = fs.realpathSync(dir);
  if (seenAbs.has(real)) return;
  seenAbs.add(real);
  // ... existing logic ...
};
```

## R4 — Expand the `wal_autocheckpoint` comment

**Cost:** 5 min · **Value:** low-medium (protects future contributors)

Two extra sentences saying (a) why WAL visibility matters (cross-process readers that don't share `-shm`), (b) what the tradeoff is (checkpoint-per-commit hurts throughput under write-heavy `cache_set` workloads), and (c) how a future maintainer would know it's safe to relax it (single-process embedded scenarios).

## R5 — Streaming progress for `organize_scan`

**Cost:** 1-2 days (introduces MCP progress notifications) · **Value:** medium (UX only)

For workspaces pointing at large trees, `organize_scan` can take multiple seconds while the MCP server is blocked. MCP supports progress notifications; emitting `{seen: N, discovered: M}` every 500 entries would keep the client informed. Only worth doing if you hear complaints — right now the sync path is fine for typical workspaces.

## R6 — Single-JOIN variant of `neighbors()` and `traverse()`

**Cost:** 2-3 hrs (+ tests) · **Value:** low until graphs grow

```sql
SELECT e.*, n.* FROM edges e
JOIN nodes n ON n.id = (CASE WHEN e.src = ? THEN e.dst ELSE e.src END)
WHERE (e.src = ? OR e.dst = ?) AND e.pruned_at IS NULL AND n.pruned_at IS NULL
```

Bundles the N+1 into one query. Not worth doing until you have a garden with 1k+ nodes and someone reports slowness.

## R7 — Decide the fate of `maxBytes` in `cacheStore`

**Cost:** 30 min · **Value:** low (removes dead schema OR ships a real feature)

`namespaces.max_bytes` is accepted by `configureNamespace()` and stored in the DB, but no code path reads it. Either:
- **Delete** the column and the accepted arg (dead schema shouldn't ship as configurable)
- **Implement**: when `cache_set` would push a namespace over `max_bytes`, evict oldest-`last_hit`-first until below the limit. Nice small feature, ~50 LOC + a test.

Choose one. Shipping accepted-but-ignored config is the shape that erodes trust.

## R8 — Cross-project: consider `local-first-mcp-core` shared package

**Cost:** medium (design + migration) · **Value:** deferred (only worth it if a third project ships)

Only pull this out when there's a third consumer. Two projects (panda + magpie) sharing an internal package is the ratio where premature abstraction usually happens. Log the observation, revisit at 3.

---

## What I'd do first if it were mine

1. **R1** (README secret-screening expectation) — 15 min, biggest safety return
2. **R7** (decide `maxBytes`) — 30 min, removes ambiguity from the API surface
3. **R2** (MCP-surface smoke test) — 4-6 hrs, biggest quality return

Everything else can wait until it earns priority via a reported issue.

---

## What you're doing well that I want to name explicitly

- **Soft-delete via `pruned_at`** in garden — kindred to append-only-truth discipline
- **Migrations from day one** — not the "we'll add migrations when we need them" trap
- **Uniform `ok/err` envelope + `wrap()`** — every tool has consistent error shape without per-tool boilerplate
- **Read-only lens child process** — writer/reader separation is architecturally correct and the comment explains WHY node has to be system-node (>= 22.5, `node:sqlite`, WAL-aware reads)
- **Hard limits on every list-shaped return** — no unbounded work reachable via MCP input
- **Zero god files** — no source file over 500 LOC; each store is ~200-300; `panda-core` is ~50 across four files

That kind of restraint is unusual in a 2-week-old project.
