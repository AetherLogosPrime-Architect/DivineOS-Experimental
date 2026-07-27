# Magpie Search — Recommendations (Part 3, Final)

Continuation of [recommendations.md](recommendations.md) and [recommendations_part2.md](recommendations_part2.md). Numbers continue at R19+. Cost-to-value ordered.

---

## R19 — MCP `reindex` tool drops the `source` parameter

**Cost:** 5 min · **Value:** high (closes attacker-controllable path into the indexer)

`mcp_server.py:242-247`: remove `source=a.get("source")` from the reindex handler. Reindex operates on `CLAUDE_PROJECTS_DIR` (env-controlled, operator-set). If operators need a different source dir, they set the env var and restart the server.

Same class as R10 (FilesProvider requires root) — MCP surface should be "search-only", and any tool that accepts a path parameter is an unforced-error surface.

## R20 — Fix telemetry endpoint reachability (or document Tailscale-only)

**Cost:** 30 min (docs) OR 2-4 hrs (public collector) · **Value:** medium-high (fixes a broken opt-in contract)

Three options:

**Option A (cheapest — docs)**: README:
> "The default telemetry collector is on the maintainer's private tailnet. If you want telemetry to actually send, set `MAGPIE_SEARCH_TELEMETRY_URL` to your own collector, or (if invited) join the maintainer's tailnet. Otherwise `telemetry enable` silently emits fire-and-forget events that never arrive."

**Option B**: preflight-on-enable — one POST at `telemetry enable`, report reachability, refuse to enable if unreachable.

**Option C**: public-resolvable collector.

## R21 — Rowid-invariant violations surface in `stats_summary()` and/or `health_check()`

**Cost:** 1-2 hrs · **Value:** high (silent invariant failure becomes observable degradation)

Add a state file at `$MAGPIE_SEARCH_HOME/.indexer_state.json` (mirror of backup.py's pattern). Every indexer pass writes:

```json
{
  "last_pass_ts": "...",
  "files_seen": N,
  "files_updated": N,
  "errors": [{"file": "...", "class": "RowidInvariantViolation", "message": "..."}]
}
```

`stats_summary()` includes `last_pass_errors: [...]` in its return dict. A monitor polling stats now sees invariant violations without needing to tail stderr.

Same shape as `backup.py`'s `health_check()`.

## R22 — Unknown-block-type indexing: log unknown types once + drop content

**Cost:** 30 min · **Value:** medium (bounded exposure as Claude Code schema evolves)

`indexer.py:449-452`:

```python
else:
    if t not in _SEEN_UNKNOWN_TYPES:
        _SEEN_UNKNOWN_TYPES.add(t)
        print(f"  ? unknown block type: {t!r} (indexing type only, not content)",
              file=sys.stderr)
    out.append((f"block:{t}", ""))  # index the type, drop the content
```

Trade-off: costs some searchability for new block types until an operator adds handling. Given the field is Claude Code JSONL and the schema evolves, "index the type + notify" is a better default than "serialize whole and hope redact catches everything."

## R23 — `nightly_sync.py` emits `DeprecationWarning`

**Cost:** 2 min · **Value:** low (removes future-surprise for cron/Task Scheduler users)

```python
import warnings
warnings.warn(
    "magpie_search.nightly_sync is a compat shim; migrate to magpie_search.backup",
    DeprecationWarning, stacklevel=2,
)
```

## R24 — `backfill_dedup` preserves message timestamps in `chunk_dedup`

**Cost:** 20 min · **Value:** medium (accurate first-seen timestamps for post-hoc analysis)

`indexer.py:915-937`: pull `m.ts` in the SELECT and pass it through:

```python
rows = conn.execute(
    "SELECT m.rowid AS rid, m.session_id AS sid, m.text AS txt, m.ts AS ts "
    "FROM messages m WHERE NOT EXISTS ... ORDER BY m.session_id, m.rowid LIMIT ?",
    (batch,),
).fetchall()
...
conn.execute(
    "INSERT INTO chunk_dedup(sha256, first_seen_at, last_seen_at, count) "
    "VALUES (?, ?, ?, 1) "
    "ON CONFLICT(sha256) DO UPDATE SET "
    "  first_seen_at = MIN(chunk_dedup.first_seen_at, excluded.first_seen_at), "
    "  last_seen_at = MAX(chunk_dedup.last_seen_at, excluded.last_seen_at), "
    "  count = chunk_dedup.count + 1",
    (h, r["ts"] or "", r["ts"] or ""),
)
```

ISO-8601 timestamps sort lexicographically so `MIN`/`MAX` string ops work. Empty strings sort before any real timestamp — pre-existing empty first_seen_at values get correctly replaced by any real ts.

## R25 — Reverse-line-read for `audit.tail(n)`

**Cost:** 45 min · **Value:** medium (removes O(rotate_size) memory cost per trust monitor tick)

```python
def tail(n: int = 100) -> list[dict[str, Any]]:
    p = _path()
    if not p.exists():
        return []
    try:
        block = 8192
        with p.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            data = b""
            while size > 0 and data.count(b"\n") <= n:
                read = min(block, size)
                size -= read
                f.seek(size)
                data = f.read(read) + data
        lines = data.decode("utf-8", errors="replace").splitlines()
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception:
        return []
```

## R26 — Reranker sets `rerank_score=None` on fallback so shape stays consistent

**Cost:** 5 min · **Value:** low (removes downstream foot-gun)

`llm/reranker.py:112-114` (fallback path): walk `base["hits"]` and add `h["rerank_score"] = None` to each before returning. Now every hit has BOTH `rrf_score` (fallback path) and `rerank_score` fields; the missing one is explicitly None, not `KeyError`.

## R27 — Comment case-preservation in `_normalize_for_hash`

**Cost:** 30 sec · **Value:** low (protects next contributor from adding `.lower()`)

`indexer.py:57-58`:

```python
def _normalize_for_hash(text: str) -> str:
    # DELIBERATELY case-preserving: for code/IDs/hashes, case IS content.
    # Do NOT add .lower() — "APIKey" and "apikey" must dedup to different
    # clusters when both appear literally in the transcripts.
    return _HASH_WHITESPACE_RE.sub(" ", text or "").strip()
```

## R28 — Better `install_id` fallback

**Cost:** 2 min · **Value:** low (removes cross-install ID collision)

`telemetry.py:71`:

```python
except Exception:
    return f"anon-{uuid.uuid4().hex[:8]}"
```

Per-process id when persistence fails.

---

## What I'd do first if it were mine (Part 3)

1. **R19** (MCP reindex drop source) — 5 min · attacker-controllable indexer entry
2. **R21** (indexer errors in stats) — 1-2 hrs · biggest observability win
3. **R22** (unknown block type: type-only + notify) — 30 min · bounds schema evolution risk
4. **R20** (telemetry endpoint fix/docs) — 30 min minimum · broken-contract fix
5. **R24** (backfill timestamps) — 20 min · correct historical data

---

## Consolidated top-15 across ALL three parts

Combining R1-R9, R10-R18, R19-R28, ranked by cost-to-value across the whole audit:

1. **R1** (provenance redaction in web provider) — 5 min · closes real leak edge · Part 1
2. **R10** (FilesProvider requires root) — 5 min · scope escape hatch · Part 2
3. **R19** (MCP reindex drop source) — 5 min · attacker-controllable indexer entry · Part 3
4. **R11** (SQL identifier validation in KG/Vector) — 15 min · future-proof trust boundary · Part 2
5. **R2** (outbound web query redaction) — 30 min · holds local-first promise · Part 1
6. **R22** (unknown block type handling) — 30 min · bounds schema evolution risk · Part 3
7. **R12** (deepweb SSRF guard) — 30-45 min · metadata-endpoint exposure · Part 2
8. **R21** (indexer errors in stats) — 1-2 hrs · biggest observability win · Part 3
9. **R3** (injection-marker probe in guardrails) — 3-4 hrs · biggest LLM defense-in-depth · Part 1
10. **R15** (summarizer keep tail) — 15 min · largest single-fix summary-quality win · Part 2
11. **R14** (audit numbered rotation) — 20 min · forensic history · Part 2
12. **R24** (backfill preserves timestamps) — 20 min · accurate historical data · Part 3
13. **R4** (federation error string scrubbing) — 15 min · future-leak trap · Part 1
14. **R20** (telemetry endpoint fix/docs) — 30 min · broken opt-in contract · Part 3
15. **R13** (independent verifier model) — 1-2 hrs · real second opinion in summarizer · Part 2

Total for top-15: ~10-12 hours of focused work.

---

## Trust-boundary class recommendation (cross-cutting)

Several findings across the audit (F1, F2, F11, F12, F13, F30) share one root: **the project assumes config is trusted operator input, but there's no explicit contract or enforcement of that assumption.** If a plugin system, config-file-loader-with-user-input, or MCP-input-to-config path ever gets added, all of these become active exposures simultaneously.

Consider making the trust boundary **explicit**:
- A `magpie_search.config` module loads and **validates** config once at startup, rejecting anything containing SQL-metachar / shell-metachar / path-traversal patterns.
- Provider `__init__` receives validated config, never raw dict.
- MCP tools receive an **allowlist** of scope shapes, not `Any`.

Half a day of design; makes the entire class closed-by-construction instead of remembered-per-site.

---

## What you're doing well (final synthesis)

Three patterns to name once more across all three parts:

1. **Failures named at the site of the fix** — `CRIT-1`/`HIGH-1`/`HIGH-2`/`HIGH-4`/`GAP-4`/`GAP-5`/`MED-1`/`MED-2`. Every audit-finding fix ships with an in-code teaching comment. The next maintainer inherits the WHY, not just the WHAT.

2. **Fail-closed on ambiguous verification** — `trust.py:186-192` "missing trust field counts as untrusted, not clean"; `summarizer.py:83-93` "unqualified YES required, `YES THIS IS FABRICATED` must not pass"; `backup.py:679-693` "dry-run must NEVER advance last_success_ts." Three distinct places where the RIGHT direction of asymmetry is deliberately chosen.

3. **Content firewalls at the write chokepoint** — `redactor` runs in `parse_line` before storage; `audit.log` re-runs `redactor` before write ("single chokepoint for the audit surface"); `telemetry._clean()` runs before serialization. Not one defense — three, each at the right layer.

The audit produces 33 findings across ~30 files and ~8,600 LOC. **None are structural.** The trust-boundary class (R19+R10+R11+R1+R2+R30) is the biggest architectural theme and is closable in a half-day. Everything else is polish or forensic-history improvement.

This is a codebase that would pass the DivineOS Watchmen system's standards. Named that in Parts 1 and 2; naming it once more as the final line: **the audit-driven-discipline shape shows through in the code, and it shows through consistently.**
